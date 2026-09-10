import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import math

TARGET_ASPECT_RATIO = 55.0 / 85.0  # Standard photocard aspect ratio (~0.647)
ASPECT_RATIO_TOLERANCE = 0.18      # Acceptable range: ~0.47 to ~0.83
MIN_AREA_PERCENT = 0.25            # Candidate card contour must take at least 25% of total image

def order_points(pts):
    """
    Orders coordinates: top-left, top-right, bottom-right, bottom-left.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    """
    Performs perspective deskew transform given 4 corner points.
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = max(int(height_a), int(height_b))

    dst = np.array([
        [0, 0],
        [max_w - 1, 0],
        [max_w - 1, max_h - 1],
        [0, max_h - 1]
    ], dtype="float32")

    m = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, m, (max_w, max_h))
    return warped

def center_crop_fallback(img):
    """
    Fallback: Center-crop original image using 55:85 photocard aspect ratio.
    Prevents false cropping on low contrast or complex textures like hair.
    """
    h, w = img.shape[:2]
    current_ratio = w / float(h)

    if current_ratio > TARGET_ASPECT_RATIO:
        # Image is wider than photocard: crop left and right
        target_w = int(h * TARGET_ASPECT_RATIO)
        offset_x = (w - target_w) // 2
        return img[:, offset_x:offset_x + target_w]
    else:
        # Image is taller than photocard: crop top and bottom
        target_h = int(w / TARGET_ASPECT_RATIO)
        offset_y = (h - target_h) // 2
        return img[offset_y:offset_y + target_h, :]

def detect_and_crop_photocard(image_path):
    """
    Detects photocard contour with perspective transform and fallback handling.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to read image at: {image_path}")

    h, w = img.shape[:2]
    img_area = h * w

    # Edge detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 120)

    # Dilate edges to close boundary gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edged, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    card_crop = None

    for c in contours:
        area = cv2.contourArea(c)
        if area < (img_area * MIN_AREA_PERCENT):
            break

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        # Look for 4-point convex polygon
        if len(approx) == 4 and cv2.isContourConvex(approx):
            pts = approx.reshape(4, 2)
            warped = four_point_transform(img, pts)
            crop_h, crop_w = warped.shape[:2]

            ratio = min(crop_w, crop_h) / max(crop_w, crop_h)
            if (TARGET_ASPECT_RATIO - ASPECT_RATIO_TOLERANCE) <= ratio <= (TARGET_ASPECT_RATIO + ASPECT_RATIO_TOLERANCE):
                card_crop = warped
                break

    # If detection failed or triggered false small region, fallback to center crop
    if card_crop is None:
        card_crop = center_crop_fallback(img)

    # Force vertical orientation (portrait)
    if card_crop.shape[1] > card_crop.shape[0]:
        card_crop = cv2.rotate(card_crop, cv2.ROTATE_90_CLOCKWISE)

    return card_crop

def apply_repeating_watermark(bgr_image, watermark_text="VVS ARCHIVE", output_height=1200):
    """
    Resizes image to target resolution and overlays repeating 45-degree angled text watermark.
    """
    # Resize to standard high-res height while preserving ratio
    h, w = bgr_image.shape[:2]
    output_width = int(output_height * (w / float(h)))
    resized_bgr = cv2.resize(bgr_image, (output_width, output_height), interpolation=cv2.INTER_LANCZOS4)

    # Convert BGR (OpenCV) to RGBA (Pillow)
    rgb = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2RGB)
    base_img = Image.fromarray(rgb).convert("RGBA")

    # Transparent layer for diagonal watermarks
    watermark_layer = Image.new("RGBA", (output_width, output_height), (0, 0, 0, 0))

    # Font configuration
    font_size = max(18, int(output_height * 0.026))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except IOError:
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

    # Create single rotated text stamp
    # Text bounds
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), watermark_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = 20
    stamp_w = text_w + padding * 2
    stamp_h = text_h + padding * 2

    # Draw semi-transparent white text with soft dark outline for contrast
    stamp = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    stamp_draw = ImageDraw.Draw(stamp)
    
    # Text shadow/stroke
    stamp_draw.text((padding + 1, padding + 1), watermark_text, fill=(0, 0, 0, 50), font=font)
    # Primary watermark text (opacity ~110/255)
    stamp_draw.text((padding, padding), watermark_text, fill=(255, 255, 255, 50), font=font)

    # Rotate 45 degrees
    rotated_stamp = stamp.rotate(45, resample=Image.BICUBIC, expand=True)
    rw, rh = rotated_stamp.size

    # Tile stamp across full canvas 
    spacing_x = int(rw * 0.95)
    spacing_y = int(rh * 0.95)

    for y in range(-rh, output_height + rh, spacing_y):
        # Stagger alternate rows for clean honeycomb tiling
        row_offset = (rw // 2) if ((y // spacing_y) % 2 == 1) else 0
        for x in range(-rw + row_offset, output_width + rw, spacing_x):
            watermark_layer.alpha_composite(rotated_stamp, (x, y))

    final_image = Image.alpha_composite(base_img, watermark_layer).convert("RGB")
    return final_image

def process_card_image(input_path, output_path):
    """
    End-to-end processing pipeline: detect/crop -> watermark -> webp output.
    """
    cropped = detect_and_crop_photocard(input_path)
    final_card = apply_repeating_watermark(cropped, watermark_text="VVS ARCHIVE")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_card.save(output_path, "WEBP", quality=90, method=6)
    print(f"[Done] Saved: {output_path}")

if __name__ == "__main__":
    # Example standalone run
    test_input = "260510_2pm_sk.jpg"
    test_output = "public/cards/260510_2pm_sk.webp"
    if os.path.exists(test_input):
        process_card_image(test_input, test_output)