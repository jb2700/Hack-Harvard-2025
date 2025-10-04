import cv2
import numpy as np
from PIL import Image
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DEBUG = True
debug_dir = ROOT / "images" / "debug"

def portrait(img: np.ndarray) -> np.ndarray:
    """Ensure image is in portrait orientation."""
    h, w = img.shape[:2]
    if h >= w:
        return img
    else:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
def posterize(img_rgb, k=5):
    Z = img_rgb.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    attempts = 4
    flags = cv2.KMEANS_RANDOM_CENTERS
    _, label, center = cv2.kmeans(Z, k, None, criteria, attempts, flags)
    center = np.uint8(center)
    res = center[label.flatten()]
    poster = res.reshape((img_rgb.shape))
    return poster

def affine_crop(img : np.ndarray, img_filename : str) -> np.ndarray:
    """Detect a large quadrilateral (banner) and warp to rectangle."""
    img_filename = Path(img_filename).stem

    # 1) produce closed edges from the original blurred image
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Canny edge detection
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
    # Kernel for edge closing
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    # 2) posterize the image to reduce background clutter and make the poster region pop
    poster = posterize(img, k=10)
    poster_gray = cv2.cvtColor(poster, cv2.COLOR_RGB2GRAY)
    poster_blur = cv2.GaussianBlur(poster_gray, (5, 5), 0)
    edges_p = cv2.Canny(poster_blur, 50, 150, apertureSize=3)

    closed_edges_p = cv2.morphologyEx(edges_p, cv2.MORPH_CLOSE, kernel)
    contours1, _ = cv2.findContours(closed_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours2, _ = cv2.findContours(closed_edges_p, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    all_contours = []
    if contours1:
        all_contours.extend(contours1)
    if contours2:
        all_contours.extend(contours2)

    # Sort combined contours and save debug images
    all_contours = sorted(all_contours, key=cv2.contourArea, reverse=True)
    if DEBUG == True:
        debug_dir = ROOT / "images" / "debug"
        debug_dir.mkdir(exist_ok=True, parents=True)
        Image.fromarray(edges).save(debug_dir / f"{img_filename}_edges_raw.png")
        Image.fromarray(closed_edges).save(debug_dir / f"{img_filename}_edges_closed.png")
        Image.fromarray(poster).save(debug_dir / f"{img_filename}_posterized.png")
        Image.fromarray(edges_p).save(debug_dir / f"{img_filename}_edges_poster.png")
        Image.fromarray(closed_edges_p).save(debug_dir / f"{img_filename}_edges_poster_closed.png")

    # Contour to approxPolyDP
    for contour in all_contours[:1]:
        peri = cv2.arcLength(contour, True)
        # try a small sweep of epsilons to robustly find 4 points
        approx = None
        for eps_ratio in (0.005, 0.01, 0.02, 0.04):
            candidate = cv2.approxPolyDP(contour, eps_ratio * peri, True)
            if len(candidate) == 4:
                approx = candidate
                break
        if approx is not None:
            # Order the points for perspective transform
            approx = approx.reshape(4, 2)
            # Order points: top-left, top-right, bottom-right, bottom-left
            rect = np.zeros((4, 2), dtype=np.float32)
            s = approx.sum(axis=1)
            rect[0] = approx[np.argmin(s)]  # top-left
            rect[2] = approx[np.argmax(s)]  # bottom-right
            diff = np.diff(approx, axis=1)
            rect[1] = approx[np.argmin(diff)]  # top-right
            rect[3] = approx[np.argmax(diff)]  # bottom-left
            
            # Calculate dimensions for the output rectangle
            width_a = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + ((rect[2][1] - rect[3][1]) ** 2))
            width_b = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
            max_width = max(int(width_a), int(width_b))
            
            height_a = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + ((rect[1][1] - rect[2][1]) ** 2))
            height_b = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + ((rect[0][1] - rect[3][1]) ** 2))
            max_height = max(int(height_a), int(height_b))
            
            # Define destination points for the rectangle
            dst = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype=np.float32)
            
            # Perform perspective transform
            matrix = cv2.getPerspectiveTransform(rect, dst)
            img = cv2.warpPerspective(img, matrix, (max_width, max_height))
            
            if True:
                debug_dir = ROOT / "images" / "debug"
                debug_dir.mkdir(exist_ok=True, parents=True)
                img = portrait(img)
                Image.fromarray(img).save(debug_dir / f'cropped_{img_filename}.png')
        else:
            debug_dir = ROOT / "images" / "debug"
            print(f"Warning: No quadrilateral detected for {img_filename}, returning original image.")
            img = portrait(img)
            Image.fromarray(img).save(debug_dir / f'cropped_{img_filename}.png')
    return img
