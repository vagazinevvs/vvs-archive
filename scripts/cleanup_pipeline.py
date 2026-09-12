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

    print("Using Spreadsheet ID:", spreadsheet_id)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    cards_sheet = spreadsheet.worksheet("cards")
    cards_records = cards_sheet.get_all_records()
    
    indices_to_delete = []
    deleted_ids = []
    
    # 找出符合刪除條件的行號（從第 2 行開始，因為第 1 行是表頭）
    for idx, row in enumerate(cards_records, start=2):
        card_id = str(row.get("id", ""))
        member = str(row.get("member", "")).strip().lower()
        
        is_match = False
        if member == "delete":
            is_match = True
        if target_card_id and card_id == target_card_id:
            is_match = True
        if target_member and target_member.lower() in member:
            is_match = True
            
        if is_match:
            indices_to_delete.append(idx)
            if card_id:
                deleted_ids.append(card_id)
                
    if not deleted_ids:
        print("沒有找到符合刪除條件的卡片。")
        return
        
    # 1. 從 Google 試算表中精準刪除該列（由下往上刪除以避免行號位移）
    indices_to_delete.sort(reverse=True)
    for row_idx in indices_to_delete:
        cards_sheet.delete_rows(row_idx)
        
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
    target_id = os.environ.get("TARGET_CARD_ID")
    target_mem = os.environ.get("TARGET_MEMBER")
    run_cleanup(target_card_id=target_id, target_member=target_mem)