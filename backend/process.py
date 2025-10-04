#!/usr/bin/env python3
"""
Run Segment Anything (SAM) on `polar_2.png` using the provided checkpoint `sam_vit_h_4b8939.pth`.
"""
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
from pathlib import Path
import json
import numpy as np
from PIL import Image
import cv2
from helper import affine_crop, portrait
import shutil

#requires pytesseract installation through brew or similar package manager
import pytesseract

ROOT = Path(__file__).resolve().parent
CKPT_FN = ROOT / "sam_vit_h_4b8939.pth"
OUT_RGBA_DIR = ROOT / "images" / "sam_shapes"

def get_masks(img):
    sam_builder = sam_model_registry.get("vit_h")
    model = sam_builder(checkpoint=str(CKPT_FN))
    model.to("cpu")
    mask_generator = SamAutomaticMaskGenerator(model)
    print("Generating masks...")
    masks = mask_generator.generate(img)
    print(f"Generated {len(masks)} masks")
    masks_arr = [m["segmentation"] for m in masks]
    return masks

def write_masks(masks, out_dir, img_rgb):
        """Write mask outputs into out_dir.
        For each mask we write:
            - mask_{i:03d}_rgba.png: RGBA image where pixels inside the mask keep the
                original image RGB values and alpha=255; outside pixels are transparent.
            - mask_{i:03d}_color.png: a colorful solid fill for the mask area (alpha=255)
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, m in enumerate(masks):
            seg = m["segmentation"].astype(bool)
            h, w = seg.shape

            # RGBA masked original: keep original colors where mask is True
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            # img_rgb is expected shape (H, W, 3) and RGB ordering
            rgba[seg, :3] = img_rgb[seg]
            rgba[seg, 3] = 255
            Image.fromarray(rgba).save(out_dir / f"mask_{i:03d}_rgba.png")

        print('saved outputs to ', out_dir)

#helper function for group masks_by_text
def detect_text_boxes(img_rgb):
    """Return list of bounding boxes (x,y,w,h) for text regions.
    """
    data = pytesseract.image_to_data(img_rgb, output_type=pytesseract.Output.DICT)
    text_boxes = []
    img_with_boxes = img_rgb.copy()
    n_boxes = len(data['text'])
    for i in range(n_boxes):
        if int(data['conf'][i]) > 30:
            text = data['text'][i].strip()
            if text: 
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                text_boxes.append((x, y, w, h))
                cv2.rectangle(img_with_boxes, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.imwrite(str(OUT_RGBA_DIR / "text_boxes.png"), cv2.cvtColor(img_with_boxes, cv2.COLOR_RGB2BGR))
    return text_boxes

#Groups masks by their text bounding boxes.
def group_masks_by_text(img, masks):
    text_boxes = detect_text_boxes(img)
    groups = []
    print('found text boxes:', len(text_boxes))
    for text_box in text_boxes:
        x, y, w, h = text_box
        group_masks = []
        for i, mask in enumerate(masks):
            seg = mask["segmentation"]
            text_mask = np.zeros_like(seg, dtype=bool)
            text_mask[y:y+h, x:x+w] = True
            mask_in_text = np.logical_and(seg, text_mask)
            mask_area = np.sum(seg)
            overlap_area = np.sum(mask_in_text)

            if mask_area > 0 and overlap_area / mask_area > 0.5:
                group_masks.append(i)
        
        if group_masks:
            groups.append({
                "text_box": text_box,
                "mask_indices": group_masks
            })
    return groups
    
def downscale_image(img, max_dim=1600):
    height, width = img.shape[:2]
    if max(height, width) > max_dim:
        scale = max_dim / max(height, width)
        new_size = (int(width * scale), int(height * scale))
        img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
    return img


# For each group, create prefixed copies of mask files so it's easy to
# identify which masks belong to which text box. Prefix uses the
# text_box top-left coordinates: "{x}_{y}_mask_###_rgba.png".
def save_masks_for_image(img_filename):
    down_path = ROOT / "images" / "input" / "downscaled" / img_filename
    load_path = down_path

    img_rgb = np.array(Image.open(load_path).convert("RGB"))
    masks = get_masks(img_rgb)

    out_dir = OUT_RGBA_DIR / img_filename.rstrip(".jpeg")
    write_masks(masks, out_dir, img_rgb)
    groups = group_masks_by_text(img_rgb, masks)

    if groups:
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "groups.json", "w") as f:
            json.dump({"groups": groups}, f, indent=2)
            
        print(f"Wrote groups.json with {len(groups)} groups")
        for g in groups:
            tb = g.get('text_box', None)
            if not tb:
                continue
            x, y = tb[0], tb[1]
            prefix = f"{x}_{y}"
            group_dir = out_dir / prefix
            group_dir.mkdir(parents=True, exist_ok=True)
            for mi in g.get('mask_indices', []):
                src = out_dir / f"mask_{mi:03d}_rgba.png"
                if src.exists():
                    dst = group_dir / f"mask_{mi:03d}_rgba.png"
                    # avoid overwriting existing file
                    if not dst.exists():
                        try:
                            shutil.copy2(src, dst)
                        except Exception as e:
                            print(f"Failed to copy {src} -> {dst}: {e}")
        
def main():
    INPUT_DIR = ROOT / "images" / "input"
    OUT_RGBA_DIR.mkdir(exist_ok=True)

    # original_dir = INPUT_DIR / "original"
    # downscaled_dir = INPUT_DIR / "downscaled"
    # downscaled_dir.mkdir(exist_ok=True)

    # for image_path in original_dir.glob("*"):
    #     if image_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
    #         print(f"Downscaling {image_path.name}...")
    #         img = downscale_image(np.array(Image.open(image_path).convert("RGB")))
    #         # Save downscaled image
    #         output_path = downscaled_dir / image_path.name
    #         img.save(output_path, quality=100)

    save_masks_for_image("IMG_0451.jpeg")
    image_filename = None
    if (image_filename != None):
        pass
        # img = np.array(Image.open(downscaled_dir / image_filename).convert("RGB"))
        # #Mask generation
        # masks = get_masks(img)
        # write_masks(masks, OUT_RGBA_DIR / image_filename.rstrip(".png"))
        # groups = group_masks_by_text(img, masks)
        # if groups:
        #     with open(OUT_RGBA_DIR / image_filename /"groups.json", "w") as f:
        #         json.dump({"groups": groups}, f, indent=2)
        #     print(f"Wrote groups.json with {len(groups)} groups")

if __name__ == "__main__":
    main()