import os
import json
import logging
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import get_env_var, normalize_url, safe_truncate
from query_generator import generate_queries
from news_fetcher import gather_articles_for_query
from summarizer import summarize_article, translate_to_en_html
from scorer import compute_strategic_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOMAIN = get_env_var("DOMAIN")
NICHE = get_env_var("NICHE")
MAX_ARTICLES = int(get_env_var("MAX_ARTICLES_PER_QUERY", 10))
MAX_WORKERS = int(get_env_var("MAX_WORKERS", 5))
OUTPUT_DIR = get_env_var("OUTPUT_DIR", "./outputs")
MAX_RETRIES = int(get_env_var("MAX_RETRIES", 2))
os.makedirs(OUTPUT_DIR, exist_ok=True)

def retry(func, *args, retries=MAX_RETRIES, backoff=1, **kwargs):
    """
    Retry a function on exception up to `retries` times with exponential backoff.
    """
    attempt = 0
    while attempt <= retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt > retries:
                logger.warning("Max retries reached for %s: %s", func.__name__, e)
                raise
            else:
                logger.info("Retrying %s (attempt %d/%d) after error: %s", func.__name__, attempt, retries, e)
                time.sleep(backoff * attempt)


def process_article(article, domain, niche):
    """
    Full pipeline for a single article:
    - Translate if needed
    - Summarize
    - Compute strategic signals
    """
    try:
        url = article.get("url")
        if not url:
            return None
        snippet_html = article.get("snippet_html", "")
        snippet_lang = article.get("lang", "en")

        # translate
        translated_html = retry(translate_to_en_html, snippet_html, source_lang=snippet_lang)

        # summerize
        summary = retry(summarize_article, translated_html, domain, " ".join(niche))

        # score
        scoring = retry(compute_strategic_score, summary, domain, " ".join(niche))

        # final output
        record = {
            "headline": article.get("headline", ""),
            "url": url,
            "original_lang": snippet_lang,
            "translated_html": translated_html,
            "snippet_text": article.get("snippet_text", ""),
            "summary": summary,
            "scoring": scoring
        }
        return record
    except Exception as e:
        logger.warning("Failed to process article %s: %s", article.get("url"), e)
        return None

# main pipeline
def run_pipeline(domain, niche, max_articles=MAX_ARTICLES, max_workers=MAX_WORKERS):
    final_results = []
    queries = generate_queries(domain, niche, num_queries=8)
    logger.info("Generated queries: %s", queries)

    for query in queries:
        logger.info("Processing query: %s", query)

        # Fetch articles
        articles = gather_articles_for_query(query, max_articles=max_articles)
        logger.info("Fetched %d articles for query '%s'", len(articles), query)

        # Deduplicate URLs
        seen_urls = set()
        unique_articles = []
        for art in articles:
            norm = normalize_url(art.get("url", ""))
            if norm and norm not in seen_urls:
                seen_urls.add(norm)
                unique_articles.append(art)

        # Process articles concurrently
        processed = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_article = {executor.submit(process_article, art, domain, niche): art for art in unique_articles}
            for future in as_completed(future_to_article):
                try:
                    result = future.result()
                    if result:
                        processed.append(result)
                except Exception as e:
                    logger.warning("Article processing failed: %s", e)

        final_results.extend(processed)

    # Save results
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"news_summary_{timestamp}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)

    logger.info("Pipeline completed. Results saved to %s", output_file)
    return final_results


if __name__ == "__main__":
    results = run_pipeline(DOMAIN, NICHE)
    logger.info("Total articles processed: %d", len(results))