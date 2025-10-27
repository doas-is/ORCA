import os
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import requests
from utils import getenv

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("CHAT_API_KEY")
RAPIDAPI_HOST = os.getenv("CHAT_API_HOST")
MODEL_URL = os.getenv("CHAT_MODEL_URL")

PROMPT_MIN_SCORE = int(os.getenv("PROMPT_MIN_SCORE"))
num_queries=os.getenv("NUM_QUERIES")


def query_model(prompt, temperature=0.2, max_tokens=100) -> str:
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt, "max_tokens": max_tokens, "temperature": temperature}
    try:
        r = requests.post(MODEL_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json().get("result", "")
    except Exception as e:
        logger.warning("Query model failed: %s", e)
        return ""

def strip_code_fences(text: str) -> str:
    # cleans the output """[query1, query2...]"""
    if not text:
        return ""
    return text.replace("```", "").strip()

import re
from textblob import TextBlob

def heuristic_score(query: str, domain: str = "", niche: str = "") -> int:
    q = query.lower().strip()
    q_terms = re.findall(r"\w+", q)
    domain_terms = re.findall(r"\w+", domain.lower())
    niche_terms = re.findall(r"\w+", niche.lower())

    # Relevance
    overlap = len(set(q_terms) & (set(domain_terms) | set(niche_terms)))
    rel_score = min(100 * overlap / max(1, len(set(domain_terms + niche_terms))), 100)

    # Freshness intent 
    freshness_keywords = ["2025", "2026", "latest", "recent", "breaking", "update", "trend", "trends", "current"]
    fresh_hits = sum(k in q for k in freshness_keywords)
    fresh_score = min(20 * fresh_hits, 100)

    # Source credibility
    credibility_terms = ["site:", "gov", "bbc","cnn", "reuters", "time", "news.google","bloomberg", "apnews", "official", "press release"]
    cred_hits = sum(k in q for k in credibility_terms)
    cred_score = min(25 * cred_hits, 100)

    # Specificity (context-aware)
    # If query has “updates” but also domain terms, reward it.
    vague_only = any(v in q for v in ["news", "update", "updates", "trends"]) and overlap == 0
    length_factor = len(q_terms)
    if vague_only:
        spec_score = max(10 * length_factor - 20, 20)  # penalize vague + short
    else:
        spec_score = min(10 * length_factor + (5 if "site:" in q else 0), 100)  # reward structured query

    # spelling_errors 
    blob = TextBlob(query)
    spelling_errors = abs(len(blob.correct().split()) - len(blob.words))
    ling_score = max(100 - 10 * spelling_errors, 60)

    # Weighted final score
    final = (
        0.35 * rel_score +
        0.20 * fresh_score +
        0.20 * cred_score +
        0.15 * spec_score +
        0.10 * ling_score
    )

    return int(round(min(final, 100)))



def generate_queries(domain: str, niche: str, num_queries: int) -> List[str]:
    prompt = f"""
        You are a news search strategist.

        Generate {num_queries} short, precise search queries (2–6 words) to find the most recent factual news about:
        Domain: {domain}
        Niche: {niche}

        Requirements:
        - Focus on recent context (2025-2026).
        - Prefer official and credible sources (e.g., site:reuters.com, site:bbc.com, site:gov).
        - Avoid duplicates, vague terms
        - Return only a JSON array of strings.
    """
    response = query_model(prompt)
    # parse each line, remove numbers/dashes
    queries = []
    for line in response.splitlines():
        clean = line.strip().lstrip("0123456789.- ").strip()
        if clean:
            queries.append(clean)
        if len(queries) >= num_queries:
            break
    logger.info("Generated queries: %s", queries)
    return queries


def improve_query(q: str, domain: str, niche: str) -> str:
    prompt = f"I have written this search query in order to search for relevant news about the domain of {domain}, niche: {niche}. Improve it (max 8 words) for precision: '{q}'. Return only the rewritten query."
    try:
        improved = query_model(prompt, temperature=0.3, max_tokens=50)
        return strip_code_fences(improved) or q
    except Exception:
        if "recent" not in q.lower():
            q += " recent"
        return q.strip()

def score_queries(queries: List[str], domain: str, niche: str) -> List[Dict[str, Any]]:
    if not queries:
        return []
    results = []
    for q in queries:
        try:
            score = heuristic_score(q)
        except Exception:
            score = 50
        results.append({"query": q, "score": score, "feedback": "heuristic fallback"})
    return results


# PUBLIC INTERFACE
def run_query_generator(domain: str, niche: str, num: int = 8) -> Dict[str, Any]:
    logger.info(f"Generating queries for domain='{domain}', niche='{niche}'")

    queries = generate_queries(domain, niche, num)
    scored = score_queries(queries, domain, niche)

    # improve low-score queries concurrently
    results = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(improve_query, q["query"], domain, niche): q for q in scored if q["score"] < PROMPT_MIN_SCORE}
        for q in scored:
            if q["score"] >= PROMPT_MIN_SCORE:
                results.append({**q, "improved": q["query"]})
        for fut in as_completed(futures):
            q = futures[fut]
            try:
                improved_q = fut.result()
                results.append({**q, "improved": improved_q})
            except Exception as e:
                results.append({**q, "improved": q["query"], "error": str(e)})

    structured_output = {
        "domain": domain,
        "niche": niche,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "queries": results
    }

    os.makedirs("./outputs", exist_ok=True)
    fname = f"./outputs/query_generator_{domain.replace(' ','_')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(structured_output, f, indent=2, ensure_ascii=False)

    logger.info(f"Generated {len(results)} queries → saved to {fname}")
    return structured_output


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    domain = os.getenv("DOMAIN", "AI research")
    niche = os.getenv("NICHE", "generative AI applications")
    run_query_generator(domain, niche, num=10)
