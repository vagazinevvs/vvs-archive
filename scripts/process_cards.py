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


def order_points(pts: np.ndarray) -> np.ndarray:
    """Sort 4 corner points in order: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect

def auto_detect_and_crop(img: np.ndarray, debug_mask_path: str = None) -> np.ndarray:
    """Robustly isolate photocard across textured/plain backgrounds with debug logging."""
    orig_h, orig_w = img.shape[:2]
    img_area_orig = float(orig_w * orig_h)

    # 1. Downscale to working resolution (max 800px)
    max_dim = 800.0
    scale = max_dim / max(orig_h, orig_w)
    work_w = int(orig_w * scale)
    work_h = int(orig_h * scale)
    small = cv2.resize(img, (work_w, work_h), interpolation=cv2.INTER_AREA)

    # 2. Median blur to flatten background textures (leather grain, paper noise)
    denoised = cv2.medianBlur(small, 7)

    # 3. Sample outer border perimeter to estimate background color in LAB
    border_th = max(5, int(min(work_w, work_h) * 0.03))
    borders = [
        denoised[0:border_th, :],
        denoised[-border_th:, :],
        denoised[:, 0:border_th],
        denoised[:, -border_th:],
    ]
    border_pixels = np.concatenate([b.reshape(-1, 3) for b in borders], axis=0)
    bg_bgr = np.median(border_pixels, axis=0).astype(np.uint8)

    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB).astype(np.float32)
    bg_lab = cv2.cvtColor(np.uint8([[bg_bgr]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]

    # Calculate Euclidean distance against background
    delta_e = np.linalg.norm(lab - bg_lab, axis=2)
    delta_e_norm = cv2.normalize(delta_e, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # 4. Otsu adaptive binarization
    _, mask = cv2.threshold(delta_e_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 5. Fill all inner card holes (hair, face, shine, clothes)
    close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_k)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    solid_mask = np.zeros_like(mask)
    work_area = float(work_w * work_h)

    for c in cnts:
        if cv2.contourArea(c) > (work_area * 0.05):
            cv2.drawContours(solid_mask, [c], -1, 255, thickness=cv2.FILLED)

    if debug_mask_path:
        cv2.imwrite(debug_mask_path, solid_mask)

    # 6. Extract candidate photocard contour
    cand_cnts, _ = cv2.findContours(solid_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    target_cnt = None
    best_area = 0.0

    for cnt in cand_cnts:
        area = cv2.contourArea(cnt)
        if (work_area * 0.10) < area < (work_area * 0.95):
            rect = cv2.minAreaRect(cnt)
            rw, rh = rect[1]
            if rw == 0 or rh == 0:
                continue

            aspect = min(rw, rh) / float(max(rw, rh))
            # Photocard aspect ratio is roughly 55:85 (~0.647)
            if 0.45 <= aspect <= 0.85:
                if area > best_area:
                    best_area = area
                    target_cnt = cnt

    # 7. Perspective transform and gentle outward padding
    if target_cnt is not None:
        rect = cv2.minAreaRect(target_cnt)
        quad_pts = cv2.boxPoints(rect).astype("float32")

        # Map back to full-resolution coordinates
        pts_orig = quad_pts / scale
        ordered_pts = order_points(pts_orig)

        # Force vertical portrait alignment
        edge_w = np.linalg.norm(ordered_pts[0] - ordered_pts[1])
        edge_h = np.linalg.norm(ordered_pts[0] - ordered_pts[3])
        if edge_w > edge_h:
            ordered_pts = np.roll(ordered_pts, 1, axis=0)

        # Add 2.5% outward padding to prevent clipping edges or hair
        center = np.mean(ordered_pts, axis=0)
        ordered_pts = center + (ordered_pts - center) * 1.025

        ordered_pts[:, 0] = np.clip(ordered_pts[:, 0], 0, orig_w - 1)
        ordered_pts[:, 1] = np.clip(ordered_pts[:, 1], 0, orig_h - 1)

        dst_pts = np.array(
            [
                [0, 0],
                [TARGET_WIDTH - 1, 0],
                [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
                [0, TARGET_HEIGHT - 1],
            ],
            dtype="float32",
        )

        matrix = cv2.getPerspectiveTransform(ordered_pts, dst_pts)
        warped = cv2.warpPerspective(img, matrix, (TARGET_WIDTH, TARGET_HEIGHT))
        print(f"[SUCCESS] Photocard detected! Area coverage: {(best_area / work_area) * 100:.1f}%")
        return warped

    print("[WARN] Card contour not found. Applied proportional center fallback.")
    current_ratio = orig_w / orig_h
    if current_ratio > TARGET_RATIO:
        new_w = int(orig_h * TARGET_RATIO)
        start_x = (orig_w - new_w) // 2
        cropped = img[:, start_x:start_x + new_w]
    else:
        new_h = int(orig_w / TARGET_RATIO)
        start_y = (orig_h - new_h) // 2
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

    # Oversized canvas to prevent edge cutoffs during rotation
    diag = int(np.sqrt(w**2 + h**2)) + 150
    watermark_layer = Image.new("RGBA", (diag, diag), (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark_layer)

    font_size = 18
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    spacing_x = text_w + 70
    spacing_y = text_h + 55
    text_color = (255, 255, 255, 50)

    # Tile watermark pattern
    for row_idx, y in enumerate(range(0, diag, spacing_y)):
        row_offset = (spacing_x // 2) if (row_idx % 2 == 1) else 0
        for x in range(-spacing_x, diag + spacing_x, spacing_x):
            draw.text((x + row_offset, y), text, font=font, fill=text_color)

    rotated = watermark_layer.rotate(45, resample=Image.BICUBIC)

    # Crop back to match target dimensions
    center_x, center_y = diag // 2, diag // 2
    left = center_x - (w // 2)
    top = center_y - (h // 2)
    cropped_watermark = rotated.crop((left, top, left + w, top + h))

    watermarked = Image.alpha_composite(base, cropped_watermark)
    return watermarked.convert("RGB")


def process_image(img: np.ndarray, output_path: str):
    """Run pipeline stages: Deskew/Crop -> White Balance -> Watermark -> WebP."""
    straightened = auto_detect_and_crop(img)
    wb_img = apply_white_balance(straightened)

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

    all_rows = submit_ws.get_all_values()
    if len(all_rows) <= 1:
        print("No records found in 'submit' sheet.")
        all_cards = cards_ws.get_all_records()
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(all_cards, f, ensure_ascii=False, indent=2)
        return

    headers = all_rows[0]
    try:
        status_col_idx = headers.index("status") + 1
    except ValueError:
        raise ValueError("Cannot find 'status' column in 'submit' sheet.")

    os.makedirs(CARDS_DIR, exist_ok=True)
    cards_headers = cards_ws.row_values(1)
    rows_to_append = []
    cells_to_update = []

    for row_idx, row_values in enumerate(all_rows[1:], start=2):
        row = dict(zip(headers, row_values))
        status = str(row.get("status", "")).strip().lower()

        if status != "process":
            continue

        card_id = str(row.get("id", "")).strip()
        name = str(row.get("name", "")).strip()
        # 1. 彈性抓取圖片連結欄位 (支援 photo, imageUrl, image, url 等欄位名稱，忽略大小寫與空格)
        url_key = next((k for k in row.keys() if k.strip().lower() in ["photo", "imageurl", "image", "url", "image_url"]), None)
        raw_url = str(row.get(url_key, "")).strip() if url_key else ""

        if not card_id or not name or not raw_url:
            print(f"Skipping row {row_idx}: missing id, name, or photo url.")
            continue

        target_webp = os.path.join(CARDS_DIR, f"{card_id}.webp")
        local_url = f"./cards/{card_id}.webp"

        print(f"Processing: {card_id} ({name})...")
        try:
            img = download_image(raw_url)
            if img is not None:
                process_image(img, target_webp)
            else:
                print(f"Failed to decode image buffer for {card_id}")
                continue
        except Exception as e:
            print(f"Error processing {card_id}: {e}")
            continue

        # 2. 回寫時同時對齊 imageUrl 與 photo，確保 cards 分頁無論用哪個欄位名都能拿到本地路徑
        row_dict = dict(row)
        row_dict["imageUrl"] = local_url
        row_dict["photo"] = local_url
        aligned_row = [str(row_dict.get(h, "")) for h in cards_headers]
        rows_to_append.append(aligned_row)

        cells_to_update.append(gspread.Cell(row=row_idx, col=status_col_idx, value="archived"))
        
    if rows_to_append:
        cards_ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")
        submit_ws.update_cells(cells_to_update)
        print(f"Appended {len(rows_to_append)} rows to 'cards' and updated status to 'archived'.")

    all_cards = cards_ws.get_all_records()
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
