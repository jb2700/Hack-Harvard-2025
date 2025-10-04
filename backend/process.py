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

def main():
    INPUT_DIR = ROOT / "images" / "input"
    OUTPUT_DIR = ROOT / "images" / "cropped"
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUT_RGBA_DIR.mkdir(exist_ok=True)

    # Process all images in input directory
    # for image_path in INPUT_DIR.glob("*"):
    #     if image_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
    #         print(f"Processing {image_path.name}...")
    #         img = np.array(Image.open(image_path).convert("RGB"))

    #         # STEP 1: Crop image to rectangle. Apply quadrilateral detection and cropping
    #         cropped_img = affine_crop(img, image_path)
    #         # Save cropped image
    #         output_path = OUTPUT_DIR / f"cropped_{image_path.name}"
    #         Image.fromarray(cropped_img).save(output_path)

    # Downscale images in original folder
    original_dir = INPUT_DIR / "original"
    downscaled_dir = INPUT_DIR / "downscaled"
    downscaled_dir.mkdir(exist_ok=True)

    for image_path in original_dir.glob("*"):
        if image_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            print(f"Downscaling {image_path.name}...")
            img = downscale_image(np.array(Image.open(image_path).convert("RGB")))
            # Save downscaled image
            output_path = downscaled_dir / image_path.name
            img.save(output_path, quality=100)

    image_filename = None
    if (image_filename != None):
        img = np.array(Image.open(downscaled_dir / image_filename).convert("RGB"))
        #Mask generation
        masks = get_masks(img)
        for i, m in enumerate(masks):
            seg_bool = m["segmentation"].astype(bool)
            # save RGBA with transparent outside, original pixels inside.
            rgba = np.zeros((img.shape[0], img.shape[1], 4), dtype=np.uint8)
            rgba[:, :, :3] = img
            rgba[:, :, 3] = (seg_bool.astype(np.uint8) * 255)
            # Create folder based on original filename
            img_name = Path(image_filename).stem
            img_folder = OUT_RGBA_DIR / img_name
            img_folder.mkdir(exist_ok=True)
            Image.fromarray(rgba).save(img_folder / f"mask_{i:03d}_rgba.png")
        print("Saved outputs to", OUT_RGBA_DIR)
        groups = group_masks_by_text(img, masks)
        if groups:
            with open(OUT_RGBA_DIR / img_name /"groups.json", "w") as f:
                json.dump({"groups": groups}, f, indent=2)
            print(f"Wrote groups.json with {len(groups)} groups")

if __name__ == "__main__":
    main()
