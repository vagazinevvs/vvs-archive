import cv2
import os
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

def crop_card(image_path, debug_dir="debug_output"):
    """Crop photocard using robust contour bounding box."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to read image at: {image_path}")
    
    h, w = img.shape[:2]
    img_area = h * w
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 降低門檻或直接用 Otsu 二值化找出卡片主體
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 閉運算填補卡片內部雜訊
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    card_crop = None
    if contours:
        largest_c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest_c) > (img_area * MIN_AREA_PERCENT):
            # 取得最小外接矩形（支援旋轉）
            rect = cv2.minAreaRect(largest_c)
            box = cv2.boxPoints(rect)
            box = np.intp(box)
            
            warped = four_point_transform(img, box.astype("float32"))
            crop_h, crop_w = warped.shape[:2]
            ratio = min(crop_w, crop_h) / max(crop_w, crop_h)
            
            if (TARGET_ASPECT_RATIO - 0.25) <= ratio <= (TARGET_ASPECT_RATIO + 0.25):
                card_crop = warped

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
    
    font_size = max(40, int(output_height * 0.1))
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
    stamp_draw.text((padding + 1, padding + 1), watermark_text, fill=(0, 0, 0, 200), font=font)
    stamp_draw.text((padding, padding), watermark_text, fill=(255, 255, 255, 200), font=font)
    
    rotated_stamp = stamp.rotate(45, resample=Image.BICUBIC, expand=True)
    rw, rh = rotated_stamp.size
    
    for y in range(-rh, output_height + rh, int(rh * 0.95)):
        row_offset = (rw // 2) if ((y // int(rh * 0.95)) % 2 == 1) else 0
        for x in range(-rw + row_offset, output_width + rw, int(rw * 0.95)):
            watermark_layer.alpha_composite(rotated_stamp, (x, y))
            
    return Image.alpha_composite(base_img, watermark_layer).convert("RGB")

def debug_crop_card(image_path, debug_dir="debug_output"):
    """暫時的 Debug 函式：輸出邊緣檢測與輪廓抓取的中間過程圖片"""
    os.makedirs(debug_dir, exist_ok=True)
    img = cv2.imread(image_path)
    if img is None:
        print(f"無法讀取圖片: {image_path}")
        return
    
    h, w = img.shape[:2]
    img_area = h * w
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 120)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edged, kernel, iterations=2)
    
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    cv2.imwrite(os.path.join(debug_dir, f"{base_name}_gray.jpg"), gray)
    cv2.imwrite(os.path.join(debug_dir, f"{base_name}_blurred.jpg"), blurred)
    cv2.imwrite(os.path.join(debug_dir, f"{base_name}_edged.jpg"), edged)
    cv2.imwrite(os.path.join(debug_dir, f"{base_name}_dilated.jpg"), dilated)
    
    contours, _ = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    debug_contours_img = img.copy()
    for i, c in enumerate(contours[:5]):  # 繪製前 5 大輪廓
        area = cv2.contourArea(c)
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        
        # 綠色代表剛好 4 個頂點，紅色代表其他形狀
        color = (0, 255, 0) if len(approx) == 4 else (0, 0, 255)
        cv2.drawContours(debug_contours_img, [approx], -1, color, 3)
        print(f"輪廓 #{i}: 面積={area}, 頂點數={len(approx)}")
        
    cv2.imwrite(os.path.join(debug_dir, f"{base_name}_contours.jpg"), debug_contours_img)
    print(f"Debug 圖片已輸出至 {debug_dir}/ 資料夾")

if __name__ == "__main__":
    import os
    # 定義專案根目錄的上一層 (GitHub/)
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_img = os.path.join(root_dir, "raw_incoming", "swy-260712_2-hs.jpg")
    
    if os.path.exists(test_img):
        debug_crop_card(test_img)
    else:
        print(f"找不到測試圖片: {test_img}")