# enhanced crawler_core with:
# - better ssl/tls handling (configurable)
# - rotating user-agents and optional proxy support
# - captcha/block detection and playwright fallback (screenshot + flag)
# - richer on-page seo extraction (schema.org, headings, alt counts, canonical, hreflang)
# - optional crawl4ai integration (hooked via env vars)
# - structured json output with crawl4ai snapshot if available


# pip install crawl4ai

import os
import re
import json
import time
import logging
import tempfile
import random
import ssl
from queue import Queue
from datetime import datetime
from urllib.parse import urljoin, urlparse
from collections import defaultdict, deque

import requests
import tldextract
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib import robotparser
import urllib3

# try to import playwright for headful/headless browser fallback
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

# optional pdf parsing
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("warning: pypdf not installed, pdf parsing disabled")

# load env
load_dotenv()

INPUT_SOURCE = os.getenv("INPUT_SOURCE")
INPUT_FILE_PATH = os.getenv("INPUT_FILE_PATH")

# default base user agent (used when rotation off or as fallback)
BASE_USER_AGENT = os.getenv("USER_AGENT", "mozilla/5.0 (windows nt 10.0; win64; x64) applewebkit/537.36 (khtml, like gecko) chrome/115.0 safari/537.36")

MAX_PAGES_PER_DOMAIN = int(os.getenv("MAX_PAGES_PER_DOMAIN"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # default 10mb

# security / network options
ALLOW_INSECURE_TLS = os.getenv("ALLOW_INSECURE_TLS").lower() == "true"  # allow fallback to verify=False on ssl errors
PROXIES = [p.strip() for p in os.getenv("PROXIES",).split(",") if p.strip()]
ROTATE_USER_AGENTS = os.getenv("ROTATE_USER_AGENTS").lower() == "true"
PLAYWRIGHT_ENABLED = os.getenv("PLAYWRIGHT_ENABLED").lower() == "true"
CRAWL4AI_API_URL = os.getenv("CRAWL4AI_API_URL")  # optional: supply your crawl4ai endpoint
CRAWL4AI_API_KEY = os.getenv("CRAWL4AI_API_KEY")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# setup logging
logger = logging.getLogger("crawler")
logger.setLevel(logging.INFO)
fh = logging.FileHandler(os.path.join(OUTPUT_DIR, "crawler.log"))
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(fh)
    logger.addHandler(ch)
else:
    # avoid duplicate handlers when reloading in notebooks
    logger.handlers = [fh, ch]
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

# quiet insecure warnings if fallback allowed (we'll disable later only if needed)
if ALLOW_INSECURE_TLS:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# requests session with retry & backoff
session = requests.Session()
session.headers.update({"User-Agent": BASE_USER_AGENT})
adapter = requests.adapters.HTTPAdapter(
    max_retries=requests.adapters.Retry(
        total=MAX_RETRIES,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"]
    )
)
session.mount("https://", adapter)
session.mount("http://", adapter)

# simple rate limiter per domain with jitter to look human-ish
class SimpleLimiter:
    def __init__(self, requests_per_second=1):
        self.rps = requests_per_second
        self.last_request = defaultdict(float)
    def wait(self, domain):
        elapsed = time.time() - self.last_request[domain]
        wait_time = max(0, (1.0 / self.rps) - elapsed)
        # add a small random jitter to mimic human behavior
        wait_time += random.uniform(0, 0.5)
        if wait_time > 0:
            time.sleep(wait_time)
        self.last_request[domain] = time.time()

limiter = SimpleLimiter(requests_per_second=1)

# file extensions we treat as downloadable
FILE_EXTENSIONS = {".pdf": "pdf", ".docx": "docx"}

def is_file_url(url):
    try:
        ext = os.path.splitext(urlparse(url).path.lower())[1]
        return ext in FILE_EXTENSIONS
    except Exception:
        return False

# user-agent rotation list (simple, can be extended)
COMMON_USER_AGENTS = [
    BASE_USER_AGENT,
    "mozilla/5.0 (macintosh; intel mac os x 10_15_7) applewebkit/605.1.15 (khtml, like gecko) version/14.0.3 safari/605.1.15",
    "mozilla/5.0 (x11; linux x86_64) applewebkit/537.36 (khtml, like gecko) chrome/115.0.0.0 safari/537.36",
    "mozilla/5.0 (iphone; cpu iphone os 14_0 like mac os x) applewebkit/605.1.15 (khtml, like gecko) version/14.0 mobile/15a372 safari/604.1"
]

# optional proxy deque for rotating proxies
proxy_deque = deque(PROXIES) if PROXIES else deque()

def pick_proxy():
    if not proxy_deque:
        return None
    # rotate
    proxy = proxy_deque[0]
    proxy_deque.rotate(-1)
    # support http(s) proxy format
    return {"http": proxy, "https": proxy}

def pick_user_agent():
    if ROTATE_USER_AGENTS and COMMON_USER_AGENTS:
        return random.choice(COMMON_USER_AGENTS)
    return BASE_USER_AGENT

# safe_get: robust HTTP get with user-agent rotation, proxy support, ssl fallback and detection of blocks
def safe_get(url, timeout=REQUEST_TIMEOUT, stream=False, allow_insecure_fallback=True):
    """
    robust get:
    - rotate user-agent if configured
    - rotate proxies if provided
    - attempt normal request, if ssl error and allowed, retry with verify=False
    - return requests.Response or None
    """
    headers = {"User-Agent": pick_user_agent()}
    proxies = pick_proxy()
    try:
        resp = session.get(url, headers=headers, timeout=timeout, stream=stream, proxies=proxies, verify=not ALLOW_INSECURE_TLS)
        resp.raise_for_status()
        return resp
    except requests.exceptions.SSLError as e:
        logger.warning(f"ssl error for {url}: {e}")
        if allow_insecure_fallback and ALLOW_INSECURE_TLS:
            logger.info(f"retrying {url} with verify=False (insecure mode enabled)")
            try:
                resp = session.get(url, headers=headers, timeout=timeout, stream=stream, proxies=proxies, verify=False)
                resp.raise_for_status()
                return resp
            except Exception as e2:
                logger.debug(f"insecure retry failed for {url}: {e2}")
                return None
        return None
    except requests.exceptions.RequestException as e:
        logger.debug(f"request exception for {url}: {e}")
        return None

def fetch_html(url, use_playwright_if_blocked=True):
    """
    fetch html content, prefer lightweight requests but fallback to playwright:
    - if initial request returns content that looks like a captcha/challenge, try playwright
    - if playwright not available or fails, return None
    """
    r = safe_get(url)
    if not r:
        # try playwright only if enabled and available
        if PLAYWRIGHT_ENABLED and PLAYWRIGHT_AVAILABLE:
            return _fetch_with_playwright(url)
        return None
    content_type = r.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return None
    text = r.text
    if looks_like_block_or_captcha(text) and use_playwright_if_blocked and PLAYWRIGHT_ENABLED and PLAYWRIGHT_AVAILABLE:
        # detected cloudflare/recaptcha style block, try playwright for a better render + screenshot
        logger.info(f"captcha/block suspected at {url}, attempting playwright render")
        return _fetch_with_playwright(url, screenshot_on_block=True, html_only=True)
    return text

def _fetch_with_playwright(url, screenshot_on_block=False, html_only=True):
    """
    playwright fallback:
    - launch a browser with realistic viewport and headers
    - do small human-like interactions (mousemove) to reduce detection
    - capture screenshot if a block/captcha is detected
    - return page content or None
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.debug("playwright not available, cannot perform browser fetch")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(user_agent=pick_user_agent(), viewport={"width": 1280, "height": 800})
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except PlaywrightTimeout:
                logger.debug(f"playwright timeout loading {url}")
            # small human-like mouse movement
            try:
                page.mouse.move(random.randint(100, 400), random.randint(100, 400), steps=3)
            except Exception:
                pass
            content = page.content()
            # detect block on rendered html
            if looks_like_block_or_captcha(content):
                logger.info(f"playwright render suggests a captcha or block at {url}")
                if screenshot_on_block:
                    try:
                        safe_name = re.sub(r'[^a-z0-9]', '_', url.lower())[:120]
                        screenshot_path = os.path.join(OUTPUT_DIR, f"block_{safe_name}_{int(time.time())}.png")
                        page.screenshot(path=screenshot_path, full_page=True)
                        logger.info(f"screenshot of block saved to {screenshot_path}")
                    except Exception as e:
                        logger.debug(f"could not save screenshot for {url}: {e}")
                browser.close()
                return None
            browser.close()
            return content
    except Exception as e:
        logger.debug(f"playwright fetch error for {url}: {e}")
        return None

def download_file(url):
    try:
        r = safe_get(url, timeout=REQUEST_TIMEOUT, stream=True)
        if not r:
            return None, None
        r.raise_for_status()
        content = b""
        for chunk in r.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_FILE_SIZE:
                return None, None
        return content, r.headers.get("Content-Type", "")
    except Exception as e:
        logger.debug(f"download error for {url}: {e}")
        return None, None

def extract_pdf_text(content_bytes):
    if not PDF_AVAILABLE:
        return ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content_bytes)
            tmp_path = tmp.name
        reader = PdfReader(tmp_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        os.remove(tmp_path)
        return text[:5000]
    except Exception as e:
        logger.debug(f"pdf extraction error: {e}")
        return ""

def normalize_url(href, base_url):
    try:
        href = href.strip().split("#")[0]
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:")):
            return None
        if href.startswith("http"):
            return href
        return urljoin(base_url, href)
    except Exception:
        return None

def allowed_by_robots(url):
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = robotparser.RobotFileParser()
        rp.set_url(urljoin(base, "/robots.txt"))
        rp.read()
        # check crawl delay for our user agent if present
        try:
            delay = rp.crawl_delay(BASE_USER_AGENT) or rp.crawl_delay("*") or 0
        except Exception:
            delay = 0
        return rp.can_fetch(BASE_USER_AGENT, url), delay
    except Exception as e:
        logger.debug(f"robots parse error: {e}")
        return True, 0

# helper to detect blocks/captcha content in html
BLOCK_PATTERNS = [
    r"captcha", r"cloudflare", r"verify you are human", r"are you human", r"please enable javascript",
    r"browser check", r"access denied", r"attention required"
]
def looks_like_block_or_captcha(html_text):
    if not html_text:
        return False
    t = html_text.lower()
    return any(p in t for p in ("captcha", "verify you're human", "are you human", "cloudflare", "access denied", 
                                "please enable javascript", "browser check", "spf-error"))




# --- link discovery & enhanced seo extraction ---

IMPORTANT_PATH_KEYWORDS = [
    "about", "a-propos", "qui-sommes-nous", "team", "equipe",
    "blog", "news", "actualites", "articles",
    "rse", "csr", "confidentialite", "privacy", "politique",
    "terms", "conditions", "mentions-legales", "rgpd",
    "pricing", "price", "product", "service", "features"
]

def discover_links_and_struct(html, base_url, domain):
    """
    returns internal links, external links, files, soup and
    a rich page-structure summary: headings, canonical, hreflang, schemas, images, alt counts
    """
    soup = BeautifulSoup(html, "html.parser")
    internal_links = set()
    external_links = set()
    file_links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = normalize_url(href, base_url)
        if not full_url:
            continue

        if is_file_url(full_url):
            file_links.add(full_url)
            continue

        try:
            url_domain = tldextract.extract(full_url).registered_domain
            if url_domain == domain:
                internal_links.add(full_url)
            else:
                external_links.add(full_url)
        except Exception:
            continue

    # gather headings
    headings = []
    for h in soup.find_all(re.compile("^h[1-6]$")):
        headings.append({"tag": h.name, "text": h.get_text(strip=True)})

    # canonical
    canonical_tag = soup.find("link", rel="canonical")
    canonical = canonical_tag["href"] if canonical_tag and canonical_tag.get("href") else None

    # hreflang
    hreflangs = []
    for tag in soup.find_all("link", rel="alternate"):
        if tag.get("hreflang") and tag.get("href"):
            hreflangs.append({"hreflang": tag.get("hreflang"), "href": tag.get("href")})

    # schema.org json-ld
    schemas = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.string or "{}")
            schemas.append(payload)
        except Exception:
            # ignore parse errors
            continue

    # images & alt count
    images = []
    missing_alt = 0
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        alt = img.get("alt") or ""
        images.append({"src": src, "alt": alt})
        if not alt.strip():
            missing_alt += 1

    # meta tags
    title = soup.title.get_text(strip=True) if soup.title else ""
    description = None
    meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"]

    # simple word count & text extraction
    for tag in soup(['script', 'style', 'noscript', 'svg', 'iframe']):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    word_count = len(text.split())

    # internal link prioritization
    prioritized = {u for u in internal_links if any(k in u.lower() for k in IMPORTANT_PATH_KEYWORDS)}
    internal_links = list(prioritized.union(internal_links))

    return list(internal_links), list(external_links), list(file_links), soup, {
        "headings": headings,
        "canonical": canonical,
        "hreflangs": hreflangs,
        "schemas": schemas,
        "images": images,
        "missing_alt_count": missing_alt,
        "title": title,
        "meta_description": description,
        "word_count": word_count
    }

def extract_metadata_from_soup(soup):
    """
    keep older metadata extractor but add language detection and social link heuristics
    """
    metadata = {
        "name": None,
        "description": None,
        "social": {},
        "language": None,
        "keywords_found": []
    }
    try:
        h1 = soup.find("h1")
        if h1:
            metadata["name"] = h1.get_text(strip=True)
        elif soup.title:
            metadata["name"] = soup.title.get_text(strip=True)

        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_desc and meta_desc.get("content"):
            metadata["description"] = meta_desc["content"]

        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata["language"] = html_tag.get("lang").split("-")[0].lower()

        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "linkedin.com" in href:
                metadata["social"].setdefault("linkedin", a["href"])
            elif "twitter.com" in href or "x.com" in href:
                metadata["social"].setdefault("twitter", a["href"])
            elif "facebook.com" in href:
                metadata["social"].setdefault("facebook", a["href"])
            elif "instagram.com" in href:
                metadata["social"].setdefault("instagram", a["href"])

        # small keyword list: you can extend with domain-specific lists later
        keywords = [
            "project", "projet", "partner", "partenaire", "collaboration", "collaborer",
            "award", "prix", "event", "événement", "conference", "conférence",
            "csr", "rse", "innovation", "impact", "durable", "pricing", "product", "service", "crm"
        ]
        text = soup.get_text(" ", strip=True).lower()
        found = [k for k in keywords if k in text]
        metadata["keywords_found"] = list(set(found))
    except Exception as e:
        logger.debug(f"metadata extraction error: {e}")
    return metadata

def parse_text_from_soup(soup, max_chars=2000):
    try:
        for tag in soup(['script', 'style', 'noscript', 'svg', 'iframe']):
            tag.decompose()
        text_parts = [
            tag.get_text(" ", strip=True)
            for tag in soup.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'div'])
        ]
        return " ".join(text_parts)[:max_chars]
    except Exception:
        return ""



# --- crawl4ai integration hook (for locally installes crawl4ai) ---
from crawl4ai import Crawl4AI, CrawlConfig

def call_crawl4ai_snapshot(domain: str):
    """ run crawl4ai locally to collect semantic and structural data from a domain.
        returns a dictionary ready to merge with crawler_core results."""
    try:
        config = CrawlConfig(
            max_depth=5,                
            max_pages=120, 
            render_js=True,   # enable js rendering when necessary
            obey_robots_txt=True,   # respect robots.txt
            allow_insecure=True,   # bypass ssl/tls errors if needed
            retry_failed=True,    # reattempt blocked requests
            timeout=60,
        )

        # initialize the local crawler
        crawler = Crawl4AI(config=config)
        # launch crawl
        snapshot = crawler.crawl(domain)

        print(f"[info] crawl4ai local snapshot generated for {domain}")

        # return structured dict
        return {
            "domain": domain,
            "pages_crawled": len(snapshot.pages),
            "meta_tags": snapshot.meta_tags,
            "headings": snapshot.headings,
            "keywords": snapshot.keywords,
            "schemas": snapshot.schemas,
            "internal_links": snapshot.internal_links,
            "external_links": snapshot.external_links,
            "raw_data": snapshot.to_dict()  # detailed crawl data
        }

    except Exception as e:
        print(f"[error] crawl4ai local crawl failed for {domain}: {e}")
        return None



# main crawling logic
def crawl_domain(start_url, max_pages=MAX_PAGES_PER_DOMAIN):
    """
        - respects robots.txt
        - uses safe_get / playwright fallback for captcha/blocks
        - extracts richer page-level seo info (schemas, headings, alt-text)
        - tries to use crawl4ai snapshot if configured
        - returns rich structured result ready for seo_analyzer.py
    """
    try:
        domain = tldextract.extract(start_url).registered_domain
        logger.info(f"starting crawl: {start_url} (domain: {domain})")

        allowed, delay = allowed_by_robots(start_url)
        if not allowed:
            logger.warning(f"blocked by robots.txt: {start_url}")
            return None
        logger.info(f"crawl delay suggested by robots: {delay}s")

        # optionally fetch a deep crawl snapshot from crawl4ai if configured
        crawl4ai_snapshot = call_crawl4ai_snapshot(domain)

        results = {
            "input_url": start_url,
            "domain": domain,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "company": {"name": None, "description": None, "services": [], "confidence": 0.5},
            "social": {},
            "external_sites": [],
            "sections": {"about": [], "blog": [], "policies": [], "other": []},
            "evidence": [],
            "files": [],
            "crawl_log": {"pages_crawled": 0, "errors": [], "max_pages": max_pages},
            "crawl4ai_snapshot": crawl4ai_snapshot  # may be None
        }

        seen_urls = set()
        url_queue = Queue()
        url_queue.put(start_url)
        pages_crawled = 0

        while not url_queue.empty() and pages_crawled < max_pages:
            current_url = url_queue.get()
            if current_url in seen_urls:
                continue
            seen_urls.add(current_url)

            try:
                limiter.wait(domain)
                if delay > 0:
                    time.sleep(delay)

                html = fetch_html(current_url)
                if not html:
                    # log and continue; playwright may have taken screenshot if blocked
                    results["crawl_log"]["errors"].append({"page": current_url, "error": "no html fetched / blocked or non-html"})
                    continue

                internal_links, external_links, file_links, soup, page_struct = discover_links_and_struct(html, current_url, domain)
                pages_crawled += 1
                results["crawl_log"]["pages_crawled"] = pages_crawled

                logger.info(f"crawled [{pages_crawled}/{max_pages}]: {current_url}")

                metadata = extract_metadata_from_soup(soup)
                if not results["company"]["name"] and metadata["name"]:
                    results["company"]["name"] = metadata["name"]
                if not results["company"]["description"] and metadata["description"]:
                    results["company"]["description"] = metadata["description"]
                results["social"].update(metadata["social"])

                text_snippet = parse_text_from_soup(soup, max_chars=1200)
                if text_snippet:
                    keywords = metadata["keywords_found"]
                    results["evidence"].append({
                        "page": current_url,
                        "snippet": text_snippet,
                        "keywords_found": keywords,
                        "page_struct": {
                            "title": page_struct.get("title"),
                            "meta_description": page_struct.get("meta_description"),
                            "word_count": page_struct.get("word_count"),
                            "missing_alt_count": page_struct.get("missing_alt_count"),
                            "headings": page_struct.get("headings")[:10]  # keep first 10 headings only
                        }
                    })

                # categorize section
                lower_url = current_url.lower()
                if any(k in lower_url for k in ["about", "a-propos", "team", "qui-sommes-nous", "equipe"]):
                    results["sections"]["about"].append(current_url)
                elif any(k in lower_url for k in ["blog", "news", "actualites", "articles", "updates"]):
                    results["sections"]["blog"].append(current_url)
                elif any(k in lower_url for k in ["privacy", "rse", "confidentialite", "policy", "rgpd", "mentions-legales", "terms", "conditions"]):
                    results["sections"]["policies"].append(current_url)
                else:
                    results["sections"]["other"].append(current_url)

                # add new internal links to queue
                for link in internal_links:
                    if link not in seen_urls and len(seen_urls) + url_queue.qsize() < max_pages * 3:
                        url_queue.put(link)

                # visit a sample of external links only from homepage (first page)
                if pages_crawled == 1:
                    for ext_link in external_links[:20]:
                        results["external_sites"].append(ext_link)
                        try:
                            logger.info(f"visiting external link: {ext_link}")
                            ext_html = fetch_html(ext_link)
                            if ext_html:
                                ext_soup = BeautifulSoup(ext_html, "html.parser")
                                ext_meta = extract_metadata_from_soup(ext_soup)
                                results["social"].update(ext_meta["social"])
                                if ext_meta["keywords_found"]:
                                    results["evidence"].append({
                                        "page": ext_link,
                                        "snippet": ext_meta.get("description") or "",
                                        "keywords_found": ext_meta.get("keywords_found")
                                    })
                        except Exception as e:
                            logger.debug(f"external link crawl error ({ext_link}): {e}")

                # download files
                for file_url in file_links:
                    if len(results["files"]) >= 10:
                        break
                    content, content_type = download_file(file_url)
                    if content:
                        text = extract_pdf_text(content)
                        results["files"].append({
                            "url": file_url,
                            "content_type": content_type,
                            "text_snippet": text[:2000] if text else ""
                        })

            except Exception as e:
                logger.error(f"error crawling {current_url}: {e}")
                results["crawl_log"]["errors"].append({"page": current_url, "error": str(e)})

        # basic confidence scoring
        confidence = 0.5
        if pages_crawled > 0:
            confidence += min(0.3, (pages_crawled / max_pages) * 0.3)
        if results["company"]["name"]:
            confidence += 0.1
        if results["company"]["description"]:
            confidence += 0.1
        results["company"]["confidence"] = round(confidence, 2)

        logger.info(f"crawl complete: {domain} - {pages_crawled} pages")
        return results
    except Exception as e:
        logger.exception(f"fatal error crawling {start_url}")
        return None

# --- save results ---
def save_result_to_file(result):
    if not result:
        return None
    try:
        domain = result["domain"].replace(".", "_")
        timestamp = int(time.time())
        filename = f"{domain}_crawl_{timestamp}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"saved result to: {filepath}")
        return filepath
    except Exception as e:
        logger.exception(f"error saving result: {e}")
        return None

# --- input helpers ---
def get_input_urls_from_file(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return [d["url"] if isinstance(d, dict) and "url" in d else d for d in data]
            except json.JSONDecodeError:
                f.seek(0)
                return [line.strip() for line in f if line.strip()]
    except Exception:
        return []

def get_input_urls_manual():
    urls = input("\nenter one or more urls (comma-separated): ").strip()
    return [u.strip() for u in urls.split(",") if u.strip()]

# --- main ---
def main():
    logger.info("=" * 60)
    logger.info("🕷️ Website crawler started ...")
    logger.info(f"playwright enabled: {PLAYWRIGHT_ENABLED and PLAYWRIGHT_AVAILABLE}")
    logger.info("=" * 60)

    urls = []
    # ====================================================================================
    # we gotta specify the input type before running the crawler
    # ====================================================================================
    if INPUT_SOURCE == "manual": 
        urls = get_input_urls_manual()
    elif INPUT_SOURCE == "file":
        urls = get_input_urls_from_file(INPUT_FILE_PATH)
    else:
        logger.error("invalid INPUT_SOURCE. use 'manual' or 'file'.")
        return

    if not urls:
        logger.warning("no urls to crawl. exiting.")
        return

    for i, url in enumerate(urls, 1):
        logger.info(f"\n--- crawling {i}/{len(urls)}: {url} ---")
        result = crawl_domain(url)
        if result:
            save_result_to_file(result)

    logger.info("=" * 60)
    logger.info("crawl finished.")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()