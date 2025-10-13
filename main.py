# python -m playwright install 
# orchestrator: generate queries, gather articles, translate, summarize, score, and store json.

import time
import sys
from src.utils import get_env_var, load_json, save_json, current_timestamp, normalize_url
from src.query_generator import generate_queries
from src.news_fetcher import gather_articles_for_query
from src.translator import translate_to_en_html
from src.summarizer import summarize_article
from src.scorer import compute_strategic_score
from datetime import datetime

DOMAIN = get_env_var("DOMAIN")
NICHE = get_env_var("NICHE")
AUTOMATIC = get_env_var("AUTOMATIC_SCRAPING")
UPDATE_HOURS = int(get_env_var("UPDATE_INTERVAL_HOURS"))
OUTPUT_FILE = get_env_var("OUTPUT_FILE")
MAX_ARTICLES = int(get_env_var("MAX_ARTICLES_PER_QUERY"))

def run_once():
    # load existing storage to support novelty checks and dedup
    db = load_json(OUTPUT_FILE) or {}
    if "articles" not in db:
        db["articles"] = []
    existing_titles = [a.get("headline","") for a in db["articles"]]
    existing_urls = set([normalize_url(a.get("source_url","")) for a in db["articles"] if a.get("source_url")])
    fetched_at = current_timestamp()
    result_batch = {
        "domain": DOMAIN,
        "niche": NICHE,
        "fetched_at": fetched_at,
        "articles": []
    }

    # generate queries
    print("generating queries...")
    queries = generate_queries(DOMAIN, NICHE, num_queries=8)
    print(f"queries: {queries}")

    # for each query, gather articles (api + google news complement), then process them
    for q in queries:
        print(f"gathering articles for query: {q}")
        articles = gather_articles_for_query(q, max_articles=MAX_ARTICLES)
        print(f"found {len(articles)} raw articles for this query")
        for art in articles:
            url = art.get("url")
            if not url:
                continue
            norm = normalize_url(url)
            if norm in existing_urls:
                # skip duplicates already in DB
                continue
            # snippet_html preferred, snippet_text used for safety
            snippet_html = art.get("snippet_html", "") or f"<p>{art.get('snippet_text','')}</p>"
            source_lang = art.get("lang", "en")
            # translate html-preserving
            snippet_en_html = translate_to_en_html(snippet_html, source_lang)
            # summarize (structured)
            summary_struct = summarize_article(snippet_en_html, DOMAIN, NICHE)
            # headline fallback: if headline missing try first h1 or first sentence
            headline = art.get("headline") or (summary_struct.get("paragraph_summary","").split(".")[0] if summary_struct.get("paragraph_summary") else "")
            # compute strategic scores
            scores = compute_strategic_score(
                text=summary_struct.get("paragraph_summary","") or snippet_en_html,
                title=headline,
                url=url,
                domain=DOMAIN,
                niche=NICHE,
                existing_titles=existing_titles
            )
            # prepare stored entry
            entry = {
                "headline": headline,
                "source_url": url,
                "snippet_original_html": snippet_html,
                "snippet_en_html": snippet_en_html,
                "summary_structured": summary_struct,
                "scores": scores,
                "source_language": source_lang,
                "collected_at": current_timestamp()
            }
            # append to result batch and to db articles
            result_batch["articles"].append(entry)
            db["articles"].append({
                "headline": headline,
                "source_url": url,
                "collected_at": current_timestamp()
            })
            existing_titles.append(headline)
            existing_urls.add(norm)
            # respect light sleep to avoid hammering sites
            time.sleep(0.5)

    # save new results appended to existing db (we keep both)
    # if file didn't exist previously, db now contains new articles
    save_json(db, OUTPUT_FILE)
    # also save batch for quick retrieval of latest run
    save_json(result_batch, OUTPUT_FILE.replace(".json", "_latest.json"))
    print(f"saved {len(result_batch['articles'])} new articles. output -> {OUTPUT_FILE}")
    return result_batch

def main():
    if AUTOMATIC:
        print("automatic scraping enabled. running in loop.")
        while True:
            run_once()
            print(f"sleeping for {UPDATE_HOURS} hours...")
            time.sleep(UPDATE_HOURS * 3600)
    else:
        print("manual mode (run once). starting pipeline.")
        run_once()
        print("done. exit.")

if __name__ == "__main__":
    main()