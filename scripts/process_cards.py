import os
import re
import json
import requests
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import gspread
from google.oauth2.service_account import Credentials

TARGET_WIDTH = 600
TARGET_HEIGHT = 927
TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT

CARDS_DIR = os.path.join("public", "cards")
OUTPUT_JSON = os.path.join("public", "cards.json")


def extract_drive_id(url: str) -> str:
    """Extract unique file ID from Google Drive URLs."""
    match = re.search(r"(?:id=|\/d\/)([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else ""


def download_image(url: str) -> np.ndarray:
    """Download image and return OpenCV BGR image array."""
    file_id = extract_drive_id(url)
    fetch_url = f"https://lh3.googleusercontent.com/d/{file_id}" if file_id else url

    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(fetch_url, headers=headers, timeout=30)
    resp.raise_for_status()

    image_arr = np.frombuffer(resp.content, np.uint8)
    return cv2.imdecode(image_arr, cv2.IMREAD_COLOR)


def auto_detect_and_crop(img: np.ndarray) -> np.ndarray:
    """Detect card contour against solid/dark background and crop tightly."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Sample corners to determine background luminosity
    corner_samples = [
        int(gray[10, 10]),
        int(gray[10, w - 11]),
        int(gray[h - 11, 10]),
        int(gray[h - 11, w - 11]),
    ]
    bg_val = np.median(corner_samples)

    # Segment card from solid background
    if bg_val < 40:  # Dark / Black background
        _, thresh = cv2.threshold(gray, int(bg_val + 25), 255, cv2.THRESH_BINARY)
    elif bg_val > 215:  # White background
        _, thresh = cv2.threshold(gray, int(bg_val - 25), 255, cv2.THRESH_BINARY_INV)
    else:  # Fallback to Otsu thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Fill internal dark regions (hair, ties, shadows) using morphological closing
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_area = w * h

    card_box = None
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:3]:
        area = cv2.contourArea(cnt)
        if area > (img_area * 0.20):
            bx, by, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / float(bh)
            if 0.45 <= aspect <= 0.85:
                card_box = (bx, by, bw, bh)
                break

    # If photocard bounding box identified, crop it
    if card_box:
        bx, by, bw, bh = card_box
        # Add 2px margin inward to strip residual background bleeding
        bx = min(bx + 2, w)
        by = min(by + 2, h)
        bw = max(bw - 4, 1)
        bh = max(bh - 4, 1)
        return img[by:by + bh, bx:bx + bw]

    # Proportional center-crop fallback
    current_ratio = w / h
    if current_ratio > TARGET_RATIO:
        new_w = int(h * TARGET_RATIO)
        start_x = (w - new_w) // 2
        return img[:, start_x:start_x + new_w]
    else:
        new_h = int(w / TARGET_RATIO)
        start_y = (h - new_h) // 2
        return img[start_y:start_y + new_h, :]

def order_points(pts: np.ndarray) -> np.ndarray:
    """Sort 4 corner points in order: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    
    # Top-left has smallest sum, bottom-right has largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Top-right has smallest diff (x - y or y - x), bottom-left has largest diff
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect
def order_points(pts: np.ndarray) -> np.ndarray:
    """Sort 4 corner points in order: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    
    # Top-left has smallest sum, bottom-right has largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Top-right has smallest diff (x - y or y - x), bottom-left has largest diff
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def auto_detect_and_crop(img: np.ndarray) -> np.ndarray:
    """Detect skewed card contour, correct perspective distortion, and warp to straight frame."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Background segmentation
    corner_samples = [
        int(gray[10, 10]),
        int(gray[10, w - 11]),
        int(gray[h - 11, 10]),
        int(gray[h - 11, w - 11]),
    ]
    bg_val = np.median(corner_samples)

    if bg_val < 40:
        _, thresh = cv2.threshold(gray, int(bg_val + 25), 255, cv2.THRESH_BINARY)
    elif bg_val > 215:
        _, thresh = cv2.threshold(gray, int(bg_val - 25), 255, cv2.THRESH_BINARY_INV)
    else:
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 2. Morphological closing to seal internal regions
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_area = w * h

    target_cnt = None
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:3]:
        area = cv2.contourArea(cnt)
        if area > (img_area * 0.20):
            target_cnt = cnt
            break

    # 3. Perspective correction via 4-point transform
    if target_cnt is not None:
        # Approximate contour to polygon
        peri = cv2.arcLength(target_cnt, True)
        approx = cv2.approxPolyDP(target_cnt, 0.03 * peri, True)

        # If clean 4-corner polygon found, use it; otherwise fallback to minAreaRect
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype("float32")
        else:
            rect = cv2.minAreaRect(target_cnt)
            pts = cv2.boxPoints(rect).astype("float32")

        ordered_pts = order_points(pts)

        # Define destination canvas coordinates (600x927)
        dst_pts = np.array(
            [
                [0, 0],
                [TARGET_WIDTH - 1, 0],
                [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
                [0, TARGET_HEIGHT - 1],
            ],
            dtype="float32",
        )

        # Compute homography matrix and warp
        matrix = cv2.getPerspectiveTransform(ordered_pts, dst_pts)
        warped = cv2.warpPerspective(img, matrix, (TARGET_WIDTH, TARGET_HEIGHT))
        return warped

    # Fallback: Center crop if contour detection fails
    current_ratio = w / h
    if current_ratio > TARGET_RATIO:
        new_w = int(h * TARGET_RATIO)
        start_x = (w - new_w) // 2
        cropped = img[:, start_x:start_x + new_w]
    else:
        new_h = int(w / TARGET_RATIO)
        start_y = (h - new_h) // 2
        cropped = img[start_y:start_y + new_h, :]

    return cv2.resize(cropped, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_LANCZOS4)
def apply_white_balance(img: np.ndarray) -> np.ndarray:
    """Correct color cast using Gray-World algorithm on cropped card."""
    b, g, r = cv2.split(img)
    mean_b = np.mean(b)
    mean_g = np.mean(g)
    mean_r = np.mean(r)
    mean_gray = (mean_b + mean_g + mean_r) / 3.0

    kb = mean_gray / (mean_b + 1e-5)
    kg = mean_gray / (mean_g + 1e-5)
    kr = mean_gray / (mean_r + 1e-5)

    b = np.clip(b * kb, 0, 255).astype(np.uint8)
    g = np.clip(g * kg, 0, 255).astype(np.uint8)
    r = np.clip(r * kr, 0, 255).astype(np.uint8)

    return cv2.merge([b, g, r])


def add_watermark(pil_img: Image.Image, text: str = "VVS ARCHIVE") -> Image.Image:
    """Apply a repeating 45-degree diagonal watermark across the entire image."""
    base = pil_img.convert("RGBA")
    w, h = base.size

    # Create an oversized canvas to cover rotation without black/empty borders
    diag = int(np.sqrt(w**2 + h**2)) + 150
    watermark_layer = Image.new("RGBA", (diag, diag), (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark_layer)

    font_size = 25
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

    # Calculate text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Tile step intervals
    spacing_x = text_w + 70
    spacing_y = text_h + 55

    # Low opacity white text (alpha=50) to protect cards without obscuring face
    text_color = (255, 255, 255, 50)

    # Tile pattern with staggered offset
    for row_idx, y in enumerate(range(0, diag, spacing_y)):
        row_offset = (spacing_x // 2) if (row_idx % 2 == 1) else 0
        for x in range(-spacing_x, diag + spacing_x, spacing_x):
            draw.text((x + row_offset, y), text, font=font, fill=text_color)

    # Rotate 45 degrees around center
    rotated = watermark_layer.rotate(45, resample=Image.BICUBIC)

    # Crop center back to original image dimensions
    center_x, center_y = diag // 2, diag // 2
    left = center_x - (w // 2)
    top = center_y - (h // 2)
    cropped_watermark = rotated.crop((left, top, left + w, top + h))

    # Composite watermark onto base image
    watermarked = Image.alpha_composite(base, cropped_watermark)
    return watermarked.convert("RGB")

def process_image(img: np.ndarray, output_path: str):
    """Run pipeline stages: Deskew/Crop -> White Balance -> Watermark -> WebP."""
    # 1. Perspective correction, crop, and resize in one step
    straightened = auto_detect_and_crop(img)

    # 2. Correct white balance on the straightened card
    wb_img = apply_white_balance(straightened)

    # 3. Add watermark and export to WebP
    rgb_img = cv2.cvtColor(wb_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_img)
    watermarked_img = add_watermark(pil_img, text="VVS ARCHIVE")
    watermarked_img.save(output_path, "WEBP", quality=85, method=6)


def main():
    sa_json = os.environ.get("GCP_SA_KEY")
    sheet_id = os.environ.get("SPREADSHEET_ID")
    if not sa_json or not sheet_id:
        raise ValueError("Missing GCP_SA_KEY or SPREADSHEET_ID in environment.")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    submit_ws = sh.worksheet("submit")
    cards_ws = sh.worksheet("cards")

    # 取得 submit 分頁的所有資料（含標題列）
    all_rows = submit_ws.get_all_values()
    if len(all_rows) <= 1:
        print("No records found in 'submit' sheet.")
        return

    headers = all_rows[0]
    try:
        status_col_idx = headers.index("status") + 1  # 轉為 1-based 索引
    except ValueError:
        raise ValueError("Cannot find 'status' column in 'submit' sheet.")

    cards_headers = cards_ws.row_values(1)
    rows_to_append = []
    cells_to_update = []

    # 遍歷資料列（從第 2 列開始，row_idx 為 1-based）
    for row_idx, row_values in enumerate(all_rows[1:], start=2):
        row = dict(zip(headers, row_values))
        status = str(row.get("status", "")).strip().lower()

        # 只處理狀態為 "process" 的列
        if status != "process":
            continue

        card_id = str(row.get("id", "")).strip()
        name = str(row.get("name", "")).strip()
        raw_url = str(row.get("imageUrl", "")).strip()

        if not card_id or not name:
            continue

        target_webp = os.path.join(CARDS_DIR, f"{card_id}.webp")
        local_url = f"./cards/{card_id}.webp"

        print(f"Processing: {card_id} ({name})...")
        try:
            img = download_image(raw_url)
            if img is not None:
                process_image(img, target_webp)
            else:
                continue
        except Exception as e:
            print(f"Error processing {card_id}: {e}")
            continue

        # 組裝寫入 cards 分頁的資料
        row_dict = dict(row)
        row_dict["imageUrl"] = local_url
        aligned_row = [str(row_dict.get(h, "")) for h in cards_headers]
        rows_to_append.append(aligned_row)

        # 標記需要將 status 更新為 archived 的儲存格
        cells_to_update.append(gspread.Cell(row=row_idx, col=status_col_idx, value="archived"))

    # 批次寫入 cards 分頁
    if rows_to_append:
        cards_ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")
        # 批次將 submit 對應列改為 archived
        submit_ws.update_cells(cells_to_update)
        print(f"Appended {len(rows_to_append)} rows to 'cards' and updated status to 'archived'.")


if __name__ == "__main__":
    main()