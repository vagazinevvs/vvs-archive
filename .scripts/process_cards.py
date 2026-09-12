import os
import re
import json
import requests
import cv2
import numpy as np
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# Target dimensions (55mm x 85mm -> ratio approx 1:1.545)
TARGET_WIDTH = 600
TARGET_HEIGHT = 927
TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT

CARDS_DIR = os.path.join("public", "cards")
OUTPUT_JSON = os.path.join("public", "cards.json")


def extract_drive_id(url: str) -> str:
    """Extract file ID from various Google Drive link formats."""
    match = re.search(r"(?:id=|\/d\/)([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else ""


def download_image(url: str) -> np.ndarray:
    """Download image data and convert to OpenCV BGR format."""
    file_id = extract_drive_id(url)
    fetch_url = f"https://lh3.googleusercontent.com/d/{file_id}" if file_id else url
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(fetch_url, headers=headers, timeout=30)
    resp.raise_for_status()
    image_arr = np.frombuffer(resp.content, np.uint8)
    return cv2.imdecode(image_arr, cv2.IMREAD_COLOR)


def apply_white_balance(img: np.ndarray) -> np.ndarray:
    """Apply Gray-World algorithm to correct color temperature."""
    b, g, r = cv2.split(img)
    mean_gray = (np.mean(b) + np.mean(g) + np.mean(r)) / 3.0
    b = np.clip(b * (mean_gray / (np.mean(b) + 1e-5)), 0, 255).astype(np.uint8)
    g = np.clip(g * (mean_gray / (np.mean(g) + 1e-5)), 0, 255).astype(np.uint8)
    r = np.clip(r * (mean_gray / (np.mean(r) + 1e-5)), 0, 255).astype(np.uint8)
    return cv2.merge([b, g, r])


def auto_detect_and_crop(img: np.ndarray) -> np.ndarray:
    """Contour detection for photocard edges with center-crop fallback."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = img.shape[:2]
    card_box = None
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > (w * h * 0.20):
            bx, by, bw, bh = cv2.boundingRect(approx)
            if 0.5 <= (bw / float(bh)) <= 0.8:
                card_box = (bx, by, bw, bh)
                break

    if card_box:
        bx, by, bw, bh = card_box
        return img[by:by + bh, bx:bx + bw]

    # Center-crop fallback
    if (w / h) > TARGET_RATIO:
        new_w = int(h * TARGET_RATIO)
        return img[:, (w - new_w) // 2:(w - new_w) // 2 + new_w]
    else:
        new_h = int(w / TARGET_RATIO)
        return img[(h - new_h) // 2:(h - new_h) // 2 + new_h, :]


def process_image(img: np.ndarray, output_path: str):
    """Pipeline: White balance -> smart crop -> resize -> export WebP."""
    wb_img = apply_white_balance(img)
    cropped = auto_detect_and_crop(wb_img)
    resized = cv2.resize(cropped, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_LANCZOS4)
    rgb_img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb_img).save(output_path, "WEBP", quality=85, method=6)


def main():
    sa_json = os.environ.get("GCP_SA_KEY")
    sheet_id = os.environ.get("SPREADSHEET_ID")
    if not sa_json or not sheet_id:
        raise ValueError("Missing GCP_SA_KEY or SPREADSHEET_ID in environment.")

    # Authenticate with Google Sheets
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    process_ws = sh.worksheet("process")
    cards_ws = sh.worksheet("cards")

    pending_records = process_ws.get_all_records()
    if not pending_records:
        print("No pending cards found in 'process' tab.")
        # Ensure cards.json is up-to-date with current cards tab
        current_cards = cards_ws.get_all_records()
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(current_cards, f, ensure_ascii=False, indent=2)
        return

    os.makedirs(CARDS_DIR, exist_ok=True)
    rows_to_append = []

    for row in pending_records:
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
                print(f"Failed to decode image for {card_id}")
                continue
        except Exception as e:
            print(f"Error processing {card_id}: {e}")
            continue

        # Prepare new row for 'cards' tab
        new_row = [
            card_id,
            row.get("era", ""),
            row.get("member", ""),
            row.get("category", ""),
            name,
            local_url,
        ]
        rows_to_append.append(new_row)

    if rows_to_append:
        # Append processed cards to 'cards' sheet
        cards_ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")

        # Clear processed rows from 'process' sheet (preserve header row)
        process_ws.batch_clear(["A2:Z"])
        print(f"Moved {len(rows_to_append)} cards from 'process' to 'cards'.")

    # Export latest full cards database to public/cards.json for the frontend
    all_cards = cards_ws.get_all_records()
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)

    print("Successfully updated cards.json.")


if __name__ == "__main__":
    main()