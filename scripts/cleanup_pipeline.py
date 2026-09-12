import os
import json
import gspread
from google.oauth2.service_account import Credentials

def run_cleanup(target_card_id=None, target_member=None):
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
    
    rows_to_keep = []
    deleted_ids = []
    
    # 保留表頭
    header = cards_sheet.row_values(1)
    
    for row in cards_records:
        card_id = str(row.get("id", ""))
        member = str(row.get("member", ""))
        era = str(row.get("era", "")).strip()
        
        # 判斷是否符合刪除條件：當 member 為 "delete" 或符合其他指定條件
        is_match = False
        if member == "delete":
            is_match = True
        if target_card_id and card_id == target_card_id:
            is_match = True
        if target_member and target_member.lower() in member:
            is_match = True
            
        if is_match:
            deleted_ids.append(card_id)
        else:
            rows_to_keep.append(row)
            
        if is_match:
            deleted_ids.append(card_id)
        else:
            rows_to_keep.append(row)
            
    if not deleted_ids:
        print("沒有找到符合刪除條件的卡片。")
        return
        
    # 1. 更新 Google 試算表（清空後重新寫入保留的資料）
    cards_sheet.clear()
    cards_sheet.append_row(header)
    
    new_rows = []
    for row in rows_to_keep:
        new_rows.append([
            row.get("id", ""),
            row.get("era", ""),
            row.get("member", ""),
            row.get("category", ""),
            row.get("name", ""),
            row.get("imageUrl", "")
        ])
    if new_rows:
        cards_sheet.append_rows(new_rows)
        
    print(f"🗑️ 已從 Google 試算表中刪除以下卡片: {deleted_ids}")

    # 2. 同步刪除本地 public/cards.json 中的記錄
    local_json_path = "public/cards.json"
    if os.path.exists(local_json_path):
        with open(local_json_path, "r", encoding="utf-8") as f:
            local_cards = json.load(f)
            
        updated_cards = [c for c in local_cards if str(c.get("id")) not in deleted_ids]
        
        with open(local_json_path, "w", encoding="utf-8") as f:
            json.dump(updated_cards, f, ensure_ascii=False, indent=2)
        print(f"💾 已更新本地 {local_json_path}")

    # 3. 刪除對應的 .webp 圖片檔案
    for cid in deleted_ids:
        img_path = os.path.join("public", "cards", f"{cid}.webp")
        if os.path.exists(img_path):
            os.remove(img_path)
            print(f"🖼️ 已刪除圖片檔案: {img_path}")

if __name__ == "__main__":
    # 可透過環境變數或參數指定要刪除的 ID 或成員
    target_id = os.environ.get("TARGET_CARD_ID")
    target_mem = os.environ.get("TARGET_MEMBER")
    run_cleanup(target_card_id=target_id, target_member=target_mem)