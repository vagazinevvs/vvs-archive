# scripts/config.py

# Era mapping: short codes to full display names
ERA_NORMALIZE_MAP = {
    "swy": "Still With You",
}

# Member mapping: short codes to full display names (VANNER members)
MEMBER_NORMALIZE_MAP = {
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
    return ERA_NORMALIZE_MAP.get(cleaned.lower(), cleaned)

def normalize_member(member: str) -> str:
    if not member:
        return ""
    parts = [p.strip() for p in member.replace("_", ",").split(",")]
    normalized_parts = [MEMBER_NORMALIZE_MAP.get(p.lower(), p) for p in parts]
    return "_".join(normalized_parts)