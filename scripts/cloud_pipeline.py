import os
import json
import gspread
from google.oauth2.service_account import Credentials
from scripts.config import normalize_era, normalize_member

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
    
    # 1. 檢查 submit 工作表中狀態為 "process" 的項目並寫入 cards 工作表，完成後更新狀態為 done
    try:
        submit_sheet = spreadsheet.worksheet("submit")
        submit_records = submit_sheet.get_all_records()
        new_rows_from_submit = []
        
        # 取得 submit 表的 header 與 status 欄位索引 (1-based)
        submit_headers = submit_sheet.row_values(1)
        status_col_idx = submit_headers.index("status") + 1 if "status" in submit_headers else None

        for idx, row in enumerate(submit_records, start=2): # start=2 因為從第二列開始是資料
            status = str(row.get("status", "")).strip().lower()
            card_id = str(row.get("id", ""))
            
            if status == "process" and card_id and card_id not in existing_ids:
                normalized_era = normalize_era(str(row.get("era", "")))
                normalized_member = normalize_member(str(row.get("member", "")))
                
                new_rows_from_submit.append([
                    row.get("id"),
                    normalized_era,
                    normalized_member,
                    row.get("category"),
                    row.get("name"),
                    row.get("imageUrl")
                ])
                existing_ids.add(card_id)
                
                # 更新該筆 submit 記錄的狀態為 done
                if status_col_idx:
                    submit_sheet.update_cell(idx, status_col_idx, "done")
                
        if new_rows_from_submit:
            cards_sheet.append_rows(new_rows_from_submit)
            print(f"Added {len(new_rows_from_submit)} cards from submit sheet and updated statuses.")
    except Exception as e:
        print(f"Notice: 'submit' sheet check skipped or failed ({e}).")

    # 2. 讀取本機推上來的 public/cards.json，將雲端試算表缺少的本地卡片自動補登回 Google Sheets
    local_cards_path = "public/cards.json"
    if os.path.exists(local_cards_path):
        try:
            with open(local_cards_path, "r", encoding="utf-8") as f:
                local_cards = json.load(f)
            
            cards_records = cards_sheet.get_all_records()
            existing_ids = {str(row.get("id")) for row in cards_records}
            
            new_rows_from_local = []
            for card in local_cards:
                card_id = str(card.get("id", ""))
                if card_id and card_id not in existing_ids:
                    normalized_era = normalize_era(str(card.get("era", "")))
                    normalized_member = normalize_member(str(card.get("member", "")))
                    
                    new_rows_from_local.append([
                        card.get("id"),
                        normalized_era,
                        normalized_member,
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