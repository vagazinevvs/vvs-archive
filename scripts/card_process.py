import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TARGET_ASPECT_RATIO = 55.0 / 85.0
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

def apply_white_balance(bgr_img):
    h, w = bgr_img.shape[:2]
    corner_h = int(h * 0.12)
    corner_w = int(w * 0.12)
    
    corners = {
        "tl": bgr_img[0:corner_h, 0:corner_w],
        "tr": bgr_img[0:corner_h, w-corner_w:w],
        "bl": bgr_img[h-corner_h:h, 0:corner_w],
        "br": bgr_img[h-corner_h:h, w-corner_w:w]
    }
    
    best_bg = None
    max_score = -float('inf')
    
    for key, patch in corners.items():
        b_mean = np.mean(patch[:, :, 0])
        g_mean = np.mean(patch[:, :, 1])
        r_mean = np.mean(patch[:, :, 2])
        
        brightness = (b_mean + g_mean + r_mean) / 3.0
        color_std = np.std([b_mean, g_mean, r_mean])
        score = brightness - (color_std * 0.5)
        
        if score > max_score:
            max_score = score
            best_bg = patch
            
    if best_bg is None:
        best_bg = corners["tr"]
        
    average_b = np.mean(best_bg[:, :, 0])
    average_g = np.mean(best_bg[:, :, 1])
    average_r = np.mean(best_bg[:, :, 2])
    average = (average_b + average_g + average_r) / 3.0
    
    result = bgr_img.astype(np.float32)
    if average_b > 0: result[:, :, 0] *= (average / average_b)
    if average_g > 0: result[:, :, 1] *= (average / average_g)
    if average_r > 0: result[:, :, 2] *= (average / average_r)
    
    return np.clip(result, 0, 255).astype(np.uint8)

def crop_card(image_input, debug_dir=None):
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
    else:
        img = image_input
        
    if img is None:
        raise ValueError("Unable to read image for cropping")
    
    h, w = img.shape[:2]
    img_area = h * w
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 11, 35, 35)
    edged = cv2.Canny(filtered, 15, 60)
    
    kernel = np.ones((21, 11), np.uint8)
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(os.path.join(debug_dir, "diag_filtered.jpg"), filtered)
        cv2.imwrite(os.path.join(debug_dir, "diag_edged.jpg"), edged)
        cv2.imwrite(os.path.join(debug_dir, "diag_closed.jpg"), closed)
    
    contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    card_crop = None
    
    if contours:
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for c in contours:
            area = cv2.contourArea(c)
            if area > (img_area * 0.10):
                hull = cv2.convexHull(c)
                rect = cv2.minAreaRect(hull)
                box = cv2.boxPoints(rect)
                pts = box.astype("float32")
                
                w_box = np.linalg.norm(pts[0] - pts[1])
                h_box = np.linalg.norm(pts[1] - pts[2])
                if w_box == 0 or h_box == 0:
                    continue
                
                ratio = min(w_box, h_box) / max(w_box, h_box)
                
                if 0.5 <= ratio <= 0.8:
                    center = np.mean(pts, axis=0)
                    # 調整為 0.99 以完美貼合實際邊緣
                    pts = center + (pts - center) * 0.99
                    
                    card_crop = four_point_transform(img, pts)
                    break

    if card_crop is None:
        target_aspect = 55.0 / 85.0
        if (w / h) > target_aspect:
            crop_h = int(h * 0.85)
            crop_w = int(crop_h * target_aspect)
        else:
            crop_w = int(w * 0.85)
            crop_h = int(crop_w / target_aspect)
            
        start_x = (w - crop_w) // 2
        start_y = (h - crop_h) // 2
        card_crop = img[start_y:start_y+crop_h, start_x:start_x+crop_w]
        
    if card_crop.shape[1] > card_crop.shape[0]:
        card_crop = cv2.rotate(card_crop, cv2.ROTATE_90_CLOCKWISE)
        
    return card_crop

def apply_watermark(bgr_image, watermark_text="VVS ARCHIVE"):
    output_height, output_width = bgr_image.shape[:2]
    
    rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
    base_img = Image.fromarray(rgb).convert("RGBA")
    watermark_layer = Image.new("RGBA", (output_width, output_height), (0, 0, 0, 0))
    
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DejaVuSans-Bold.ttf")
    font_size = max(30, int(output_height * 0.01))
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
    
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), watermark_text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    padding, stamp_w, stamp_h = 20, text_w + 40, text_h + 40
    stamp = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    stamp_draw = ImageDraw.Draw(stamp)
    stamp_draw.text((padding + 1, padding + 1), watermark_text, fill=(0, 0, 0, 50), font=font)
    stamp_draw.text((padding, padding), watermark_text, fill=(255, 255, 255,50), font=font)
    
    rotated_stamp = stamp.rotate(45, resample=Image.BICUBIC, expand=True)
    rw, rh = rotated_stamp.size
    
    for y in range(-rh, output_height + rh, int(rh * 0.95)):
        row_offset = (rw // 2) if ((y // int(rh * 0.95)) % 2 == 1) else 0
        for x in range(-rw + row_offset, output_width + rw, int(rw * 0.95)):
            watermark_layer.alpha_composite(rotated_stamp, (x, y))
            
    return Image.alpha_composite(base_img, watermark_layer).convert("RGB")

def process_card_image(input_path, card_id, output_dir="public/cards"):
    try:
        raw_img = cv2.imread(input_path)
        if raw_img is None:
        
            raise ValueError(f"Unable to read image at: {input_path}")
        
        balanced_bgr = apply_white_balance(raw_img)
        cropped_bgr = crop_card(balanced_bgr)
        
        alpha = 1.1
        beta = 15
        bright_bgr = cv2.convertScaleAbs(cropped_bgr, alpha=alpha, beta=beta)
        
        standardized_bgr = cv2.resize(bright_bgr, (800, 1200), interpolation=cv2.INTER_LANCZOS4)
        final_pil = apply_watermark(standardized_bgr)
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{card_id}.webp")
        final_pil.save(output_path, "WEBP", quality=85)
        return f"./cards/{card_id}.webp"
    except Exception as e:
        print(f"Error processing card image {card_id}: {e}")
        return None
