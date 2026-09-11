import os
import json
from card_process import crop_card, apply_watermark

# 直接輸出到 public/cards.json，讓本機測試與預覽直接對應
CARDS_JSON_PATH = "public/cards.json"
LOCAL_RAW_DIR = "raw_incoming"
LOCAL_OUTPUT_DIR = "public/cards"

def run_local_pipeline():
    os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)
    os.makedirs("public", exist_ok=True)
    
    cards = []
    if os.path.exists(CARDS_JSON_PATH):
        with open(CARDS_JSON_PATH, "r", encoding="utf-8") as f:
            cards = json.load(f)
            
    if not os.path.exists(LOCAL_RAW_DIR):
        os.makedirs(LOCAL_RAW_DIR)
        print(f"Created {LOCAL_RAW_DIR}. Place raw images inside.")
        return

    existing_ids = {card["id"] for card in cards}

    for filename in os.listdir(LOCAL_RAW_DIR):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            card_id = os.path.splitext(filename)[0]
            
            # 防呆：如果 JSON 已經存在該 ID，則跳過
            if card_id in existing_ids:
                print(f"Skipped (already exists): {filename}")
                continue

            raw_path = os.path.join(LOCAL_RAW_DIR, filename)
            output_filename = f"{card_id}.webp"
            output_path = os.path.join(LOCAL_OUTPUT_DIR, output_filename)
            
            # 呼叫核心處理
            cropped = crop_card(raw_path)
            processed_pil = apply_watermark(cropped)
            processed_pil.save(output_path, "WEBP", quality=90)
            
            # 從檔名解析 era, name, member (格式: era-name-member.jpg)
            name_part = card_id
            parts = name_part.split("-")
            
            if len(parts) >= 3:
                era = parts[0]
                raw_member = parts[-1]
                member = [m.strip() for m in raw_member.split("_")]
                card_name = "-".join(parts[1:-1]).replace("_", " ")
            elif len(parts) == 2:
                era = parts[0]
                card_name = parts[1].replace("_", " ")
                member = "All"
            else:
                era = "Unknown"
                card_name = name_part
                member = "All"
            
            cards.append({
                "id": card_id,
                "name": card_name,
                "member": member,
                "era": era,
                "category": "POB",
                "imageUrl": f"cards/{output_filename}"
            })
            print(f"Processed locally: {filename}")
            
    with open(CARDS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    print(f"Local pipeline completed. {CARDS_JSON_PATH} updated successfully.")

if __name__ == "__main__":
    run_local_pipeline()