# scripts/config.py

# Era mapping: short codes to full display names
ERA_MAPPING = {
    "swy": "Still With You",
    "tt": "Twisted Tie",
}

# Member mapping: short codes to full display names (VANNER members)
MEMBER_MAPPING = {
    "th": "Taehwan",
    "gon": "Gon",
    "hs": "Hyesung",
    "sk": "Sungkook",
    "yg": "Yeongkwang",
    "hsk": ["Hyesung", "Sungkook"],
}

# Side / tag mapping: short codes to display labels
SIDE_MAPPING = {
    "back": "卡背",
}


def normalize_era(era: str) -> str:
    if not era:
        return "Unknown"
    cleaned = era.strip()
    return ERA_MAPPING.get(cleaned.lower(), cleaned)


def normalize_member(member_input):
    if isinstance(member_input, list):
        mapped = [MEMBER_MAPPING.get(str(m).strip().lower(), str(m).strip()) for m in member_input if m]
        return ", ".join([m for m in mapped if m])
    if isinstance(member_input, str):
        # 移除可能殘留的方括號或引號
        cleaned = member_input.strip("[]'\"")
        tokens = [m.strip("'\" ").lower() for m in cleaned.split(",") if m.strip("'\" ")]
        mapped = [MEMBER_MAPPING.get(t, t) for t in tokens]
        return ", ".join([m for m in mapped if m])
    return str(member_input)


def normalize_side(side: str) -> str:
    if not side:
        return ""
    cleaned = str(side).strip().lower()
    return SIDE_MAPPING.get(cleaned, str(side).strip())