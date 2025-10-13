# fetch articles with complementary approach:
# 1) use newsdata.io api
# 2) run a google news search via playwright to gather additional links
# 3) for each url, extract an html snippet preserving tags (h1,h2,strong,em,p,ul/li)
# 4) return up to max_articles unique articles per query

import requests
from bs4 import BeautifulSoup
from src.utils import get_env_var, normalize_url, safe_truncate
from langdetect import detect
from playwright.sync_api import sync_playwright
import time
import tldextract
from urllib.parse import urljoin

NEWSDATA_API_KEY = get_env_var("NEWSDATA_API_KEY", "")
TARGET_LANGS = [l.strip() for l in get_env_var("LANGUAGES", "en").split(",")]
MAX_ART = int(get_env_var("MAX_ARTICLES_PER_QUERY", 10))

def _parse_api_results(api_json, max_articles):
    articles = []
    for item in api_json.get("results", [])[:max_articles]:
        headline = item.get("title", "") or item.get("title_no_format", "")
        description = item.get("description") or item.get("content") or ""
        url = item.get("link") or item.get("url")
        lang = item.get("language") or ""
        # sometimes description is short; keep it but scraper will supplement
        articles.append({"headline": headline, "snippet": description, "url": url, "lang": lang})
    return articles

def fetch_news_from_api(query, max_articles=MAX_ART):
    # newsdata.io endpoint
    try:
        params = {
            "apikey": NEWSDATA_API_KEY,
            "q": query,
            "language": ",".join(TARGET_LANGS),
            "page": 1
        }
        resp = requests.get("https://newsdata.io/api/1/news", params=params, timeout=20)
        if resp.status_code != 200:
            return []
        return _parse_api_results(resp.json(), max_articles)
    except Exception:
        return []

def _extract_main_html(url):
    # returns html-preserving snippet (h1,h2,strong,em,p,ul/li) and detected language
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            # some sites block headless user agents; set a common ua
            page.set_extra_http_headers({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"})
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            html = page.content()
            browser.close()
    except Exception:
        # fallback to requests
        try:
            headers = {"User-Agent":"Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=15, verify=True)
            html = r.text
        except Exception:
            return "", "en"
    soup = BeautifulSoup(html, "html.parser")
    # try metadata first
    meta_desc = soup.find("meta", {"property":"og:description"}) or soup.find("meta", {"name":"description"})
    if meta_desc and meta_desc.get("content"):
        candidate = meta_desc.get("content")
        try:
            lang = detect(candidate)
        except:
            lang = "en"
        # build small html
        return f"<p>{candidate}</p>", lang
    # otherwise gather structural tags
    parts = []
    for tag in soup.find_all(["h1","h2","strong","em","p","ul","li"]):
        # preserve only text and simple tags
        name = tag.name
        text = tag.get_text(separator=" ", strip=True)
        if not text:
            continue
        if name in ["h1","h2"]:
            parts.append(f"<{name}>{text}</{name}>")
        elif name in ["strong","em"]:
            parts.append(f"<{name}>{text}</{name}>")
        elif name == "p":
            parts.append(f"<p>{text}</p>")
        elif name in ["ul","li"]:
            parts.append(f"<li>{text}</li>")
        # stop if we collected enough
        if len(parts) >= 15:
            break
    html_snippet = "".join(parts)
    # detect language on the concatenated text
    try:
        lang = detect(BeautifulSoup(html_snippet, "html.parser").get_text())
    except:
        lang = "en"
    return safe_truncate(html_snippet, 8000), lang


def fetch_from_google_news(query, max_links=MAX_ART, resolve_targets=True, headless=True):
    links = []
    try:
        search_url = f"https://news.google.com/search?q={requests.utils.requote_uri(query)}"

        # use playwright for reliability
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=headless)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0"})
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # extract anchors inside article tags
            anchors = page.query_selector_all("article a")
            for a in anchors:
                href = a.get_attribute("href")
                if not href:
                    continue

                # google news often uses relative links (e.g., ./articles/...)
                if href.startswith("./"):
                    full = urljoin("https://news.google.com", href[1:])
                elif href.startswith("/"):
                    full = urljoin("https://news.google.com", href)
                else:
                    full = href

                links.append(full)
                if len(links) >= max_links:
                    break

            browser.close()

    except Exception as e:
        print(f"[warn] google news scraping failed for query '{query}': {e}")

        # fallback: try static html parse
        try:
            r = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select("article a[href]")[:max_links]:
                    href = a.get("href")
                    if href.startswith("./"):
                        full = urljoin("https://news.google.com", href[1:])
                    elif href.startswith("/"):
                        full = urljoin("https://news.google.com", href)
                    else:
                        full = href
                    links.append(full)
        except Exception as e2:
            print(f"[error] fallback failed: {e2}")

    # optional: convert Google News wrapper links into real publisher URLs.
    """
        FOR CONTEXT : 
        https://news.google.com/articles/... is a Google wrapper link, which redirects (or contains an anchor) to the actual publisher’s site (e.g., BBC, Reuters, etc.).
        so without resolving those wrappers, you’d only store https://news.google.com/articles/... - not the real news site.
        it runs only if resolve_targets=True
    """
    if resolve_targets:
        resolved = []
        for g_link in links:
            if "news.google.com" in g_link and ("/articles/" in g_link or "/article/" in g_link):
                try:
                    with sync_playwright() as p:
                        browser = p.firefox.launch(headless=headless)
                        page = browser.new_page()
                        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0"})
                        page.goto(g_link, wait_until="networkidle", timeout=20000)
                        anchors = page.query_selector_all("a") # scan all anchors (<a>) on that page
                        target = None
                        for a in anchors:
                            href = a.get_attribute("href")
                            if href and href.startswith("http") and "news.google.com" not in href:
                                target = href
                                break
                        browser.close()
                        resolved.append(target or g_link)
                except Exception:
                    resolved.append(g_link)
            else:
                resolved.append(g_link)
            if len(resolved) >= max_links:
                break
        return resolved

    return links


def gather_articles_for_query(query, max_articles=MAX_ART):
    # gather from api then complement with google news scraping and per-url extraction
    results = []
    urls_seen = set()
    # 1) api
    api_articles = fetch_news_from_api(query, max_articles=max_articles)
    for a in api_articles:
        url = a.get("url")
        if not url:
            continue
        norm = normalize_url(url)
        if norm in urls_seen:
            continue
        urls_seen.add(norm)
        # if snippet short, extract html
        snippet = a.get("snippet") or ""
        if not snippet or len(snippet) < 100:
            html_snip, lang = _extract_main_html(url)
            text_snip = BeautifulSoup(html_snip, "html.parser").get_text() if html_snip else ""
            results.append({
                "headline": a.get("headline",""),
                "snippet_html": html_snip,
                "snippet_text": text_snip,
                "url": url,
                "lang": a.get("lang") or lang
            })
        else:
            # keep both text and minimal html
            results.append({
                "headline": a.get("headline",""),
                "snippet_html": f"<p>{a.get('snippet')}</p>",
                "snippet_text": a.get("snippet"),
                "url": url,
                "lang": a.get("lang","en")
            })
        if len(results) >= max_articles:
            return results
    # 2) google news complement
    google_links = fetch_from_google_news(query, max_links=max_articles*2)
    for link in google_links:
        if len(results) >= max_articles:
            break
        # if google news internal link, we still try to open it and extract target
        html_snip, lang = _extract_main_html(link)
        text_snip = BeautifulSoup(html_snip, "html.parser").get_text() if html_snip else ""
        norm = normalize_url(link)
        if norm in urls_seen:
            continue
        urls_seen.add(norm)
        # sometimes the link is a google wrapper; keep it anyway
        results.append({
            "headline": "",  # unknown until we parse page
            "snippet_html": html_snip,
            "snippet_text": text_snip,
            "url": link,
            "lang": lang
        })
    return results