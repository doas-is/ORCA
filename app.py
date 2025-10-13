import os
import threading
import time
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# import agents
from crawler_core import crawl_domain
from competitors_agent import identify_competitors # correct this later
from seo_analyzer import analyze_sites
from news_fetcher import fetch_news
from summarizer import summarize_articles
from translator import translate_text
from scorer import score_articles
from query_generator import generate_queries

load_dotenv()

# basic logging setup
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("orca_app")

# flask app initialization
app = Flask(__name__)

OUTPUT_DIR = os.getenv("OUTPUT_DIR")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# concurrency control (avoid flooding the system)
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS"))
semaphore = threading.Semaphore(MAX_CONCURRENT_TASKS)


# CORE FUNCTIONS

# run the full ORCA pipeline end-to-end
def run_full_pipeline(domain: str, competitors: list, niche: str):
    result = {
        "domain": domain,
        "competitors": competitors,
        "niche": niche,
        "timestamps": {"started": int(time.time())},
        "status": "in_progress"
    }

    try:
        with semaphore:
            # step 1: crawl user website
            logger.info(f"[1/7] Crawling user website: {domain}")
            crawl_data = crawl_domain(domain)

            # step 2: identify competitors
            logger.info(f"[2/7] Identifying competitors for {domain}")
            auto_competitors = identify_competitors(domain, niche)

            # merge known + discovered competitors (dedup later if needed)
            combined_competitors = list(set(competitors + auto_competitors))
            result["competitors_detected"] = combined_competitors

            # step 3: HITL (human-in-the-loop)
            # in real system, Node.js UI will show competitor list and wait for user validation
            # here, we assume user confirms the list automatically
            logger.info("[3/7] Waiting for user validation (simulated HITL step)")
            time.sleep(1)  # simulate short pause

            # step 4: SEO analysis for all domains
            logger.info(f"[4/7] Running SEO analysis for {len(combined_competitors) + 1} domains")
            seo_results = analyze_sites([domain] + combined_competitors)
            result["seo_reports"] = seo_results

            # step 5: fetch and summarize strategic news
            logger.info(f"[5/7] Fetching niche news for '{niche}'")
            news_articles = fetch_news(domain, niche)
            summarized = summarize_articles(news_articles, domain, niche)

            # optional translation if language ≠ English
            translated = [translate_text(item["summary"]) if item.get("lang") != "en" else item["summary"]
                          for item in summarized]

            # step 6: score the insights
            logger.info("[6/7] Scoring summarized news")
            scored = score_articles(translated)

            result["strategic_news"] = scored

            # step 7: generate optimized search queries for next run
            logger.info("[7/7] Generating new queries")
            new_queries = generate_queries(domain, niche)
            result["next_queries"] = new_queries

            # mark completion
            result["status"] = "completed"
            result["timestamps"]["ended"] = int(time.time())
            result["duration_sec"] = result["timestamps"]["ended"] - result["timestamps"]["started"]

            # save output to file
            out_path = os.path.join(OUTPUT_DIR, f"{domain.replace('.', '_')}_analysis.json")
            with open(out_path, "w", encoding="utf-8") as f:
                import json
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Full pipeline completed for {domain}, saved to {out_path}")
            result["output_path"] = out_path

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.exception(f"Pipeline error for {domain}: {e}")

    return result





# FLASK ENDPOINTS

@app.route("/health", methods=["GET"])
def health_check():
    """basic health check for Node.js frontend"""
    return jsonify({"status": "ok", "message": "ORCA Flask backend is alive"})


@app.route("/start-pipeline", methods=["POST"])
def start_pipeline():
    """
    Trigger the full ORCA pipeline.
    Expected JSON:
    {
      "domain": "https://example.com",
      "competitors": ["https://competitor1.com", "https://competitor2.com"],
      "niche": "CRM software"
    }
    """
    try:
        payload = request.get_json(force=True)
        domain = payload.get("domain")
        competitors = payload.get("competitors", [])
        niche = payload.get("niche", "general")

        if not domain:
            return jsonify({"error": "Missing domain"}), 400

        # ============ l partie hedhi a reviser ============
        # run asynchronously in a thread so Flask can respond immediately
        thread = threading.Thread(target=run_full_pipeline, args=(domain, competitors, niche), daemon=True)
        thread.start()

        logger.info(f"Pipeline launched for {domain}")
        return jsonify({"message": "Pipeline started", "domain": domain}), 202

    except Exception as e:
        logger.exception("Error starting pipeline")
        return jsonify({"error": str(e)}), 500


@app.route("/run-crawl", methods=["POST"])
def run_crawl():
    """only run the crawling step (for quick testing)"""
    payload = request.get_json(force=True)
    domain = payload.get("domain")
    if not domain:
        return jsonify({"error": "Missing domain"}), 400
    data = crawl_domain(domain)
    return jsonify(data)


@app.route("/run-seo", methods=["POST"])
def run_seo():
    payload = request.get_json(force=True)
    sites = payload.get("sites", []) # list of domains
    if not sites:
        return jsonify({"error": "No sites provided"}), 400
    result = analyze_sites(sites)
    return jsonify(result)


@app.route("/fetch-news", methods=["POST"])
def run_news_fetch():
    """run news collection for a specific domain/niche"""
    payload = request.get_json(force=True)
    domain = payload.get("domain")
    niche = payload.get("niche", "")
    result = fetch_news(domain, niche)
    return jsonify(result)


# future: add endpoints for daily/weekly scheduled updates
# @app.route("/schedule-report", methods=["POST"])
# def schedule_report():
#     """schedule automatic daily/weekly analysis"""
#     pass

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)