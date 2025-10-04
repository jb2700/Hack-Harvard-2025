#!/usr/bin/env python3
"""
Run Segment Anything (SAM) on `polar_2.png` using the provided checkpoint `sam_vit_h_4b8939.pth`.
"""
from pathlib import Path
import sys
import json
import numpy as np
from PIL import Image
import torch
import random
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
import cv2
import shutil
import urllib.request
import os

ROOT = Path(__file__).resolve().parent
IMAGE_FN = ROOT / "polar_2.png"
CKPT_FN = ROOT / "sam_vit_h_4b8939.pth"
OUT_DIR = ROOT / "sam_outputs"
OUT_RGBA_DIR = ROOT / "rgba_sam_outputs"

def get_masks(img):
    sam_builder = sam_model_registry.get("vit_h")
    model = sam_builder(checkpoint=str(CKPT_FN))
    model.to("cpu")
    mask_generator = SamAutomaticMaskGenerator(model)
    print("Generating masks...")
    masks = mask_generator.generate(img)
    print(f"Generated {len(masks)} masks")
    OUT_DIR.mkdir(exist_ok=True)
    masks_arr = [m["segmentation"] for m in masks]
    np.save(OUT_DIR / "masks.npy", masks_arr)
    return masks

def detect_text_boxes(img_rgb):
    """Return list of bounding boxes (x,y,w,h) for text regions.
    """
    img_h, img_w = img_rgb.shape[:2]

    # Prepare model path
    model_dir = ROOT / "models"
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / "frozen_east_text_detection.pb"

    # Download EAST model if missing
    if not model_path.exists():
        try:
            _download_east_model(model_path)
        except Exception:
            # ignore download errors and fall back
            pass

    # Try EAST detector first
    if model_path.exists():
        try:
            net = cv2.dnn.readNet(str(model_path))
            # EAST requires width/height to be multiples of 32
            newW = (img_w + 31) // 32 * 32
            newH = (img_h + 31) // 32 * 32
            rW = img_w / float(newW)
            rH = img_h / float(newH)
            blob = cv2.dnn.blobFromImage(img_rgb, 1.0, (newW, newH), (123.68, 116.78, 103.94), swapRB=True, crop=False)
            net.setInput(blob)
            scores, geometry = net.forward(["feature_fusion/Conv_7/Sigmoid", "feature_fusion/concat_3"])
            rects, confidences = _decode_east(scores, geometry, confThreshold=0.2)
            boxes = []
            if rects:
                # apply NMS with permissive thresholds
                try:
                    indices = cv2.dnn.NMSBoxes(rects, confidences, score_threshold=0.2, nms_threshold=0.4)
                except Exception:
                    # fallback for older OpenCV which uses positional args
                    indices = cv2.dnn.NMSBoxes(rects, confidences, 0.2, 0.4)
                if len(indices) > 0:
                    for i in indices.flatten():
                        x0, y0, w_box, h_box = rects[i]
                        x = int(max(0, x0 * rW))
                        y = int(max(0, y0 * rH))
                        w_box = int(min(img_w - x, w_box * rW))
                        h_box = int(min(img_h - y, h_box * rH))
                        # expand a small margin
                        padx = max(2, int(0.02 * w_box))
                        pady = max(2, int(0.02 * h_box))
                        x = max(0, x - padx)
                        y = max(0, y - pady)
                        w_box = min(img_w - x, w_box + 2 * padx)
                        h_box = min(img_h - y, h_box + 2 * pady)
                        boxes.append((x, y, w_box, h_box))
                else:
                    # use raw rects if NMS removed everything
                    for (x0, y0, w_box, h_box) in rects:
                        x = int(max(0, x0 * rW))
                        y = int(max(0, y0 * rH))
                        w_box = int(min(img_w - x, w_box * rW))
                        h_box = int(min(img_h - y, h_box * rH))
                        boxes.append((x, y, w_box, h_box))
            if boxes:
                return boxes
        except Exception:
            # if EAST fails, fall back to MSER below
            pass

    # Last-resort fallback: MSER
    try:
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        raw_boxes = []
        for region in regions:
            try:
                rx, ry, rw, rh = cv2.boundingRect(region.reshape(-1, 1, 2))
            except Exception:
                continue
            # basic filters
            if rw < 8 or rh < 8:
                continue
            raw_boxes.append((rx, ry, rw, rh))
        if not raw_boxes:
            return []
        # merge and return
        return _merge_boxes(raw_boxes, iou_thresh=0.1)
    except Exception:
        return []


def _download_east_model(path):
    url = "https://github.com/argman/EAST/releases/download/v1.0/frozen_east_text_detection.pb"
    tmp = str(path) + ".download"
    print(f"Downloading EAST model to {path} ...")
    urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, str(path))


def _decode_east(scores, geometry, confThreshold=0.5):
    scores = scores[0, 0]
    geo = geometry[0]
    H, W = scores.shape
    rects = []
    confidences = []
    for y in range(H):
        for x in range(W):
            score = scores[y, x]
            if score < confThreshold:
                continue
            offsetX = x * 4.0
            offsetY = y * 4.0
            angle = geo[4, y, x]
            cos = np.cos(angle)
            sin = np.sin(angle)
            h = geo[0, y, x] + geo[2, y, x]
            w = geo[1, y, x] + geo[3, y, x]
            endX = int(offsetX + (cos * geo[1, y, x]) + (sin * geo[2, y, x]))
            endY = int(offsetY - (sin * geo[1, y, x]) + (cos * geo[2, y, x]))
            startX = int(endX - w)
            startY = int(endY - h)
            rects.append([startX, startY, int(w), int(h)])
            confidences.append(float(score))
    return rects, confidences


def _merge_boxes(boxes, iou_thresh=0.2):
    if not boxes:
        return []
    rects = []
    for (x, y, w, h) in boxes:
        rects.append([int(x), int(y), int(x + w), int(y + h)])
    merged = True
    while merged:
        merged = False
        new_rects = []
        used = [False] * len(rects)
        for i, a in enumerate(rects):
            if used[i]:
                continue
            ax1, ay1, ax2, ay2 = a
            aw = ax2 - ax1
            ah = ay2 - ay1
            cur = a.copy()
            for j, b in enumerate(rects):
                if i == j or used[j]:
                    continue
                bx1, by1, bx2, by2 = b
                ix1 = max(ax1, bx1)
                iy1 = max(ay1, by1)
                ix2 = min(ax2, bx2)
                iy2 = min(ay2, by2)
                iw = max(0, ix2 - ix1)
                ih = max(0, iy2 - iy1)
                inter = iw * ih
                area_a = aw * ah
                area_b = (bx2 - bx1) * (by2 - by1)
                union = area_a + area_b - inter
                iou = inter / union if union > 0 else 0.0
                gap_x = max(0, max(bx1 - ax2, ax1 - bx2))
                gap_y = max(0, max(by1 - ay2, ay1 - by2))
                gap = max(gap_x, gap_y)
                if iou >= iou_thresh or gap <= 12:
                    cur[0] = min(cur[0], bx1)
                    cur[1] = min(cur[1], by1)
                    cur[2] = max(cur[2], bx2)
                    cur[3] = max(cur[3], by2)
                    used[j] = True
                    merged = True
            used[i] = True
            new_rects.append(cur)
        rects = new_rects
    out = []
    for x1, y1, x2, y2 in rects:
        out.append((int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
    return out

def group_masks_by_text(img, masks):
    text_boxes = detect_text_boxes(img)
    groups = []
    # for each text box, find masks that overlap
    if not text_boxes:
        return groups
    for text_box in text_boxes:
        x, y, w, h = text_box
        group_masks = []
        for i, mask in enumerate(masks):
            seg = mask["segmentation"]
            # Create mask for text box region
            text_mask = np.zeros_like(seg, dtype=bool)
            text_mask[y:y+h, x:x+w] = True
            mask_in_text = np.logical_and(seg, text_mask)
            mask_area = np.sum(seg)
            overlap_area = np.sum(mask_in_text)

            # If majority of mask is in text box, add to group
            if mask_area > 0 and overlap_area / mask_area > 0.5:
                group_masks.append(i)
        
        if group_masks:
            groups.append({
                "text_box": text_box,
                "mask_indices": group_masks
            })
    return groups

def main():
    if not IMAGE_FN.exists():
        print(f"Image not found: {IMAGE_FN}")
        sys.exit(2)

    if not CKPT_FN.exists():
        print(f"Checkpoint not found: {CKPT_FN}")
        sys.exit(2)

    # save individual masks and an overlay
    img = np.array(Image.open(IMAGE_FN).convert("RGB"))
    masks = get_masks(img)
    # ensure rgba output dir exists
    OUT_RGBA_DIR.mkdir(exist_ok=True)
    colors = [(random.randint(0,255), random.randint(0,255), random.randint(0,255)) for _ in range(len(masks))]
    overlay = img.copy()
    alpha = 0.5
    for i, m in enumerate(masks):
        seg_bool = m["segmentation"].astype(bool)
        seg = (seg_bool.astype(np.uint8) * 255)
        Image.fromarray(seg).save(OUT_DIR / f"mask_{i:03d}.png")
        # save RGBA with transparent outside, original pixels inside.
        rgba = np.zeros((img.shape[0], img.shape[1], 4), dtype=np.uint8)
        rgba[:, :, :3] = img
        rgba[:, :, 3] = (seg_bool.astype(np.uint8) * 255)
        Image.fromarray(rgba).save(OUT_RGBA_DIR / f"mask_{i:03d}_rgba.png")
        color = colors[i]
        overlay[seg_bool] = (overlay[seg_bool] * (1 - alpha) + np.array(color) * alpha).astype(np.uint8)
    print("Saved outputs to", OUT_DIR)

    # Save overlay image
    try:
        Image.fromarray(overlay).save(OUT_DIR / "overlaid.png")
    except Exception:
        pass

    # Group masks by detected text boxes and write groups.json
    groups = group_masks_by_text(img, masks)
    if groups:
        with open(OUT_DIR / "groups.json", "w") as f:
            json.dump({"groups": groups}, f, indent=2)
        print(f"Wrote groups.json with {len(groups)} groups")

if __name__ == "__main__":
    main()
