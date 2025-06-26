import re

def sanitize(s: str) -> str:
    return remove_emojis(s.replace("/", "-").replace("\\", "-").replace(",", "-"))


def remove_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & pictographs
        "\U0001F680-\U0001F6FF"  # Transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # Flags
        "\U00002700-\U000027BF"  # Dingbats
        "\U0001F900-\U0001F9FF"  # Supplemental symbols
        "\U00002600-\U000026FF"  # Misc symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U000025A0-\U00002BEF"  # Various symbols
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)