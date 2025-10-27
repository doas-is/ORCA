import requests
from bs4 import BeautifulSoup
from utils import get_env_var, normalize_url, safe_truncate
from langdetect import detect
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import concurrent.futures
import logging
import time
import tldextract
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== CONFIG ====
NEWSDATA_API_KEY = get_env_var("NEWSDATA_API_KEY", "")
TARGET_LANGS = [l.strip() for l in get_env_var("LANGUAGES", "en").split(",") if l.strip()]
MAX_ART = int(get_env_var("MAX_ARTICLES_PER_QUERY", 10))
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# ==== HELPERS ====
def _parse_api_results(api_json, max_articles):
    """Extract headline, snippet, URL, and language from NewsData API results."""
    articles = []
    for item in api_json.get("results", [])[:max_articles]:
        headline = item.get("title", "") or item.get("title_no_format", "")
        description = item.get("description") or item.get("content") or ""
        url = item.get("link") or item.get("url")
        lang = item.get("language") or "en"
        if not url:
            continue
        articles.append({
            "headline": headline.strip(),
            "snippet": description.strip(),
            "url": url.strip(),
            "lang": lang.strip()
        })
    return articles


def fetch_news_from_api(query, max_articles=MAX_ART):
    """Fetch recent articles using the NewsData.io API."""
    if not NEWSDATA_API_KEY:
        logger.warning("NEWSDATA_API_KEY not set; skipping API fetch.")
        return []

    try:
        params = {
            "apikey": NEWSDATA_API_KEY,
            "q": query,
            "language": ",".join(TARGET_LANGS) if TARGET_LANGS else None,
            "page": 1
        }
        resp = requests.get("https://newsdata.io/api/1/news", params=params, timeout=20)
        resp.raise_for_status()
        return _parse_api_results(resp.json(), max_articles)
    except Exception as e:
        logger.warning(f"fetch_news_from_api failed for query '{query}': {e}")
        return []


# ==== HTML EXTRACTION ====
def _extract_main_html(url, headless=True):
    """
    Returns (html_snippet_preserving_tags, detected_language).
    Extracts core HTML content while preserving structure.
    """
    html = None
    try:
        # Use Playwright for dynamic pages
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=headless)
            page = browser.new_page()
            page.set_extra_http_headers(HEADERS)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(0.3)
            html = page.content()
            browser.close()
    except Exception as e:
        logger.debug(f"Playwright fetch failed for {url}: {e}")

    if not html:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=True)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            logger.warning(f"Requests fallback failed for {url}: {e}")
            return "", "en"

    soup = BeautifulSoup(html, "html.parser")

    # Prefer meta description if available
    meta_desc = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
    if meta_desc and meta_desc.get("content"):
        content = meta_desc.get("content").strip()
        try:
            lang = detect(content) if len(content) > 20 else "en"
        except Exception:
            lang = "en"
        return safe_truncate(f"<p>{content}</p>", 8000), lang

    # Extract main tags
    parts, collected = [], 0
    for selector in ["h1", "h2", "p", "ul"]:
        for tag in soup.find_all(selector):
            if selector == "ul":
                lis = [li.get_text(" ", strip=True) for li in tag.find_all("li") if li.get_text(strip=True)]
                if lis:
                    parts.append(f"<ul>{''.join(f'<li>{t}</li>' for t in lis)}</ul>")
                    collected += 1
            else:
                txt = tag.get_text(" ", strip=True)
                if txt:
                    parts.append(f"<{selector}>{txt}</{selector}>")
                    collected += 1
            if collected >= 15:
                break
        if collected >= 15:
            break

    if collected < 15:
        for tag in soup.find_all(["strong", "em"]):
            txt = tag.get_text(" ", strip=True)
            if txt:
                parts.append(f"<{tag.name}>{txt}</{tag.name}>")
                collected += 1
            if collected >= 15:
                break

    html_snippet = "".join(parts)
    if not html_snippet:
        body_text = soup.get_text(" ", strip=True)
        html_snippet = f"<p>{body_text[:800]}</p>" if body_text else ""

    try:
        plain = BeautifulSoup(html_snippet, "html.parser").get_text(" ", strip=True)
        lang = detect(plain) if len(plain) > 20 else "en"
    except Exception:
        lang = "en"

    return safe_truncate(html_snippet, 8000), lang


# ==== GOOGLE NEWS SCRAPER ====
def fetch_from_google_news(query, max_links=MAX_ART, headless=True):
    """Fetch Google News result links."""
    links, seen = [], set()
    search_url = f"https://news.google.com/search?q={requests.utils.requote_uri(query)}"

    try:
        r = requests.get(search_url, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            anchors = soup.select("article a[href]")
            for a in anchors:
                href = a.get("href")
                if not href:
                    continue
                if href.startswith("./"):
                    href = urljoin("https://news.google.com", href[1:])
                elif href.startswith("/"):
                    href = urljoin("https://news.google.com", href)
                if href not in seen:
                    seen.add(href)
                    links.append(href)
                if len(links) >= max_links:
                    break
    except Exception as e:
        logger.warning(f"Google static fetch failed: {e}")

    if len(links) < max_links:
        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=headless)
                page = browser.new_page()
                page.set_extra_http_headers(HEADERS)
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(0.3)
                anchors = page.query_selector_all("article a")
                for a in anchors:
                    href = a.get_attribute("href")
                    if href and href not in seen:
                        if href.startswith("./"):
                            href = urljoin("https://news.google.com", href[1:])
                        elif href.startswith("/"):
                            href = urljoin("https://news.google.com", href)
                        seen.add(href)
                        links.append(href)
                        if len(links) >= max_links:
                            break
                browser.close()
        except Exception as e:
            logger.warning(f"Playwright Google News failed for '{query}': {e}")

    return links[:max_links]


# ==== MAIN FUNCTION ====
def gather_articles_for_query(query, max_articles=MAX_ART):
    """
    Gather articles from API and Google News, fetch HTML concurrently.
    Returns list of dicts with keys:
    headline, snippet_html, snippet_text, url, lang
    """
    results, urls_seen = [], set()
    api_articles = fetch_news_from_api(query, max_articles=max_articles)

    # === 1. Add API results ===
    for a in api_articles:
        url = a.get("url")
        if not url:
            continue
        norm = normalize_url(url) if callable(globals().get("normalize_url")) else url
        if norm in urls_seen:
            continue
        urls_seen.add(norm)
        snippet = a.get("snippet") or ""
        if len(snippet) < 100:
            html_snip, lang = _extract_main_html(url)
            text_snip = BeautifulSoup(html_snip, "html.parser").get_text() if html_snip else ""
        else:
            html_snip, lang, text_snip = f"<p>{snippet}</p>", a.get("lang", "en"), snippet

        results.append({
            "headline": a.get("headline", ""),
            "snippet_html": html_snip or "",
            "snippet_text": text_snip or "",
            "url": url,
            "lang": lang
        })
        if len(results) >= max_articles:
            return results

    # 2. Complement with Google News links
    google_links = fetch_from_google_news(query, max_links=max_articles * 2)

    # Fetch HTML concurrently
    def fetch_html(link):
        try:
            html_snip, lang = _extract_main_html(link)
            text_snip = BeautifulSoup(html_snip, "html.parser").get_text() if html_snip else ""
            return {
                "headline": "",
                "snippet_html": html_snip or "",
                "snippet_text": text_snip or "",
                "url": link,
                "lang": lang
            }
        except Exception as e:
            logger.warning(f"Failed to fetch HTML for {link}: {e}")
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_html, link) for link in google_links if normalize_url(link) not in urls_seen]
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            if res and res["url"] not in urls_seen:
                urls_seen.add(res["url"])
                results.append(res)
                if len(results) >= max_articles:
                    break

    return results[:max_articles]
