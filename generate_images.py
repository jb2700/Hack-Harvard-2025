from PIL import Image, ImageDraw
import os

def make_test_input_and_mask(
    input_path="input.png",
    mask_path="mask.png",
    width=256, height=256,
    mask_box=(80, 80, 180, 180)
):
    """
    Creates:
     - input image: colored gradient + a circle or rectangle
     - mask image: white region inside mask_box (to inpaint), black elsewhere
    """
    # Create a background gradient or pattern
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            # simple gradient from blue to green
            r = 50
            g = int(100 + (155 * x / width))
            b = int(100 + (155 * y / height))
            pixels[x, y] = (r, g, b)
    # Draw a shape to make it interesting
    draw = ImageDraw.Draw(img)
    draw.ellipse((60, 60, 120, 120), fill=(200, 50, 50))  # a red circle

    # Create mask (L mode, black background, white region)
    mask = Image.new("L", (width, height), color=0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rectangle(mask_box, fill=255)

    # Save them
    img.save(input_path)
    mask.save(mask_path)
    print(f"Saved test input image to {input_path}")
    print(f"Saved test mask image to {mask_path}")

if __name__ == "__main__":
    # Create test files
    make_test_input_and_mask()
