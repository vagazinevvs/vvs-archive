import os
import json
import re
from config import ERA_MAPPING, MEMBER_MAPPING

PROD_JSON_PATH = "public/cards.json"
STAGING_JSON_PATH = "public/cards_staging.json"

def expand_full_names(card):
    """將 era 與 member 的縮寫轉換為全名"""
    era_key = card.get("era", "").lower()
    if era_key in ERA_MAPPING:
        card["era"] = ERA_MAPPING[era_key]
        
    members = card.get("member", [])
    expanded_members = []
    for m in members:
        m_lower = m.lower()
        expanded_members.append(MEMBER_MAPPING.get(m_lower, m))
    card["member"] = expanded_members
    
    return card

def merge_staging_to_prod():
    if not os.path.exists(STAGING_JSON_PATH):
        print("找不到暫存檔案，無需同步。")
        return

    prod_cards = []
    if os.path.exists(PROD_JSON_PATH):
        with open(PROD_JSON_PATH, "r", encoding="utf-8") as f:
            prod_cards = json.load(f)
            
    prod_map = {card["id"]: card for card in prod_cards}

    with open(STAGING_JSON_PATH, "r", encoding="utf-8") as f:
        staging_cards = json.load(f)

    added_count = 0
    for card in staging_cards:
        card_id = card["id"]
        if card_id not in prod_map:
            expanded_card = expand_full_names(card)
            prod_map[card_id] = expanded_card
            added_count += 1
            print(f"🆕 {card_id}")
        else:
            print(f"⏭️ {card_id}")

    final_cards = list(prod_map.values())
    json_str = json.dumps(final_cards, ensure_ascii=False, indent=2)
    json_str = re.sub(
        r'"member": \s*\[\s*("[^"]+")\s*\]', 
        r'"member": [\1]', 
        json_str
    )

    with open(PROD_JSON_PATH, "w", encoding="utf-8") as f:
        f.write(json_str)

    print(f"同步完成，已更新 {PROD_JSON_PATH}（新增 {added_count} 張）")

if __name__ == "__main__":
    merge_staging_to_prod()