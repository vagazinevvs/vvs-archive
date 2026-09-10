import os
import json
from card_process import crop_card, apply_watermark

TEMP_JSON_PATH = "temp_cards.json"
LOCAL_RAW_DIR = "raw_incoming"
LOCAL_OUTPUT_DIR = "public/cards"

def run_local_pipeline():
    os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)
    temp_cards = []
    
    if os.path.exists(TEMP_JSON_PATH):
        with open(TEMP_JSON_PATH, "r", encoding="utf-8") as f:
            temp_cards = json.load(f)
            
    if not os.path.exists(LOCAL_RAW_DIR):
        os.makedirs(LOCAL_RAW_DIR)
        print(f"Created {LOCAL_RAW_DIR}. Place raw images inside.")
        return

    for filename in os.listdir(LOCAL_RAW_DIR):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            raw_path = os.path.join(LOCAL_RAW_DIR, filename)
            card_id = os.path.splitext(filename)[0]
            output_filename = f"{card_id}.jpg"
            output_path = os.path.join(LOCAL_OUTPUT_DIR, output_filename)
            
            # 呼叫核心處理
            cropped = crop_card(raw_path)
            processed_pil = apply_watermark(cropped)
            processed_pil.save(output_path, "JPEG", quality=90)
            
            temp_cards.append({
                "id": card_id,
                "name": card_id,
                "member": "All",
                "era": "Unknown",
                "category": "POB",
                "imageUrl": f"cards/{output_filename}"
            })
            print(f"Processed locally: {filename}")
            
    with open(TEMP_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(temp_cards, f, ensure_ascii=False, indent=2)
    print(f"Local pipeline completed. Temp JSON updated at {TEMP_JSON_PATH}")

if __name__ == "__main__":
    run_local_pipeline()