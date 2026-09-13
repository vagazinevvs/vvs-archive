import os
import json
import gspread
from google.oauth2.service_account import Credentials

def sync_sheet_to_json(output_path="public/cardsfromsheet.json"):
    sa_key = os.environ.get("GCP_SA_KEY")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    
    if not sa_key or not spreadsheet_id:
        print("Missing cloud credentials.")
        return
        
    creds = Credentials.from_service_account_info(
        json.loads(sa_key), 
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )

    print("Using Spreadsheet ID:", spreadsheet_id)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    cards_sheet = spreadsheet.worksheet("cards")
    rows = cards_sheet.get_all_records()
    
    cards_data = []
    for row in rows:
        raw_member = row.get("member", "")
        
        # 1. 檢查並排除 member 為 back 的獨立條目
        if isinstance(raw_member, str) and raw_member.strip().lower() == "back":
            continue
        elif isinstance(raw_member, list) and any(m.strip().lower() == "back" for m in raw_member):
            continue
            
        # 2. 將 member 保持為單一字串格式
        if isinstance(raw_member, list):
            member = raw_member[0] if raw_member else ""
        else:
            member = str(raw_member).strip()
            
        card_obj = {}
        for key, val in row.items():
            if val != "":
                if key == "member":
                    card_obj[key] = member
                else:
                    card_obj[key] = val
                    
        cards_data.append(card_obj)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cards_data, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully synced {len(cards_data)} sorted cards from Google Sheet to {output_path}")

if __name__ == "__main__":
    sync_sheet_to_json()