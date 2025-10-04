from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "images"
DOWNSCALE_DIR = ROOT / "images" / "input" / "downscaled"
RGBA_DIR = ROOT / "rgba_sam_outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
DOWNSCALE_DIR.mkdir(exist_ok=True)
RGBA_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

CORS(app, origins=["http://localhost:5173", "http://10.253.30.117:5173"])

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def downscale_image(img, max_dim=1600):
    height, width = img.shape[:2]
    if max(height, width) > max_dim:
        scale = max_dim / max(height, width)
        new_size = (int(width * scale), int(height * scale))
        img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
    return img

@app.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "no file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "no selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        out_dir = UPLOAD_DIR / "input" / "original"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename

        # Read file bytes (don't rely on file.stream position after save)
        file_bytes = file.read()
        if not file_bytes:
            return jsonify({"error": "empty file"}), 400

        # Write the original file bytes to disk
        with open(out_path, "wb") as f:
            f.write(file_bytes)

        # Decode image from bytes and create downscaled version
        arr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"error": "could not decode image"}), 400

        # ensure downscale dir exists (create parents)
        DOWNSCALE_DIR.mkdir(parents=True, exist_ok=True)
        img_small = downscale_image(img)
        cv2.imwrite(str(DOWNSCALE_DIR / filename), img_small)

        # Return the URL path relative to the /images endpoint
        rel_url = f"/images/input/original/{filename}"
        return jsonify({"filename": filename, "url": rel_url})
    return jsonify({"error": "invalid file type"}), 400

@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)

@app.route("/rgba/<path:filename>")
def serve_rgba(filename):
    return send_from_directory(str(RGBA_DIR), filename)


@app.route("/all_images", methods=["GET"])
def list_images():
    # Return only images located under the 'sam_shapes' directory (recursive).
    target_dir = UPLOAD_DIR / "sam_shapes"
    files = []
    for f in target_dir.rglob("*"):
        if f.is_file() and allowed_file(f.name):
            rel = f.relative_to(UPLOAD_DIR).as_posix()
            files.append(f"/images/{rel}")

    #print("Here are the sam_shapes image URLs:", files)
    return jsonify({"images": files})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5054)
