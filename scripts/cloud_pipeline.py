import os
import json
import re
import requests
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from card_process import process_card_image

def download_and_process_image(drive_url, save_filename):
    match = re.search(r'(?:id=|\/d\/)([a-zA-Z0-9_-]+)', drive_url)
    if not match:
        print(f"[DEBUG] URL match failed for: {drive_url}")
        return None
        
    file_id = match.group(1)
    download_url = f"https://lh3.googleusercontent.com/d/{file_id}"
    
    os.makedirs("public/cards", exist_ok=True)
    temp_path = f"temp_{file_id}.png"
    
    try:
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
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
    
    # 來源 1：掃描本地 public/cards.json 補登至試算表
    local_json_path = "public/cards.json"
    if os.path.exists(local_json_path):
        try:
            with open(local_json_path, "r", encoding="utf-8") as f:
                local_cards = json.load(f)
                
            new_rows_from_local = []
            for card in local_cards:
                card_id = str(card.get("id", ""))
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
                    print(f"📤 補登本地卡片 ID '{card_id}' 至試算表")
                    
            if new_rows_from_local:
                cards_sheet.append_rows(new_rows_from_local)
                print(f"成功從 public/cards.json 補登 {len(new_rows_from_local)} 筆至試算表。")
        except Exception as e:
            print(f"Notice: Failed to process public/cards.json ({e}).")

    # 來源 2：處理來自 submit 工作表的雲端上傳請求
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
                if card_id in existing_ids:
                    if status_col_idx:
                        submit_sheet.update_cell(idx, status_col_idx, "rejected")
                        print(f"Card ID '{card_id}' already exists. Marked row {idx} as 'rejected'.")
                else:
                    drive_url = str(row.get("photo", ""))
                    local_img_path = download_and_process_image(drive_url, card_id)

                    if local_img_path:
                        # 在加入新 row 之前進行名稱標準化
                        raw_member = str(row.get("member", ""))
                        standardized_member = ", ".join([standardize_member_name(m) for m in parse_members_python(raw_member)])

                        new_rows_from_submit.append([
                            card_id,
                            str(row.get("era", "")),
                            standardized_member, # 使用標準化後的成員名稱
                            row.get("category"),
                            row.get("name"),
                            local_img_path
                        ])
                        existing_ids.add(card_id)
                        
                        if status_col_idx:
                            submit_sheet.update_cell(idx, status_col_idx, "archived")
                        print(f"Successfully processed and archived submit card ID: {card_id}")
                    else:
                        print(f"Failed to fetch image for submit card ID: {card_id}")
                
        if new_rows_from_submit:
            cards_sheet.append_rows(new_rows_from_submit)
            print(f"成功從 submit 處理並追加 {len(new_rows_from_submit)} 筆至試算表。")
            
    except Exception as e:
        print(f"Notice: 'submit' sheet processing failed ({e}).")

def parse_members_python(member_str):
    """
    Parse member input string from Google Sheets into a standardized list of members.
    Handles commas, slashes, or mixed delimiters.
    """
    if not member_str:
        return ["all"]
    
    # Split by common delimiters like comma, slash, or ampersand
    raw_parts = re.split(r'[,/&]+', str(member_str))
    members = []
    
    for part in raw_parts:
        cleaned = part.strip()
        if cleaned:
            members.append(cleaned)
            
    return members if members else ["all"]

def standardize_member_name(member_name):
    """
    Map various spellings or aliases to standardized internal keys.
    """
    name_lower = member_name.lower()
    
    if any(k in name_lower for k in ['taehwan', '泰煥', '고태운', 'taewoon']):
        return 'Taehwan'
    if any(k in name_lower for k in ['hyesung', '慧成', '박혜성']):
        return 'Hyesung'
    if any(k in name_lower for k in ['sungkook', '成國', '성국']):
        return 'Sungkook'
    if any(k in name_lower for k in ['gon', '原書', '이원서']):
        return 'Gon'
    if any(k in name_lower for k in ['yeongkwang', '泳光', '안영준', 'yeonggwang']):
        return 'Yeongkwang'
        
    return member_name

if __name__ == "__main__":
    run_cloud_pipeline()