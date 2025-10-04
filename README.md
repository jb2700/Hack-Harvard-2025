# Promosaic: Remix anything, anytime.

"Good artists copy, great artists steal".

![diagram of methodology](https://raw.githubusercontent.com/jb2700/Hack-Harvard-2025/refs/heads/main/readme_imgs/diagram.jpg)

Our project reimagines how people can capture, remix, and reuse the designs that surround them every day. Using Meta’s Segment Anything Model, we built an editor that makes it effortless to transform “designs in the wild”—whether it’s a vinyl sticker, a flyer taped to a pole, or a massive billboard—into reusable creative material. Instead of simply copying, our tool lets you extract structure, preserve style, and generate entirely new designs that blend elements from multiple sources.

Here’s how it works:
	1.	Image preprocessing: Using the state-of-the-art Segment Anything model, we transform photos of graphics and text -- in nearly any setting, with varying illuminations, angles, and orientation -- into clean masked outlines.
	2.	Element classification: Using PyTesseract and font classification algorithms, we identify text and font details, while regions are labeled as headings, body text, images, or decorations.
	3.	Style extraction: We try to pull the design’s “feel”—its color palette, gradients, textures, borders, margins, spacing, and alignment rules.
	4.	Template generation: With a reusable vector template (SVG/JSON), we align placeholders and style attributes aligned to the original. 
	5.	User interface: Through our editor, you can tweak placements, swap fonts, or adjust spacing, and export a polished output as PDF. This means you can easily swap in elements from different input sources, like stickers or text decals!

By bridging machine learning, computer vision, and design, our tool empowers anyone to engage with their cultural environment as both consumer and creator. Flyers on a street corner or stickers on a laptop no longer just advertise—they become living artifacts, remixable and generative in shaping new cultural expression.

This also uses `mps` for faster runtime on Mac. Please also download the MPS patch from here:

python -m pip install 'segment-anything @ git+https://github.com/DrSleep/segment-anything@cd507390ca9591951d0bfff2723d1f6be8792bb8'


Please run `brew install tesseract` and download the Segment Anything model checkpoint `sam_vit_h_4b8939.pth` from https://github.com/facebookresearch/segment-anything.


