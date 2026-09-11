import os
import json
import re
import requests
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from config import normalize_era, normalize_member

def download_and_process_image(drive_url, save_filename):
    # 從 Google Drive 連結提取 File ID
    match = re.search(r'(?:id=|\/d\/)([a-zA-Z0-9_-]+)', drive_url)
    if not match:
        return None
    file_id = match.group(1)
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    os.makedirs("public/cards", exist_ok=True)
    temp_path = f"temp_{file_id}.png"
    
    try:
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            # 轉換為 WebP 格式並儲存到 public/cards/
            img = Image.open(temp_path)
            webp_filename = f"{save_filename}.webp"
            webp_path = os.path.join("public/cards", webp_filename)
            img.save(webp_path, "WEBP", quality=85)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            return f"./cards/{webp_filename}"
    except Exception as e:
        print(f"Failed to process image from Drive: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return None

def run_cloud_pipeline():
    sa_key = os.environ.get("GCP_SA_KEY")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    
    if not sa_key or not spreadsheet_id:
        print("Missing cloud credentials.")
        return
        
    creds = Credentials.from_service_account_info(
        json.loads(sa_key), 
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    cards_sheet = spreadsheet.worksheet("cards")
    cards_records = cards_sheet.get_all_records()
    existing_ids = {str(row.get("id")) for row in cards_records}
    
    try:
        submit_sheet = spreadsheet.worksheet("submit")
        submit_records = submit_sheet.get_all_records()
        new_rows_from_submit = []
        
        submit_headers = submit_sheet.row_values(1)
        status_col_idx = submit_headers.index("status") + 1 if "status" in submit_headers else None

        for idx, row in enumerate(submit_records, start=2):
            status = str(row.get("status", "")).strip().lower()
            card_id = str(row.get("id", ""))
            
            if status == "process" and card_id:
                # 防呆：若 ID 已存在 cards，改為 rejected
                if card_id in existing_ids:
                    if status_col_idx:
                        submit_sheet.update_cell(idx, status_col_idx, "rejected")
                        print(f"Card ID '{card_id}' already exists. Marked row {idx} as 'rejected'.")
                else:
                    drive_url = str(row.get("photo", ""))
                    # 處理圖片下載與 WebP 轉換
                    local_img_path = download_and_process_image(drive_url, card_id)
                    
                    if local_img_path:
                        normalized_era = normalize_era(str(row.get("era", "")))
                        normalized_member = normalize_member(str(row.get("member", "")))
                        
                        new_rows_from_submit.append([
                            card_id,
                            normalized_era,
                            normalized_member,
                            row.get("category"),
                            row.get("name"),
                            local_img_path
                        ])
                        existing_ids.add(card_id)
                        
                        if status_col_idx:
                            submit_sheet.update_cell(idx, status_col_idx, "archived")
                        print(f"Successfully processed and archived card ID: {card_id}")
                    else:
                        print(f"Failed to fetch image for card ID: {card_id}")
                
        if new_rows_from_submit:
            cards_sheet.append_rows(new_rows_from_submit)
            
    except Exception as e:
        print(f"Notice: 'submit' sheet processing failed ({e}).")

    # 輸出最終 cards.json
    final_records = cards_sheet.get_all_records()
    os.makedirs("public", exist_ok=True)
    with open("public/cards.json", "w", encoding="utf-8") as f:
        json.dump(final_records, f, ensure_ascii=False, indent=2)
    print("Cloud pipeline updated public/cards.json successfully.")

if __name__ == "__main__":
    run_cloud_pipeline()
