import os
import json
import gspread
from google.oauth2.service_account import Credentials

def run_cloud_pipeline():
    """Fetch from Google Sheet, process if needed, and update cards.json."""
    sa_key = os.environ.get("GCP_SA_KEY")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    
    if not sa_key or not spreadsheet_id:
        print("Missing cloud credentials.")
        return
        
    creds = Credentials.from_service_account_info(json.loads(sa_key), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).worksheet("cards")
    records = sheet.get_all_records()
    
    os.makedirs("public", exist_ok=True)
    with open("public/cards.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print("Cloud pipeline updated public/cards.json successfully.")

if __name__ == "__main__":
    run_cloud_pipeline()