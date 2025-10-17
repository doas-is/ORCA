# summarize translated html/text for strategic social listening.
# returns structured result:
# - paragraph_summary: short technical paragraph
# - bullet_points: key technical/strategic points
# - top_actions: 3 prioritized recommended actions
# - signals_to_watch: short list of signals or keywords to monitor

import openai
from src.utils import get_env_var
from bs4 import BeautifulSoup

openai.api_key = get_env_var("OPENAI_API_KEY", "")
SUMMARIZER_MODEL = get_env_var("OPENAI_SUMMARIZER_MODEL")

def _strip_html_to_text(html):
    return BeautifulSoup(html, "html.parser").get_text(separator="\n")

def summarize_article(html_or_text, domain, niche):
    # prepare text: we prefer text for LLM but keep html content to preserve headings for context
    text = _strip_html_to_text(html_or_text) if "<" in (html_or_text or "") else (html_or_text or "")
    short_text_for_prompt = text[:6000]  # avoid too long prompts

    prompt = f"""
        you are a competitive intelligence analyst focused on strategic social listening (veille stratégique, concurrentielle, et technologique).
        given the article below (translated to english), produce a structured summary tailored for a strategic intelligence officer in marketing/sales/rd:
        - a short technical paragraph (2-3 sentences) using precise technical terms where relevant.
        - 5 concise bullet points highlighting technical facts, product names, dates, organizations, quantitative numbers, extracted from the article.
        - top 3 prioritized actions (very short) that a marketing/sales/strategy team should consider based on this article.
        - 3 signals to keep monitoring (keywords or behaviors), if available.
        also include any notable quotations or claims and flag them as "claim: ...".
        output as json with keys: paragraph_summary, bullet_points (list), top_actions (list), signals_to_watch (list), notable_claims (list)

        domain: {domain}
        niche: {niche}

        article text:
        \"\"\"{short_text_for_prompt}\"\"\""""
    try:
        resp = openai.ChatCompletion.create(
            model=SUMMARIZER_MODEL,
            messages=[{"role":"user","content":prompt}],
            temperature=0.0,
            max_tokens=600
        )
        raw = resp.choices[0].message.content
        # try to parse json returned by model
        import json
        parsed = {}
        try:
            parsed = json.loads(raw)
        except Exception:
            # if the model returned plain text, try to extract sections heuristically
            parsed = {
                "paragraph_summary": raw.split("\n\n")[0] if raw else "",
                "bullet_points": [],
                "top_actions": [],
                "signals_to_watch": [],
                "notable_claims": []
            }
        return parsed
    except Exception:
        # fallback: naive short summary + empty structured lists
        first_sentences = (text.split(".")[:2])
        return {
            "paragraph_summary": ". ".join(first_sentences).strip(),
            "bullet_points": [],
            "top_actions": [],
            "signals_to_watch": [],
            "notable_claims": []
        }