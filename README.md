# Hack-Harvard-2025: Promosaic

"Good artists copy, great artists steal".

Fulfill your wildest copy dreams! Using Segment Anything, our mobile editor makes it a breeze to edit designs in the wild. Anything, from streetpost signs to billboard advertisments, is fair game. Our powerful editor not only allows you to add text in the style of the original image, but also allows you to combine structured elements from different sources, making something that is entirely your own.

	1.	Image preprocessing
	•	Detect edges, bounding boxes, align orientation
	•	Segment into regions: text blocks, images, backgrounds
	2.	Element classification
	•	Use OCR to detect text, fonts
	•	Label boxes: headings, subheadings, body text, image, decoration
	3.	Style extraction
	•	Extract color palette, gradients, textures, border styles
	•	Infer margins, spacing, alignment rules
	4.	Template generation
	•	Create a vector / layout template (SVG, JSON) with placeholder boxes matching the structure
	•	Assign style attributes (colors, fonts) to those placeholder boxes
	5.	User edit / refinement UI
	•	Let user tweak placement, swap fonts, adjust spacing
	•	Export final design (SVG, PDF, etc.)
	6.	Template reuse
	•	Save the generated template for future use

This also uses `mps` for faster runtime on Mac. Please also download the MPS patch from here:

python -m pip install 'segment-anything @ git+https://github.com/DrSleep/segment-anything@cd507390ca9591951d0bfff2723d1f6be8792bb8'


Please run `brew install tesseract` and download the Segment Anything model checkpoint `sam_vit_h_4b8939.pth` from https://github.com/facebookresearch/segment-anything.


