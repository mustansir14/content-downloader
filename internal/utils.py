def sanitize(s: str) -> str:
    return s.replace("/", "-").replace("\\", "-").replace(",", "-")