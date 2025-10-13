"""
This agent performs a strategic seo audit for a given [list of webstes].
it pulls data from two rapidapi endpoints:
  1. website analyze & seo audit
  2. seo keyword research
output : json file.
"""
import os
import json
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

# load environment variables
load_dotenv()

# rapidapi credentials
SEO_WEBSITE_ANALYSER_API_KEY = os.getenv("SEO_WEBSITE_ANALYSER_API_KEY")
SEO_WEBSITE_ANALYSER_API_HOST = os.getenv("SEO_WEBSITE_ANALYSER_API_HOST")
KEYWORD_RESEARCH_API_KEY = os.getenv("KEYWORD_RESEARCH_API_KEY")
KEYWORD_RESEARCH_API_HOST = os.getenv("KEYWORD_RESEARCH_API_HOST")

OUTPUT_FILE = os.getenv("OUTPUT_SEO_FILE")

# helper utilities
def current_timestamp():
    return datetime.utcnow().isoformat()

def save_json(data, path):
    """save dictionary to json"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_existing_json(path):
    """load existing json or create empty structure"""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"timestamp": current_timestamp(), "domains_analyzed": []}

# api requests
def call_website_analyzer(domain):
    #returns dictionary with technical details
    url = "https://website-analyze-and-seo-audit-pro.p.rapidapi.com/aiseo.php"
    params = {"url": domain}
    headers = {
        "x-rapidapi-key": SEO_WEBSITE_ANALYSER_API_KEY,
        "x-rapidapi-host": SEO_WEBSITE_ANALYSER_API_HOST,
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"[warn] api call failed for {domain}, status {r.status_code}")
            return {}
    except Exception as e:
        print(f"[error] website analyzer failed for {domain}: {e}")
        return {}

def call_keyword_research(domain, main_kw=""):
    #returns dictionary with keyword density & suggestions
    url = "https://seo-keyword-research.p.rapidapi.com/keyworddensity.php"
    query = {"keyword": main_kw or domain.split(".")[0], "site": domain}
    headers = {
        "x-rapidapi-key": KEYWORD_RESEARCH_API_KEY,
        "x-rapidapi-host": KEYWORD_RESEARCH_API_HOST,
    }
    try:
        r = requests.get(url, headers=headers, params=query, timeout=60)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"[warn] keyword api failed for {domain}, status {r.status_code}")
            return {}
    except Exception as e:
        print(f"[error] keyword research failed for {domain}: {e}")
        return {}


# data parsing helpers

def classify_issue_severity(issues):
    # simple heuristic to classify issues into critical, moderate, minor based on keywords in issue text
    critical, moderate, minor = [], [], []
    for issue in issues:
        txt = issue.lower()
        if any(k in txt for k in [
            "missing title", "broken link", "ssl", "404", "not secure",
            "500 error", "503", "timeout", "401 unauthorized", "cloudflare protection", "bot detected",
            "captcha", "ip blocked", "rate limited", "access denied",
            "dns error", "host not found", "connection reset","invalid ssl", "certificate error", "robot.txt block"
        ]):
            critical.append(issue)
        elif any(k in txt for k in [
            "slow", "redirect", "duplicate","slow response", "partial content", 
            "missing data", "incomplete parse","encoding error", "character encoding", "html malformed",
            "javascript required", "ajax content", "dynamic content missing",
            "redirect loop", "too many redirects", "meta redirect",
            "element not found", "selector failed", "xpath error",
            "content changed", "layout changed", "structure modified"
            ]):
            moderate.append(issue)
        else:
            minor.append(issue)
    return {"critical": critical, "moderate": moderate, "minor": minor}

def find_keyword_opportunities(keyword_data):
    """
    flag potential high traffic + low kd (keyword difficulty) opportunities
    expects keyword_data to contain traffic / kd values
    """
    opportunities = []
    try:
        for kw in keyword_data.get("data", []):
            traffic = float(kw.get("traffic", 0))
            kd = float(kw.get("kd", 0))
            if traffic > 1000 and kd < 30:
                opportunities.append({
                    "keyword": kw.get("keyword"),
                    "traffic": traffic,
                    "kd": kd
                })
    except Exception:
        pass
    return opportunities

def extract_main_metrics(audit_json):
    #parse main technical metrics from website audit response
    try:
        return {
            "overall_score": audit_json.get("overall_score") or audit_json.get("seo_score") or 0,
            "page_speed": audit_json.get("page_speed", {}).get("score", 0),
            "mobile_friendly": audit_json.get("mobile_friendly", True),
            "domain_authority": audit_json.get("domain_authority", 0),
            "broken_links": audit_json.get("broken_links", 0),
            "meta_tags": audit_json.get("meta_tags", []),
            "title": audit_json.get("title", ""),
            "description": audit_json.get("description", ""),
        }
    except Exception:
        return {}

# -----------------------------
# main analyzer logic
# -----------------------------

def analyze_domain(domain, main_keyword=""):
    print(f"\n[info] analyzing domain: {domain}")

    # step 1: call both apis
    audit_data = call_website_analyzer(domain)
    time.sleep(1)  # avoid rate limit
    keyword_data = call_keyword_research(domain, main_keyword)

    # step 2: extract metrics
    metrics = extract_main_metrics(audit_data)

    # step 3: classify issues by severity
    issues = audit_data.get("issues", []) if isinstance(audit_data.get("issues"), list) else []
    issue_classes = classify_issue_severity(issues)

    # step 4: keyword density and opportunities
    keyword_density = {}
    try:
        for kw in keyword_data.get("keyword_density", []):
            keyword_density[kw.get("keyword")] = kw.get("density")
    except Exception:
        pass

    opportunities = find_keyword_opportunities(keyword_data)

    # step 5: build structured domain result
    result = {
        "domain": domain,
        "technical_audit": metrics,
        "technical_issues": issue_classes,
        "keyword_analysis": {
            "keyword_density": keyword_density,
            "high_traffic_low_kd": opportunities,
        },
        "warnings": issue_classes.get("critical", []),
        "notes": "further analysis to be done by llm-based seo agent (gpt-4o-mini)",
        "crawl4ai_data_hook": "placeholder - merge crawl4ai semantic data here later",
    }

    return result

def load_competitors_from_file(path):
    # load competitor urls written by teh competitor_identifier agent, which returns a list of urls.
    try:
        if not os.path.exists(path):
            print(f"[warn] competitor file not found: {path}")
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # support both {"competitors":[...]} and plain list
            if isinstance(data, dict) and "competitors" in data:
                return data["competitors"]
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[error] failed to load competitors from {path}: {e}")
        return []


# main entrypoint
def main():
    domains = load_competitors_from_file("outputs/competitors.json") or ["codeconia.com"] #replace this with the actual path

    # load old results if exist
    data = load_existing_json(OUTPUT_FILE)
    analyzed = []

    for domain in domains:
        domain_result = analyze_domain(domain)
        analyzed.append(domain_result)
        # brief delay to respect rate limits
        time.sleep(2)

    # update json structure
    data["timestamp"] = current_timestamp()
    data["domains_analyzed"] = analyzed

    save_json(data, OUTPUT_FILE)
    print(f"\n[done] SEO analysis complete. results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
