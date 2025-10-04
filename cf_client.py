import base64
import json
import requests
from PIL import Image
import io

def img_to_b64_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def b64_to_image(b64: str) -> Image.Image:
    data = base64.b64decode(b64)
    return Image.open(io.BytesIO(data))

def call_cf_inpaint(worker_url: str, api_key: str, image: Image.Image, mask: Image.Image, prompt: str) -> Image.Image:
    img_b64 = img_to_b64_png(image)
    mask_b64 = img_to_b64_png(mask)
    payload = {
        "image": img_b64,
        "mask": mask_b64,
        "prompt": prompt
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    resp = requests.post(worker_url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    resp_json = resp.json()
    out_b64 = resp_json.get("output_image")
    if not out_b64:
        raise RuntimeError("No output_image in response JSON")
    return b64_to_image(out_b64)

if __name__ == "__main__":
    # Example usage
    worker_url = "https://hackharvard3.julian-beaudry.workers.dev"
    api_key = "newnewTok"  # route this in Cloudflare so Worker only accepts valid requests
    # api_key = "yJcstjDte0pdZwHFe1SGKHzLQX8KyN1R5DifzB31"
    # api_key = ""
    # load image & mask
    image = Image.open("input.png").convert("RGB")
    mask = Image.open("mask.png").convert("L")
    prompt = "fill background naturally"  # prompt guidance

    out_img = call_cf_inpaint(worker_url, api_key, image, mask, prompt)
    out_img.save("cf_output.png")
    print("Saved output to cf_output.png")
