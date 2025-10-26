import argparse
import json
import logging
import os
import random
import re
import sys
import time
from collections import deque
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

# ---------- Configuration ----------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/115.0 Safari/537.36",
]

from dotenv import load_dotenv
load_dotenv()
import os

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
DEFAULT_MAX_PAGES = int(os.getenv("DEFAULT_MAX_PAGES", 30))
DEFAULT_DEPTH = int(os.getenv("DEFAULT_DEPTH", 3))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 15))
LOG_FILE = os.path.join(OUTPUT_DIR, "crawler.log")

os.makedirs(OUTPUT_DIR, exist_ok=True)

logger = logging.getLogger("business_crawler")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(ch)

session = requests.Session()
session.headers.update({"Accept-Language": "en-US,en;q=0.9"})


# ---------- Utilities ----------
def pick_user_agent():
    return random.choice(USER_AGENTS)


def normalize_url(url):
    url = url.strip()
    if not url:
        return None
    if not urlparse(url).scheme:
        url = "http://" + url
    return url


def is_same_domain(base, url):
    try:
        return urlparse(base).netloc == urlparse(url).netloc
    except Exception:
        return False


def allowed_by_robots(url, ua="Crawler"):
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = RobotFileParser()
        rp.set_url(urljoin(base, "/robots.txt"))
        rp.read()
        allowed = rp.can_fetch(ua, url)
        delay = rp.crawl_delay(ua) or rp.crawl_delay("*") or 0
        return allowed if allowed is not None else True, delay or 0
    except Exception:
        return True, 0


def safe_get(url, timeout=REQUEST_TIMEOUT):
    headers = {"User-Agent": pick_user_agent()}
    try:
        return session.get(url, headers=headers, timeout=timeout)
    except requests.RequestException:
        return None


# ---------- Extraction ----------
BUSINESS_KEYWORDS = [
    "partner", "client", "customer", "case", "portfolio",
    "project", "about", "service",
    "industries", "expertise"
]
EXCLUDE_KEYWORDS = [
    "privacy", "cookie", "terms", "login", "register", "faq", "policy"
]

NICHE_KEYWORDS = [
    # AI & Tech
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "big data", "data science", "analytics", "data analytics", "computer vision",
    "natural language", "nlp", "automation", "robotics", "iot", "edge computing",
    "cloud", "aws", "azure", "gcp", "devops", "kubernetes", "blockchain",
    # Marketing & Design
    "seo", "sem", "digital marketing", "branding", "ux", "ui", "graphic design",
    # Finance & Business
    "fintech", "insurtech", "erp", "crm", "accounting", "business intelligence",
    "consulting", "strategy", "outsourcing",
    # Cybersecurity
    "cybersecurity", "security", "pentest", "encryption", "firewall",
    "zero trust", "identity management",
    # Healthcare & Biotech
    "healthtech", "medtech", "biotech", "pharma", "telemedicine",
    # Industry & Energy
    "manufacturing", "automation", "renewable", "energy", "smart grid",
    "industry 4.0",
    # Education & GovTech
    "edtech", "govtech", "public sector", "training", "research"
]


def extract_business_signals(soup):
    text = soup.get_text(separator=" ", strip=True)
    text_lower = text.lower()

    partners, clients = [], []
    # Look for list items and table entries
    for li in soup.find_all("li"):
        line = li.get_text(strip=True)
        parent_text = li.find_parent().get_text().lower() if li.find_parent() else ""
        if "partner" in parent_text:
            partners.append(line)
        if "client" in parent_text or "customer" in parent_text:
            clients.append(line)

    # Regex fallback
    partners += re.findall(
        r"partner(?:s|ship)?(?: with)?[:\-]?\s*([A-Z][A-Za-z0-9&\.\- ]{2,80})", text
    )
    clients += re.findall(
        r"(?:clients|customers)[:\-]?\s*([A-Z][A-Za-z0-9&\.\- ]{2,80})", text
    )

    niches = [k for k in NICHE_KEYWORDS if k in text_lower]
    return {
        "partners": list(set(partners)),
        "clients": list(set(clients)),
        "niches": list(set(niches)),
    }


# ---------- Core Crawl ----------
def crawl_domain(start_url, max_pages=DEFAULT_MAX_PAGES, depth_limit=DEFAULT_DEPTH):
    start_url = normalize_url(start_url)
    if not start_url:
        return None

    allowed, delay = allowed_by_robots(start_url)
    if not allowed:
        logger.warning(f"robots.txt disallows crawling {start_url}")
        return None

    seen = set()
    queue = deque([(start_url, 0)])
    pages_data = []
    partners_total, clients_total, niches_total = set(), set(), set()

    while queue and len(pages_data) < max_pages:
        url, depth = queue.popleft()
        if url in seen or depth > depth_limit:
            continue
        seen.add(url)

        resp = safe_get(url)
        if not resp or "text/html" not in (resp.headers.get("Content-Type") or ""):
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        signals = extract_business_signals(soup)

        partners_total.update(signals["partners"])
        clients_total.update(signals["clients"])
        niches_total.update(signals["niches"])

        # Filter and enqueue internal business-related links
        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"])
            if not is_same_domain(start_url, link):
                continue
            if any(k in link.lower() for k in EXCLUDE_KEYWORDS):
                continue
            if any(k in link.lower() for k in BUSINESS_KEYWORDS):
                if link not in seen:
                    queue.append((link, depth + 1))

        pages_data.append({
            "url": url,
            "depth": depth,
            "partners_found": signals["partners"],
            "clients_found": signals["clients"],
            "niches_found": signals["niches"],
        })
        logger.info(f"[{len(pages_data)}/{max_pages}] Crawled {url} (depth={depth})")

        if delay:
            time.sleep(delay)

    # ----- Strategic Summary -----
    insights = []
    if partners_total:
        insights.append(f"Company has {len(partners_total)} detected partners.")
    if clients_total:
        insights.append(f"Company serves about {len(clients_total)} detected clients.")
    if niches_total:
        top_niches = ', '.join(list(niches_total)[:5])
        insights.append(f"Niches detected: {top_niches}.")
    if not insights:
        insights.append("No clear business signals detected; website may be minimal or blocked.")

    summary_comment = " ".join(insights)

    result = {
        "domain": urlparse(start_url).netloc,
        "crawl_summary": {
            "start_url": start_url,
            "pages_crawled": len(pages_data),
            "crawl_depth": depth_limit,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        "business_overview": {
            "partners_found": sorted(partners_total),
            "clients_found": sorted(clients_total),
            "niches_detected": sorted(niches_total),
        },
        "strategic_insights": {
            "key_pages_scanned": len(pages_data),
            "summary_comment": summary_comment,
            "key_findings": insights,
        },
        "sample_pages": pages_data[:10],
    }

    # Console Summary
    logger.info("\n--- Strategic Summary ---")
    logger.info(f"Domain: {result['domain']}")
    logger.info(f"Partners found: {len(partners_total)}")
    logger.info(f"Clients found: {len(clients_total)}")
    logger.info(f"Niches detected: {', '.join(sorted(list(niches_total))[:10])}")
    logger.info(f"Insights: {summary_comment}\n")

    return result


# ---------- Save ----------
def save_result_to_file(result, prefix="business_overview"):
    domain = result.get("domain") or "unknown"
    safe_name = re.sub(r"[^a-z0-9]", "_", domain.lower())[:80]
    out_path = os.path.join(OUTPUT_DIR, f"{prefix}_{safe_name}_{int(time.time())}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved: {out_path}")
    return out_path


# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="Strategic Business Intelligence Crawler")
    p.add_argument("url", help="Start URL to crawl")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    return p.parse_args()


def main():
    args = parse_args()
    res = crawl_domain(args.url, max_pages=args.max_pages, depth_limit=args.depth)
    if res:
        save_result_to_file(res)


if __name__ == "__main__":
    sys.exit(main())