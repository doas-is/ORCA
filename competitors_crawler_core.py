"""
Usage examples:
  python crawler_core.py https://example.com --max-pages 15
  python crawler_core.py               # will prompt for URL(s) interactively
"""

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

from dotenv import load_dotenv
load_dotenv()
import os


# Optional imports (gracefully handled)
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

try:
    # placeholder for crawl4ai (optional). If you use it, ensure it's installed.
    import crawl4ai  # type: ignore
    CRAWL4AI_AVAILABLE = True
except Exception:
    CRAWL4AI_AVAILABLE = False

# ---------- Configuration ----------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "OrendaCrawler/1.0 (+https://example.com/orenda)",
]

COMPETITORS_LINK= os.getenv("COMPETITORS_LINK")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
DEFAULT_MAX_PAGES = int(os.getenv("DEFAULT_MAX_PAGES", 30))
DEFAULT_DEPTH = int(os.getenv("DEFAULT_DEPTH", 3))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 15))
LOG_FILE = os.path.join(OUTPUT_DIR, "crawler.log")

# Create output dir
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------- Logging ----------
logger = logging.getLogger("crawler_core")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

# ---------- Utilities ----------
def pick_user_agent():
    return random.choice(USER_AGENTS)

session = requests.Session()
session.headers.update({"Accept-Language": "en-US,en;q=0.9"})

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

# ---------- Robots ----------
def allowed_by_robots(url, ua_token="OrendaCrawler"):
    """
    Returns (allowed: bool, crawl_delay_seconds: float)
    If robots.txt can't be read, defaults to allowed=True and delay=0.
    """
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = RobotFileParser()
        rp.set_url(urljoin(base, "/robots.txt"))
        try:
            rp.read()
        except Exception as e:
            logger.debug(f"robots.txt read failed for {base}: {e}")
            return True, 0
        allowed = rp.can_fetch(ua_token, url)
        if allowed is None:
            allowed = True
        delay = rp.crawl_delay(ua_token) or rp.crawl_delay("*") or 0
        return allowed, delay or 0
    except Exception as e:
        logger.debug(f"robots parse error for {url}: {e}")
        return True, 0

# HTTP fetch
def safe_get(url, timeout=REQUEST_TIMEOUT, allow_insecure_fallback=True):
    """
    Returns requests.Response or None.
    """
    headers = {"User-Agent": pick_user_agent()}
    try:
        resp = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return resp
    except requests.exceptions.SSLError as e:
        logger.warning(f"SSL error for {url}: {e}")
        if allow_insecure_fallback:
            try:
                resp = session.get(url, headers=headers, timeout=timeout, verify=False)
                return resp
            except Exception:
                return None
        return None
    except requests.exceptions.RequestException as e:
        logger.debug(f"request exception for {url}: {e}")
        return None

def looks_like_block_or_captcha(html_text: str) -> bool:
    if not html_text:
        return False
    block_indicators = [
        "captcha", "are you a human", "access denied", "please verify", "cloudflare", "bot verification",
        "/challenge", "recaptcha", "jschl_vc", "cf_chl_jschl_tk"
    ]
    t = html_text.lower()
    return any(ind in t for ind in block_indicators)

# Playwright fallback fetch
def fetch_with_playwright(url, timeout_ms=30000):
    if not PLAYWRIGHT_AVAILABLE:
        logger.debug("Playwright not available")
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(user_agent=pick_user_agent(), viewport={"width": 1280, "height": 800})
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except PlaywrightTimeout:
                logger.debug(f"Playwright timed out while loading {url}")
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        logger.debug(f"Playwright fetch error for {url}: {e}")
        return None

def fetch_html(url, use_playwright_if_blocked=True):
    r = safe_get(url)
    if not r:
        if use_playwright_if_blocked and PLAYWRIGHT_AVAILABLE:
            return fetch_with_playwright(url)
        return None
    # treat 2xx/3xx as ok, otherwise return None (but keep response to inspect)
    if r.status_code >= 400:
        logger.debug(f"HTTP {r.status_code} for {url}")
        return None
    content_type = (r.headers.get("Content-Type") or "").lower()
    if not any(k in content_type for k in ("html", "xhtml", "xml")) and not content_type.startswith("text/"):
        logger.debug(f"non-HTML content-type '{content_type}' for {url}")
        return None
    text = r.text or ""
    if looks_like_block_or_captcha(text) and use_playwright_if_blocked and PLAYWRIGHT_AVAILABLE:
        logger.info(f"block/captcha suspected at {url}, trying playwright render")
        return fetch_with_playwright(url)
    return text

# Parsers / extractors
def extract_basic_seo(soup, url):
    def get_meta(name):
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        return tag.get("content").strip() if tag and tag.get("content") else None

    title = (soup.title.string.strip() if soup.title and soup.title.string else None)
    meta_desc = get_meta("description")
    canonical = None
    link_canon = soup.find("link", rel=lambda v: v and "canonical" in v.lower())
    if link_canon and link_canon.get("href"):
        canonical = urljoin(url, link_canon.get("href"))
    h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")]
    # text snippet: first 300 chars of visible text
    for script in soup(["script", "style", "noscript"]):
        script.decompose()
    body_text = soup.get_text(separator=" ", strip=True)
    snippet = (body_text[:300] + "...") if body_text and len(body_text) > 300 else body_text
    # find links
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        links.append(urljoin(url, href))
    # images
    imgs = [urljoin(url, img.get("src")) for img in soup.find_all("img") if img.get("src")]
    return {
        "title": title,
        "meta_description": meta_desc,
        "canonical": canonical,
        "h1": h1_tags,
        "snippet": snippet,
        "links": links,
        "images": imgs,
    }

def detect_business_signals(text, base_url=None):  # important
    # Fetch partners page if base_url is provided
    if base_url:
        try:
            resp = requests.get(base_url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # look for a link containing "partner"
            partner_page_url = None
            for a in soup.find_all("a", href=True):
                href = a['href'].lower()
                if "partner" in href:
                    partner_page_url = urljoin(base_url, a['href'])
                    break

            # if found, fetch its text
            if partner_page_url:
                resp = requests.get(partner_page_url, timeout=10)
                resp.raise_for_status()
                text = resp.text  # override input text for regex extraction
        except requests.RequestException:
            pass  # fallback: keep original text

    if not text:
        return {}

    t = text.lower()
    partners = []
    clients = []
    niche_terms = []

    # common headings/phrases to look for
    partner_indicators = ["partners", "our partners", "partner with", "partnerships", "partnered with", "collaborators"]
    client_indicators = ["clients", "our clients", "customers", "customers include", "trusted by"]
    niche_indicators = ["seo", "digital marketing", "cybersecurity", "web development", "saas", "e-commerce", "ai", "artificial intelligence","Travel Management", "data", "fintech", "cloud"]

    for phrase in partner_indicators:
        if phrase in t:
            partners.append(phrase)
    for phrase in client_indicators:
        if phrase in t:
            clients.append(phrase)
    for phrase in niche_indicators:
        if phrase in t:
            niche_terms.append(phrase)

    # attempt to pull simple "partner names" by regex near the word partner (very heuristic)
    partner_names = re.findall(
        r"(?:partner(?:s|ship)?(?: with)?[:\-]?\s*)([A-Z][A-Za-z0-9&\.\- ]{2,80})", 
        text
    )
    clients_found = re.findall(
        r"(?:clients include|clients[:\-]?\s*)([A-Z][A-Za-z0-9,&\.\- ]{2,120})", 
        text
    )

    return {
        "partner_indicators": partners,
        "client_indicators": clients,
        "niche_terms": list(set(niche_terms)),
        "partner_name_matches": partner_names,
        "client_name_matches": clients_found,
    }

# ==========================================================================
# Crawl logic 

def crawl_domain(start_url, max_pages=DEFAULT_MAX_PAGES, obey_robots=True):
    logger.info(f"Starting crawl: {start_url} (max_pages={max_pages})")
    start_url = normalize_url(start_url)
    if not start_url:
        logger.error("Invalid start URL")
        return None

    allowed, delay = (True, 0)
    if obey_robots:
        allowed, delay = allowed_by_robots(start_url)
        if not allowed:
            logger.warning(f"Robots.txt disallows crawling {start_url}")
            return None
    if delay > 0:
        logger.info(f"Robots.txt crawl-delay recommended: {delay}s")

    domain = urlparse(start_url).netloc
    seen = set()
    queue = deque([start_url])
    results = []
    pages_crawled = 0

    while queue and pages_crawled < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        if obey_robots:
            ok, _ = allowed_by_robots(url)
            if not ok:
                logger.debug(f"Skipping {url} due robots")
                continue
        # polite delay
        if delay:
            time.sleep(delay)

        html = fetch_html(url)
        if not html:
            logger.debug(f"No HTML fetched for {url}")
            pages_crawled += 1
            continue

        soup = BeautifulSoup(html, "html.parser")
        seo = extract_basic_seo(soup, url)
        body_text = soup.get_text(separator=" ", strip=True)[:3000]
        business = detect_business_signals(body_text)

        # classify links: internal or external
        internal_links = []
        external_links = []
        for link in seo["links"]:
            if not link:
                continue
            # skip javascript/mailto anchors
            if link.startswith("javascript:") or link.startswith("mailto:") or link.startswith("#"):
                continue
            absolute = urljoin(url, link)
            if is_same_domain(start_url, absolute):
                internal_links.append(absolute)
            else:
                external_links.append(absolute)

        page_result = {
            "url": url,
            "status_time": datetime.utcnow().isoformat() + "Z",
            "title": seo.get("title"),
            "meta_description": seo.get("meta_description"),
            "h1": seo.get("h1"),
            "canonical": seo.get("canonical"),
            "snippet": seo.get("snippet"),
            "text_sample": body_text[:2000],
            "internal_links_count": len(internal_links),
            "external_links_count": len(external_links),
            "internal_links_sample": internal_links[:20],
            "external_links_sample": external_links[:20],
            "images_count": len(seo.get("images", [])),
            "business_signals": business,
        }
        results.append(page_result)
        pages_crawled += 1
        logger.info(f"[{pages_crawled}/{max_pages}] Crawled: {url} (internal:{len(internal_links)} external:{len(external_links)})")

        # Enqueue internal links (breadth-first), avoid query fragments & large files
        for link in internal_links:
            # avoid binary files and long query strings (heuristic)
            if re.search(r"\.(jpg|jpeg|png|gif|pdf|zip|rar|tgz|mp4|mp3)(?:$|\?)", link, re.I):
                continue
            if link in seen:
                continue
            # keep path depth reasonable
            queue.append(link)

    # Summarize domain-level findings (very simple aggregation)
    all_text = " ".join([r.get("text_sample", "") for r in results])
    domain_summary = {
        "start_url": start_url,
        "domain": domain,
        "pages_crawled": len(results),
        "top_titles": [r.get("title") for r in results if r.get("title")][:5],
        "top_h1s": sum([r.get("h1") for r in results if r.get("h1")], [])[:10],
        "likely_niches": list(set(sum([r.get("business_signals", {}).get("niche_terms", []) for r in results], []))),
        "partner_indicators": list(set(sum([r.get("business_signals", {}).get("partner_indicators", []) for r in results], []))),
        "client_indicators": list(set(sum([r.get("business_signals", {}).get("client_indicators", []) for r in results], []))),
        "partner_name_matches": list(set(sum([r.get("business_signals", {}).get("partner_name_matches", []) for r in results], [])))[:20],
        "client_name_matches": list(set(sum([r.get("business_signals", {}).get("client_name_matches", []) for r in results], [])))[:20],
        "sample_pages": results[:10],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    return domain_summary

# Save results 
def save_result_to_file(result, prefix="result"):
    domain = result.get("domain") or urlparse(result.get("start_url", "")).netloc or "outputs"
    safe_name = re.sub(r"[^a-z0-9]", "_", domain.lower())[:100]
    out_path = os.path.join(OUTPUT_DIR, f"{prefix}_{safe_name}_{int(time.time())}.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved results to {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"Failed to save result: {e}")
        return None

# ---------- CLI / Main ----------
def parse_args():
    p = argparse.ArgumentParser(description="Crawler for SEO & business overview")
    p.add_argument("urls", nargs="*", help="Start URL(s). If none given, you'll be prompted.")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help=f"Max pages to crawl (default {DEFAULT_MAX_PAGES})")
    p.add_argument("--no-robots", dest="robots", action="store_false", help="Ignore robots.txt")
    return p.parse_args()

def prompt_for_urls():
    print("Paste one or more URLs separated by space or commas, then press Enter:")
    txt = input("> ").strip()
    if not txt:
        return []
    parts = re.split(r"[\s,]+", txt)
    return [normalize_url(p) for p in parts if p.strip()]

def main():
    args = parse_args()
    if args.urls:
        urls = [normalize_url(u) for u in args.urls if normalize_url(u)]
    else:
        urls = prompt_for_urls()

    if not urls:
        logger.error("No valid URLs provided. Exiting.")
        return 1

    for u in urls:
        logger.info("=" * 70)
        logger.info(f"Crawling start URL: {u}")
        res = crawl_domain(u, max_pages=args.max_pages, obey_robots=args.robots)
        if res:
            save_result_to_file(res, prefix="orca")
        else:
            logger.warning(f"No result for {u}")
    logger.info("All done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())