import requests
from src.utils import get_env_var

TRANSLATE_URL = get_env_var("LIBRETRANSLATE_URL")

def translate_to_en_html(text_html, source_lang):
    if not text_html:
        return ""
    if source_lang.lower().startswith("en"):
        return text_html
    try:
        payload = {
            "q": text_html,
            "source": source_lang,
            "target": "en",
            "format": "html" # we send format=html to preserve h1/h2/strong/em/p/ul/li as much as possible.
        }
        # libretranslate supports form data
        r = requests.post(TRANSLATE_URL, data=payload, timeout=30)
        if r.status_code == 200:
            return r.json().get("translatedText", text_html)
        else:
            return text_html
    except Exception:
        return text_html