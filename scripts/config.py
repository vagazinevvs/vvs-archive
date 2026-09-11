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

def normalize_member(member: str) -> str:
    if not member:
        return ""
    parts = [p.strip() for p in member.replace("_", ",").split(",")]
    normalized_parts = [MEMBER_MAPPING.get(p.lower(), p) for p in parts]
    return "_".join(normalized_parts)