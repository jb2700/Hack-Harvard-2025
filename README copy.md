# Run Segment Anything (SAM) and layer-wise vectorization on polar.jpeg

This workspace contains tools to run Segment Anything (SAM) and to perform layer-wise image vectorization of `polar.jpeg`.

Environment (macOS, zsh)

1. Create a Python environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Segment Anything (optional)

If you want to run SAM, download a checkpoint and place it next to the scripts. Recommended: `sam_vit_h_4b8939.pth` (ViT-H, ~1GB) for high-quality masks, or a ViT-B checkpoint for faster runs.

Example (replace URL with the official release link):

```bash
curl -L -o sam_vit_h_4b8939.pth "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
```

Run SAM:

```bash
python run_sam.py
# or faster (prefers ViT-B checkpoint if available):
python run_sam_fast.py
```

Outputs will be under `sam_outputs/` or `sam_outputs_fast/`.

Layer-wise vectorization

`vectorize_layers.py` quantizes the image into color layers, extracts contours for each layer, and produces an SVG and a raster preview.

Basic example:

```bash
python vectorize_layers.py --input polar.jpeg --colors 6 --min-area 200 --output polar_vector
```

This creates `polar_vector.svg` and `polar_vector_preview.png`.

Control polygon complexity

By default the script simplifies contours to reduce vertex count. To produce polygons with more sides (higher fidelity), use the following flags:

- `--approx-eps`: contour simplification epsilon. If < 1.0 it's a fraction of the contour arc length (e.g. `0.01` = 1%). Use smaller values like `0.002` or `0.001` to keep more vertices. If >= 1.0 it's an absolute pixel epsilon.
- `--min-epsilon`: minimum epsilon in pixels when `--approx-eps` is fractional (default `1.0`).
- `--no-simplify`: disable simplification entirely and keep the raw contour points (may create very large SVGs).

Examples (higher polygon fidelity):

```bash
python vectorize_layers.py --input polar.jpeg --colors 6 --min-area 200 --approx-eps 0.002 --output polar_vector_fine

python vectorize_layers.py --input polar.jpeg --colors 6 --min-area 200 --no-simplify --output polar_vector_raw
```

Tradeoffs:
- Smaller `--approx-eps` values and `--no-simplify` produce more accurate shapes but increase SVG size and vertex count.
- For smooth curves consider post-processing with potrace/autotrace or converting polygon chains to Béziers in a vector editor.
# Run Segment Anything (SAM) on polar.jpeg

This small project shows how to run Facebook Research's Segment Anything (SAM) model on the image `polar.jpeg` in this folder, and also includes a simple layer-wise image vectorization tool.

Environment (macOS, zsh)

1. Create a Python environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. (Optional for SAM) Download a SAM checkpoint and place it next to the scripts. Recommended: `sam_vit_h_4b8939.pth` (ViT-H) for high-quality masks, or a ViT-B checkpoint for faster runs.

Example (replace URL with the official release link):

```bash
curl -L -o sam_vit_h_4b8939.pth "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
```

3. Run SAM (automatic masks)

```bash
python run_sam.py
# or faster (prefers ViT-B checkpoint if available):
python run_sam_fast.py
```

Outputs will be under `sam_outputs/` or `sam_outputs_fast/`:
# Run Segment Anything (SAM) and layer-wise vectorization on polar.jpeg

This workspace contains tools to run Segment Anything (SAM) and to perform layer-wise image vectorization of `polar.jpeg`.

Environment (macOS, zsh)

1. Create a Python environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Segment Anything (optional)

If you want to run SAM, download a checkpoint and place it next to the scripts. Recommended: `sam_vit_h_4b8939.pth` (ViT-H, ~1GB) for high-quality masks, or a ViT-B checkpoint for faster runs.

Example (replace URL with the official release link):

```bash
curl -L -o sam_vit_h_4b8939.pth "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
```

Run SAM:

```bash
python run_sam.py
# or faster (prefers ViT-B checkpoint if available):
python run_sam_fast.py
```

Outputs will be under `sam_outputs/` or `sam_outputs_fast/`.

Layer-wise vectorization

`vectorize_layers.py` quantizes the image into color layers, extracts contours for each layer, and produces an SVG and a raster preview.

Basic example:

```bash
python vectorize_layers.py --input polar.jpeg --colors 6 --min-area 200 --output polar_vector
```

This creates `polar_vector.svg` and `polar_vector_preview.png`.

Color selection modes

The script supports multiple ways to pick colors/layers:

- Default: k-means on all pixels (`--colors`).
- Hue-prioritized: `--use-hue` builds a hue histogram of sufficiently saturated pixels and picks top hue peaks. Use `--sat-thresh` and `--hue-sat-power` to tune.
- Saturation-prioritized: `--use-sat` samples the top fraction of saturated pixels and runs k-means on them. Use `--sat-top-frac` to control the fraction.

Examples:

```bash
# Hue-prioritized (favor prominent hues):
python vectorize_layers.py --input polar.jpeg --colors 8 --use-hue --sat-thresh 30 --hue-sat-power 2.0 --output polar_vector_hue

# Saturation-prioritized (k-means on most-saturated pixels):
python vectorize_layers.py --input polar.jpeg --colors 8 --use-sat --sat-top-frac 0.1 --output polar_vector_sat
```

Control polygon complexity

By default the script simplifies contours to reduce vertex count. To produce polygons with more sides (higher fidelity), use:

- `--approx-eps` (smaller → more vertices), `--min-epsilon`, or `--no-simplify`.

Example (fine polygons):

```bash
python vectorize_layers.py --input polar.jpeg --colors 6 --use-sat --sat-top-frac 0.1 --approx-eps 0.002 --output polar_vector_fine
```

Tradeoffs:
- Smaller `--approx-eps` and `--no-simplify` create larger SVGs but more accurate shapes.
- Hue/saturation modes help prioritize visually vivid colors; try tuning `--hue-sat-power` or `--sat-top-frac` for your image.
