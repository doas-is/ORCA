import os
import re
import unicodedata

def get_env_var(name: str, default=None):
    # Retrieve an environment variable safely.
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def normalize_url(url: str):
    """
    Normalize a URL by stripping tracking params and standardizing structure.
    """
    if not url:
        return url
    url = url.strip()
    url = re.sub(r"utm_[^&]+&?", "", url)
    url = url.replace("?&", "?").rstrip("?&")
    return url


def safe_truncate(text: str, max_length: int):
    """
    Truncate a long string safely without cutting in the middle of words.
    """
    if not text:
        return text
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    # Cut nicely at last punctuation or space
    cutoff = max(truncated.rfind("."), truncated.rfind(" "), truncated.rfind("!"), truncated.rfind("?"))
    if cutoff > 0:
        truncated = truncated[:cutoff + 1]
    return truncated + " [...]"


def clean_text(text: str):
    """
    Normalize text: remove extra whitespace, invisible chars, normalize Unicode.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()