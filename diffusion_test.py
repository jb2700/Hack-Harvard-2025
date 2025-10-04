import torch
from PIL import Image, ImageDraw
import numpy as np
from diffusers import StableDiffusionInpaintPipeline
from diffusers.utils import load_image

def test_diffusion_inpaint():
    print("== Starting diffusion inpaint test ==")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    # Load a simple example image (you can replace with your own)
    # We'll use load_image from diffusers utils (if available), or fallback
    try:
        img = load_image("https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/inpaint.png")
        print("Loaded example image via load_image")
    except Exception as e:
        print("Could not load via load_image:", e)
        # fallback: create a simple image
        img = Image.new("RGB", (256, 256), color=(128, 128, 128))
        print("Created dummy image (256x256 gray)")

    # Create a simple mask: mask out a small square in the center
    mask = Image.new("L", img.size, color=0)  # 0 = keep, white (255) = inpaint
    draw = ImageDraw.Draw(mask)
    w, h = img.size
    box_size = 64
    left = w // 2 - box_size // 2
    top = h // 2 - box_size // 2
    right = left + box_size
    bottom = top + box_size
    draw.rectangle([left, top, right, bottom], fill=255)
    print("Mask created: a square in the center to inpaint")

    # Load the inpainting pipeline
    print("Loading StableDiffusionInpaintPipeline (this may take some time)...")
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        "runwayml/stable-diffusion-inpainting"
    ).to(device)

    print("Pipeline loaded successfully")

    # Run the inpainting
    prompt = "a nice background fill"  # fallback prompt
    print("Running inpainting with prompt:", prompt)
    result = pipe(prompt=prompt, image=img, mask_image=mask, num_inference_steps=20)
    out_img = result.images[0]
    print("Inference done; got output image")

    # Optionally save or show
    out_img.save("test_inpaint_output.png")
    print("Saved output as test_inpaint_output.png")

    # Extra: check that mask region was changed (rough check)
    out_arr = np.array(out_img)
    orig_arr = np.array(img)
    # Compare the center region
    center_patch_new = out_arr[top:bottom, left:right]
    center_patch_old = orig_arr[top:bottom, left:right]
    diff = np.mean(np.abs(center_patch_new.astype(int) - center_patch_old.astype(int)))
    print(f"Mean absolute difference in masked region: {diff:.2f}")

    print("== Test complete ==")


if __name__ == "__main__":
    test_diffusion_inpaint()
