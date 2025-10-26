#messed up, needs debugging

import requests
from utils import get_env_var
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

#https://rapidapi.com/restyler/api/article-extractor-and-summarizer/playground/apiendpoint_99e4b95c-3adc-4532-8b4e-20795c3c996a
CHAT_API_KEY = get_env_var("OPENAI_API_KEY_SUMMARIZE")
CHAT_API_HOST = get_env_var("OPENAI_API_HOST_SUMMARIZE")
CHAT_MODEL_URL = get_env_var("OPENAI_API_URL_SUMMARIZE")
TRANSLATOR_API_HOST= get_env_var("TRANSLATOR_API_HOST")
TRANSLATOR_API_KEY = get_env_var("TRANSLATOR_API_KEY")
TRANSLATE_BASE_URL=get_env_var("TRANSLATE_BASE_URL")

HEADERS_SUMMERIZE = {
    "x-rapidapi-host": CHAT_API_HOST,
    "x-rapidapi-key": CHAT_API_KEY,
    "Content-Type": "application/json"
}
HEADERS_TRANSLATE = {
    "x-rapidapi-host": TRANSLATOR_API_HOST,
    "x-rapidapi-key": TRANSLATOR_API_KEY,
    "Content-Type": "application/json"
}

def detect_language(text):
    """
    Auto-detect language using RapidAPI (Google Translate).
    """
    try:
        url = f"{TRANSLATE_BASE_URL}/detect"
        payload = {"q": text[:300]}  # shorter snippet
        response = requests.post(url, data=payload, headers=HEADERS_TRANSLATE, timeout=15)
        response.raise_for_status()
        detections = response.json().get("data", {}).get("detections", [])
        if detections and detections[0]:
            return detections[0][0].get("language", "en")
    except Exception:
        pass
    return "en"


def translate_to_en_html(text_html, source_lang=None):
    """
    Translate any HTML/text content to English using RapidAPI.
    """
    if not text_html:
        return ""

    if not source_lang or source_lang.lower().startswith("auto"):
        source_lang = detect_language(text_html)

    if source_lang.lower().startswith("en"):
        return text_html

    try:
        payload = {
            "q": text_html,
            "source": source_lang,
            "target": "en",
            "format": "html"
        }
        response = requests.post(TRANSLATE_BASE_URL, data=payload, headers=HEADERS_TRANSLATE, timeout=30)
        response.raise_for_status()
        return response.json().get("data", {}).get("translations", [{}])[0].get("translatedText", text_html)
    except Exception:
        return text_html


def summarize_article(html_or_text, domain, niche):
    # Generate structured summary.

    text = BeautifulSoup(html_or_text, "html.parser").get_text(separator="\n") if "<" in (html_or_text or "") else (html_or_text or "")
    short_text_for_prompt = text[:6000]

    prompt = f"""
    You are a competitive intelligence analyst. Given the article below (translated to English), produce a structured summary:
    - paragraph_summary: 2-5 technical sentences
    - bullet_points: 5 key points (technical facts, strategic insights, new products, upcoming events or partnerships, numbers, organizations)
    - top_actions: 3 recommended actions for marketing/sales/strategy/technical expertise
    - signals_to_watch: 3 signals or smart keywords to monitor
    - notable_claims: any notable claims or quotes

    Output as JSON with keys: paragraph_summary, bullet_points, top_actions, signals_to_watch, notable_claims

    Domain: {domain}
    Niche: {niche}

    Article text:
    \"\"\"{short_text_for_prompt}\"\"\"
    """

    try:
        payload = {"prompt": prompt, "max_tokens": 650, "temperature": 0.1}
        r = requests.post(CHAT_MODEL_URL, json=payload, headers=HEADERS_SUMMERIZE, timeout=30)
        r.raise_for_status()
        raw = r.json().get("result", "")
        import json
        parsed = {}
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {
                "paragraph_summary": raw.split("\n\n")[0] if raw else "",
                "bullet_points": [],
                "top_actions": [],
                "signals_to_watch": [],
                "notable_claims": []
            }
        return parsed
    except Exception as e:
        logger.warning("Summarizer model failed: %s", e)
        first_sentences = text.split(".")[:2]
        return {
            "paragraph_summary": ". ".join(first_sentences).strip(),
            "bullet_points": [],
            "top_actions": [],
            "signals_to_watch": [],
            "notable_claims": []
        }