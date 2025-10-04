from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "images"
RGBA_DIR = ROOT / "rgba_sam_outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
RGBA_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}



app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

CORS(app, origins=["http://localhost:5173"])


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "no file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "no selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        out_path = UPLOAD_DIR / filename
        file.save(str(out_path))
        return jsonify({"filename": filename, "url": f"/images/{filename}"})
    return jsonify({"error": "invalid file type"}), 400


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)


@app.route("/rgba/<path:filename>")
def serve_rgba(filename):
    return send_from_directory(str(RGBA_DIR), filename)


@app.route("/all_images", methods=["GET"])
def list_images():
    files = [f.name for f in UPLOAD_DIR.iterdir() if f.is_file() and allowed_file(f.name)]
    image_urls = [f"/images/{file}" for file in files]
    print("Here are the image URLs:", image_urls)
    return jsonify({"images": image_urls})

if __name__ == "__main__":
    app.run(debug=True, port=5054)
