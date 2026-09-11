import os
import json
import re
import sys
import requests
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from config import normalize_era, normalize_member
from card_process import process_card_image


def download_and_process_image(drive_url, save_filename):
    # 支援 id=... 以及 /file/d/.../view 兩種格式
    match = re.search(r'(?:id=|\/d\/)([a-zA-Z0-9_-]+)', drive_url)
    if not match:
        print(f"[DEBUG] URL match failed for: {drive_url}")
        return None
        
    file_id = match.group(1)
    download_url = f"https://lh3.googleusercontent.com/d/{file_id}"
    print(f"[DEBUG] Extracted File ID: {file_id}, Target URL: {download_url}")
    
    os.makedirs("public/cards", exist_ok=True)
    temp_path = f"temp_{file_id}.png"
    
    try:
        response = requests.get(download_url, stream=True)
        print(f"[DEBUG] Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            # 透過共用模組進行裁切、白平衡與浮水印處理
            local_img_path = process_card_image(temp_path, save_filename)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            return local_img_path
        else:
            print(f"[DEBUG] Failed with status code {response.status_code}")
    except Exception as e:
        print(f"[DEBUG] Exception caught while processing image: {e}")
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
    
# 掃描本地的 public/cards.json，將 Google 試算表上缺少的項目補上去
    local_cards_path = "public/cards.json"
    if os.path.exists(local_cards_path):
        try:
            with open(local_cards_path, "r", encoding="utf-8") as f:
                local_cards = json.load(f)
            
            new_rows_from_local = []
            for card in local_cards:
                card_id = card.get("id")
                if card_id and card_id not in existing_ids:
                    raw_members = card.get("member", "")
                    member_str = ", ".join(raw_members) if isinstance(raw_members, list) else str(raw_members)
                    
                    new_rows_from_local.append([
                        card_id,
                        card.get("era", ""),
                        member_str,
                        card.get("category", ""),
                        card.get("name", ""),
                        card.get("imageUrl", "")
                    ])
                    existing_ids.add(card_id)
                    print(f"🆕 Local card ID '{card_id}' missing in sheet, queued for append.")
            
            if new_rows_from_local:
                cards_sheet.append_rows(new_rows_from_local)
                print(f"Successfully appended {len(new_rows_from_local)} cards from public/cards.json to Google Sheets.")
        except Exception as e:
            print(f"Notice: Failed to process public/cards.json ({e}).")

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
                    # 下載圖片並套用共用處理管線
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