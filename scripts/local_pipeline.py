import os
import json
import shutil
import re
from card_process import crop_card, apply_watermark, apply_white_balance

LOCAL_RAW_DIR = "../raw_incoming"
DONE_DIR = os.path.join(LOCAL_RAW_DIR, "0-done")
LOCAL_OUTPUT_DIR = "public/cards"
CARDS_JSON_PATH = "public/cards.json"
STAGING_JSON_PATH = "public/cards_staging.json"

VALID_CATEGORIES = ["Event", "Video Call", "Polaroid", "Album", "POB"]
CATEGORY_MAP = {cat.lower().replace(" ", ""): cat for cat in VALID_CATEGORIES}


class CompactEncoder(json.JSONEncoder):
    """讓 member 陣列維持單行顯示的自訂 Encoder"""
    def encode(self, o):
        if isinstance(o, list) and all(isinstance(item, str) for item in o):
            return json.dumps(o, ensure_ascii=False)
        return super().encode(o)


def parse_card_metadata(card_id, category=""):
    """從檔名解析 era, name, member (格式: era-name-member1_member2.jpg)"""
    parts = card_id.split("-")
    
    if len(parts) >= 3:
        era = parts[0]
        raw_member = parts[-1]
        member = [m.strip().lower() for m in raw_member.split("_")]
        card_name = "-".join(parts[1:-1]).replace("_", " ")
    elif len(parts) == 2:
        era = parts[0]
        card_name = parts[1].replace("_", " ")
        member = ["all"]
    else:
        era = "Unknown"
        card_name = card_id.replace("_", " ")
        member = ["all"]
        
    return {
        "id": card_id,
        "name": card_name,
        "member": member,
        "era": era,
        "category": category,
        "imageUrl": f"/cards/{card_id}.webp"
    }

def process_pipeline():
    os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DONE_DIR, exist_ok=True)
    cards_data = []

    if not os.path.exists(LOCAL_RAW_DIR):
        #print(f"Error: Raw directory not found at {LOCAL_RAW_DIR}")
        return

    # 1. 處理根目錄檔案 (category = "")
    for filename in os.listdir(LOCAL_RAW_DIR):
        file_path = os.path.join(LOCAL_RAW_DIR, filename)
        if os.path.isfile(file_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            card_id = os.path.splitext(filename)[0]
            #print(f"-> 處理根目錄檔案: {filename} -> ID: '{card_id}'")
            
            try:
                cropped_bgr = crop_card(file_path)
                balanced_bgr = apply_white_balance(cropped_bgr)
                final_pil = apply_watermark(balanced_bgr)
                
                output_path = os.path.join(LOCAL_OUTPUT_DIR, f"{card_id}.webp")
                final_pil.save(output_path, "WEBP", quality=85)
                
                card_data = parse_card_metadata(card_id, category="")
                cards_data.append(card_data)
                
                # 移動原始檔案至 0-done
                #shutil.move(file_path, os.path.join(DONE_DIR, filename))
                print(f"   成功處理 {card_id}")
            except Exception as e:
                print(f"   處理失敗 {filename}: {e}")

    # 2. 處理分類子資料夾
    for folder_name in os.listdir(LOCAL_RAW_DIR):
        # 略過 0-done 與其他非分類項目
        if folder_name == "0-done":
            continue
            
        cat_path = os.path.join(LOCAL_RAW_DIR, folder_name)
        if not os.path.isdir(cat_path):
            continue
            
        normalized_key = folder_name.lower().replace(" ", "")
        if normalized_key not in CATEGORY_MAP:
            #print(f"[WARN] 略過未知資料夾 '{folder_name}'")
            continue
            
        category = CATEGORY_MAP[normalized_key]
        print(f"-> 處理分類: {category} (來源資料夾: {folder_name})")
        
        for filename in os.listdir(cat_path):
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue
                
            file_path = os.path.join(cat_path, filename)
            card_id = os.path.splitext(filename)[0]
            #print(f"   讀取檔案: {filename} -> ID: '{card_id}'")
            
            try:
                cropped_bgr = crop_card(file_path)
                balanced_bgr = apply_white_balance(cropped_bgr)
                final_pil = apply_watermark(balanced_bgr)
                
                output_path = os.path.join(LOCAL_OUTPUT_DIR, f"{card_id}.webp")
                final_pil.save(output_path, "WEBP", quality=85)
                
                card_data = parse_card_metadata(card_id, category=category)
                cards_data.append(card_data)
                
                # 移動原始檔案至 0-done
                #shutil.move(file_path, os.path.join(DONE_DIR, filename))
                print(f"   成功處理 {card_id}")
            except Exception as e:
                print(f"   處理失敗 {filename}: {e}")

    # 寫入暫存檔
    json_str = json.dumps(final_cards, ensure_ascii=False, indent=2)
    json_str = re.sub(
        r'"member": \s*\[\s*("[^"]+")\s*\]', 
        r'"member": [\1]', 
        json_str
    )

    with open(PROD_JSON_PATH, "w", encoding="utf-8") as f:
        f.write(json_str)

    os.remove(STAGING_JSON_PATH)
    print(f"同步完成，已更新 {PROD_JSON_PATH}（新增 {added_count} 張）")

if __name__ == "__main__":
    process_pipeline()