# scripts/config.py

# Era mapping: short codes to full display names
ERA_MAPPING = {
    "swy": "Still With You",
}

# Member mapping: short codes to full display names (VANNER members)
MEMBER_MAPPING = {
    "th": "Taehwan",
    "gon": "Gon",
    "hs": "Hyesung",
    "sk": "Sungkook",
    "yg": "Yeongkwang",
}

def normalize_era(era: str) -> str:
    if not era:
        return "Unknown"
    cleaned = era.strip()
    return ERA_MAPPING.get(cleaned.lower(), cleaned)

def normalize_member(member_input):
    if isinstance(member_input, list):
        return ", ".join([str(m).strip() for m in member_input if m])
    if isinstance(member_input, str):
        # 移除可能殘留的方括號或引號
        cleaned = member_input.strip("[]'\"")
        return ", ".join([m.strip("'\" ") for m in cleaned.split(",") if m.strip("'\" ")])
    return str(member_input)