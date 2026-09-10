import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TARGET_ASPECT_RATIO = 55.0 / 85.0
ASPECT_RATIO_TOLERANCE = 0.18
MIN_AREA_PERCENT = 0.25

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = max(int(width_a), int(width_b))
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = max(int(height_a), int(height_b))
    dst = np.array([[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]], dtype="float32")
    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, m, (max_w, max_h))

def center_crop_fallback(img):
    h, w = img.shape[:2]
    current_ratio = w / float(h)
    if current_ratio > TARGET_ASPECT_RATIO:
        target_w = int(h * TARGET_ASPECT_RATIO)
        offset_x = (w - target_w) // 2
        return img[:, offset_x:offset_x + target_w]
    else:
        target_h = int(w / TARGET_ASPECT_RATIO)
        offset_y = (h - target_h) // 2
        return img[offset_y:offset_y + target_h, :]

def apply_white_balance(bgr_img):
    """Apply simple Gray World white balance algorithm."""
    result = bgr_img.astype(np.float32)
    average_b = np.mean(result[:, :, 0])
    average_g = np.mean(result[:, :, 1])
    average_r = np.mean(result[:, :, 2])
    average = (average_b + average_g + average_r) / 3.0
    
    if average_b > 0: result[:, :, 0] *= (average / average_b)
    if average_g > 0: result[:, :, 1] *= (average / average_g)
    if average_r > 0: result[:, :, 2] *= (average / average_r)
    
    return np.clip(result, 0, 255).astype(np.uint8)

def crop_card(image_path):
    """Crop photocard from raw image."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to read image at: {image_path}")
    
    h, w = img.shape[:2]
    img_area = h * w
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 120)
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
        if len(approx) == 4 and cv2.isContourConvex(approx):
            pts = approx.reshape(4, 2)
            warped = four_point_transform(img, pts)
            crop_h, crop_w = warped.shape[:2]
            ratio = min(crop_w, crop_h) / max(crop_w, crop_h)
            if (TARGET_ASPECT_RATIO - ASPECT_RATIO_TOLERANCE) <= ratio <= (TARGET_ASPECT_RATIO + ASPECT_RATIO_TOLERANCE):
                card_crop = warped
                break
                
    if card_crop is None:
        card_crop = center_crop_fallback(img)
    if card_crop.shape[1] > card_crop.shape[0]:
        card_crop = cv2.rotate(card_crop, cv2.ROTATE_90_CLOCKWISE)
        
    return card_crop

def apply_watermark(bgr_image, watermark_text="VVS ARCHIVE", output_height=1200):
    """Apply repeating diagonal watermark to the image."""
    h, w = bgr_image.shape[:2]
    output_width = int(output_height * (w / float(h)))
    resized_bgr = cv2.resize(bgr_image, (output_width, output_height), interpolation=cv2.INTER_LANCZOS4)
    balanced_bgr = apply_white_balance(resized_bgr)
    
    rgb = cv2.cvtColor(balanced_bgr, cv2.COLOR_BGR2RGB)
    base_img = Image.fromarray(rgb).convert("RGBA")
    watermark_layer = Image.new("RGBA", (output_width, output_height), (0, 0, 0, 0))
    
    font_size = max(18, int(output_height * 0.026))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
    
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), watermark_text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    padding, stamp_w, stamp_h = 20, text_w + 40, text_h + 40
    stamp = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    stamp_draw = ImageDraw.Draw(stamp)
    stamp_draw.text((padding + 1, padding + 1), watermark_text, fill=(0, 0, 0, 50), font=font)
    stamp_draw.text((padding, padding), watermark_text, fill=(255, 255, 255, 50), font=font)
    
    rotated_stamp = stamp.rotate(45, resample=Image.BICUBIC, expand=True)
    rw, rh = rotated_stamp.size
    
    for y in range(-rh, output_height + rh, int(rh * 0.95)):
        row_offset = (rw // 2) if ((y // int(rh * 0.95)) % 2 == 1) else 0
        for x in range(-rw + row_offset, output_width + rw, int(rw * 0.95)):
            watermark_layer.alpha_composite(rotated_stamp, (x, y))
            
    return Image.alpha_composite(base_img, watermark_layer).convert("RGB")