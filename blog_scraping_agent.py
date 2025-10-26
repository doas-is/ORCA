"""
blog_crawler_v3.py
Fetch up to 15 latest blog articles (by placement order), summarize each (~200–300 words),
and save a detailed JSON report enriched with strategic fields.
"""

import os, sys, re, json, argparse
from urllib.parse import urljoin, urlparse
from datetime import datetime
from collections import Counter
import requests
from bs4 import BeautifulSoup
from readability import Document
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from dotenv import load_dotenv


load_dotenv()
HEADERS = {"User-Agent": "blog-crawler-agent/1.2"}
BLOG_KEYWORDS = ["blog","news","insights","articles","stories","press","updates","resources","actualites","research"]

# --------------------- NLTK SETUP ---------------------
for pkg in ["punkt", "punkt_tab", "stopwords"]:
    try:
        nltk.data.find(f"tokenizers/{pkg}" if "punkt" in pkg else f"corpora/{pkg}")
    except LookupError:
        nltk.download(pkg)
STOPWORDS = set(stopwords.words("english"))

# --------------------- NETWORK HELPERS ---------------------
def fetch(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text

def fetch_head(url, timeout=8):
    try:
        return requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    except Exception:
        return None

def normalize_href(href, base):
    return urljoin(base, href.split('#')[0])

def normalize_canonical(url):
    """Normalize URL for deduplication"""
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    norm = clean.geturl()
    if norm.endswith("/"):
        norm = norm.rstrip("/")
    return norm.lower()

# --------------------- DISCOVERY ---------------------
def discover_blog_url(start_url):
    base = start_url if start_url.endswith("/") else start_url + "/"
    try:
        html = fetch(base)
    except Exception as e:
        print("[discover] fetch failed:", e)
        return None
    soup = BeautifulSoup(html, "lxml")
    anchors = soup.find_all("a", href=True)
    candidates = []
    seen = set()
    for a in anchors:
        href = a['href'].strip()
        if href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        full = normalize_href(href, base)
        if full in seen: continue
        seen.add(full)
        txt = (a.get_text(" ", strip=True) or "").lower()
        score = 0
        for kw in BLOG_KEYWORDS:
            if kw in txt: score += 10
            if kw in href.lower() or kw in full.lower(): score += 6
        if score > 0:
            candidates.append((score, full, txt))
    candidates.sort(reverse=True, key=lambda x: x[0])
    for score, url, txt in candidates:
        if urlparse(url).netloc == urlparse(base).netloc:
            print(f"[discover] chosen: {url}")
            return url
    # fallback common path
    for path in ["/blog","/news","/insights","/articles"]:
        candidate = urljoin(base, path)
        rh = fetch_head(candidate)
        if rh and rh.status_code == 200:
            print("[discover] probe ok:", candidate)
            return candidate
    print("[discover] no blog found")
    return None

# --------------------- ARTICLE LISTING EXTRACTION ---------------------
def extract_article_links_from_listing(html, base_url, limit=200):
    soup = BeautifulSoup(html, "lxml")
    anchors = soup.find_all("a", href=True)
    parsed_base = urlparse(base_url)
    links = []
    seen = set()
    for a in anchors:
        href = a['href'].strip()
        if href.startswith("mailto:") or href.startswith("javascript:"): continue
        full = normalize_href(href, base_url)
        parsed = urlparse(full)
        if parsed.netloc != parsed_base.netloc: continue
        text = (a.get_text(" ", strip=True) or "").lower()
        path = parsed.path.lower()
        if any(kw in text or kw in path for kw in BLOG_KEYWORDS) or a.find_parent("article"):
            canon = normalize_canonical(full)
            if canon not in seen:
                seen.add(canon)
                links.append(full)
    return links[:limit]

# --------------------- CONTENT EXTRACTOR ---------------------
def clean_text(html_snippet):
    s = BeautifulSoup(html_snippet, "lxml").get_text(" ", strip=True)
    return " ".join(s.split())

def read_article_deep(url):
    try:
        html = fetch(url)
    except Exception as e:
        print("[read_article] fetch failed:", url, e)
        return None
    doc = Document(html)
    return clean_text(doc.summary())

# --------------------- META EXTRACTION ---------------------
def extract_meta(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    meta = {}
    meta["title"] = soup.title.string.strip() if soup.title and soup.title.string else ""
    desc = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", property="og:description")
    meta["description"] = desc.get("content","").strip() if desc else ""
    h1 = soup.find("h1")
    meta["h1"] = h1.get_text(" ",strip=True) if h1 else ""
    t = soup.find("time")
    meta["time"] = t.get("datetime", "").strip() if t else ""
    return meta

# --------------------- STRATEGIC EXTRACTORS (ADD-ON) ---------------------
def extract_headings(html):
    """Extract all H2 and H3 headings from an article"""
    soup = BeautifulSoup(html, "lxml")
    headings = []
    for tag in soup.find_all(["h2", "h3"]):
        txt = tag.get_text(" ", strip=True)
        if len(txt) > 2:
            headings.append(txt)
    return headings

def extract_external_links(html, base_url):
    """Extract all external links from article"""
    soup = BeautifulSoup(html, "lxml")
    parsed_base = urlparse(base_url)
    links = []
    for a in soup.find_all("a", href=True):
        href = normalize_href(a["href"], base_url)
        if href and urlparse(href).netloc != parsed_base.netloc:
            links.append(href)
    return list(set(links))

def infer_article_type(text, headings):
    """Infer article niche or focus type based on text & headings"""
    txt = text.lower() + " " + " ".join(headings).lower()
    if any(w in txt for w in ["case study", "client", "project", "résultat", "success story"]):
        return "case_study"
    if any(w in txt for w in ["guide", "how to", "tutorial", "tips", "best practice"]):
        return "guide_or_tutorial"
    if any(w in txt for w in ["annonce", "partenariat", "partnership", "collaboration", "event"]):
        return "news_or_collaboration"
    if any(w in txt for w in ["seo", "sem", "google", "ranking", "search engine", "copywriting"]):
        return "seo_focus"
    if any(w in txt for w in ["web", "frontend", "development", "api", "framework", "ai", "machine learning", "cloud", "cyber security", "fintech", "solutions", "deep learning", "tech"]):
        return "technical_article"
    return "general_marketing"

def extract_technical_keywords(text, top_n=10):
    """Find most domain-related terms via simple frequency"""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    words = [w for w in words if w not in STOPWORDS]
    tech_terms = [w for w in words if not re.match(r"^(les|des|une|notre|pour|avec|dans|est|and|the)$", w)]
    freq = Counter(tech_terms)
    return [w for w, _ in freq.most_common(top_n)]

def extract_smart_keywords(all_texts, top_n=12):
    vect = TfidfVectorizer(stop_words="english",
                           ngram_range=(1, 2),
                           max_features=5000)
    X = vect.fit_transform(all_texts)
    feature_names = vect.get_feature_names_out()
    keywords = []
    for i in range(X.shape[0]):
        row = X[i].toarray().ravel()
        idx = row.argsort()[::-1][:top_n]
        keywords.append([feature_names[j] for j in idx])
    return keywords

# SUMMARIZER 
def summarize_text(text, min_words=200):
    sents = sent_tokenize(text)
    if not sents: return ""
    if len(text.split()) <= min_words:
        return text
    vect = TfidfVectorizer(stop_words="english")
    X = vect.fit_transform(sents)
    scores = X.sum(axis=1).A1
    idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    selected, words = [], 0
    for i in idxs:
        selected.append(sents[i])
        words += len(sents[i].split())
        if words >= min_words:
            break
    selected = sorted(set(selected), key=lambda s: sents.index(s))
    return " ".join(selected)

# PIPELINE 
def run_pipeline(start_url, max_articles=15):
    print("[run] start:", start_url)
    blog_url = discover_blog_url(start_url) or urljoin(start_url, "/blog")
    print("[run] blog url:", blog_url)
    try:
        listing_html = fetch(blog_url)
    except Exception as e:
        print("[run] failed fetching listing:", e)
        return None

    candidates = extract_article_links_from_listing(listing_html, blog_url, limit=300)
    seen = set(); ordered = []
    for u in candidates:
        canon = normalize_canonical(u)
        if canon not in seen:
            seen.add(canon)
            ordered.append(u)
    candidates = ordered

    # JS-rendered fallback
    if len(candidates) < 5:
        print("[run] too few candidates; trying sitemap fallback...")
        for s in [urljoin(blog_url, "sitemap.xml"),
                  f"{urlparse(blog_url).scheme}://{urlparse(blog_url).netloc}/sitemap.xml"]:
            try:
                txt = fetch(s, timeout=8)
                locs = re.findall(r"<loc>([^<]+)</loc>", txt, flags=re.IGNORECASE)
                matches = [loc for loc in locs if any(kw in loc.lower() for kw in BLOG_KEYWORDS)]
                for m in matches:
                    canon = normalize_canonical(m)
                    if canon not in seen:
                        candidates.append(m)
                        seen.add(canon)
                    if len(candidates) >= 50:
                        break
            except Exception:
                continue

    print(f"[debug] {len(candidates)} candidate URLs found")
    print("[debug] sample URLs:", candidates[:10])

    articles = []
    for url in candidates:
        if len(articles) >= max_articles:
            break
        try:
            text = read_article_deep(url)
            if not text or len(text.split()) < 120:
                continue
            html = fetch(url)
            meta = extract_meta(html, url)
            summary = summarize_text(text)
            headings = extract_headings(html)
            ext_links = extract_external_links(html, url)
            article_type = infer_article_type(text, headings)
            technical_terms = extract_technical_keywords(text)
            smart_terms = extract_smart_keywords(text)

            articles.append({
                "title": meta["title"] or meta["h1"] or url.split("/")[-1],
                "url": url,
                "summary": summary,
                "word_count": len(text.split()),
                "meta_description": meta["description"],
                "published": meta["time"],
                "headings": headings,
                "article_type": article_type,
                "technical_keywords": technical_terms + smart_terms,
                "external_links": ext_links
            })
            print("[run] collected:", articles[-1]["title"])
        except Exception as e:
            print("[run] failed processing", url, e)

    return {
        "start_url": start_url,
        "blog_url": blog_url,
        "collected_at": datetime.utcnow().isoformat()+"Z",
        "articles_analyzed": len(articles),
        "articles": articles
    }

# --------------------- CLI ---------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform-link", default=None)
    parser.add_argument("--max-articles", type=int, default=15)
    args = parser.parse_args()
    start = args.platform_link or os.getenv("PLATFORM_LINK")
    if not start:
        print("Missing start URL (use --platform-link or .env)")
        sys.exit(1)
    result = run_pipeline(start, max_articles=args.max_articles)
    os.makedirs("outputs", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = f"./outputs/blog_crawler_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("✅ Saved:", out_path)

if __name__ == "__main__":
    main()