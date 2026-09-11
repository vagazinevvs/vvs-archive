import os
import json
import gspread
from google.oauth2.service_account import Credentials

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
    
    # 1. 檢查 submit 工作表中狀態為 "process" 的項目並寫入 cards 工作表
    try:
        submit_sheet = spreadsheet.worksheet("submit")
        submit_records = submit_sheet.get_all_records()
        new_rows_from_submit = []
        
        for row in submit_records:
            status = str(row.get("status", "")).strip().lower()
            card_id = str(row.get("id", ""))
            
            if status == "process" and card_id and card_id not in existing_ids:
                member_val = row.get("member")
                member_str = "_".join(member_val) if isinstance(member_val, list) else str(member_val)
                
                new_rows_from_submit.append([
                    row.get("id"),
                    row.get("era"),
                    member_str,
                    row.get("category"),
                    row.get("name"),
                    row.get("imageUrl")
                ])
                existing_ids.add(card_id)
                
        if new_rows_from_submit:
            cards_sheet.append_rows(new_rows_from_submit)
            print(f"Added {len(new_rows_from_submit)} cards from submit sheet.")
    except Exception as e:
        print(f"Notice: 'submit' sheet check skipped or failed ({e}).")

    # 2. 讀取本機推上來的 public/cards.json，將雲端試算表缺少的本地卡片自動補登回 Google Sheets
    local_cards_path = "public/cards.json"
    if os.path.exists(local_cards_path):
        try:
            with open(local_cards_path, "r", encoding="utf-8") as f:
                local_cards = json.load(f)
            
            # 重新取得目前的 spreadsheet 記錄確保比對基準最新
            cards_records = cards_sheet.get_all_records()
            existing_ids = {str(row.get("id")) for row in cards_records}
            
            new_rows_from_local = []
            for card in local_cards:
                card_id = str(card.get("id", ""))
                if card_id and card_id not in existing_ids:
                    member_val = card.get("member")
                    member_str = "_".join(member_val) if isinstance(member_val, list) else str(member_val)
                    
                    new_rows_from_local.append([
                        card.get("id"),
                        card.get("era"),
                        member_str,
                        card.get("category"),
                        card.get("name"),
                        card.get("imageUrl")
                    ])
                    existing_ids.add(card_id)
                    
            if new_rows_from_local:
                cards_sheet.append_rows(new_rows_from_local)
                print(f"Synced {len(new_rows_from_local)} offline-processed local cards to Google Sheets cards worksheet.")
        except Exception as e:
            print(f"Notice: Failed to merge local cards.json into sheet: {e}")

    # 3. 從 cards 工作表撈取最終完整資料，並覆蓋更新 public/cards.json 供前端打包部署
    final_records = cards_sheet.get_all_records()
    os.makedirs("public", exist_ok=True)
    with open("public/cards.json", "w", encoding="utf-8") as f:
        json.dump(final_records, f, ensure_ascii=False, indent=2)
    print("Cloud pipeline updated public/cards.json successfully with merged records.")

if __name__ == "__main__":
    run_cloud_pipeline()