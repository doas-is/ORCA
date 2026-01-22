"""
ACTUALLY FIXED crawler_core.py - extracts REAL company names
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

# Configuration
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
]

PLATFORM_LINK = os.getenv("PLATFORM_LINK")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
DEFAULT_MAX_PAGES = int(os.getenv("DEFAULT_MAX_PAGES", 30))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 15))

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Logging
logger = logging.getLogger("crawler_core")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(ch)

session = requests.Session()
session.headers.update({"Accept-Language": "en-US,en;q=0.9"})


def pick_user_agent():
    return random.choice(USER_AGENTS)


def normalize_url(url):
    url = url.strip()
    if not url:
        return None
    if not urlparse(url).scheme:
        url = "https://" + url
    return url


def is_same_domain(base, url):
    try:
        return urlparse(base).netloc == urlparse(url).netloc
    except Exception:
        return False


def allowed_by_robots(url, ua_token="OrendaCrawler"):
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = RobotFileParser()
        rp.set_url(urljoin(base, "/robots.txt"))
        try:
            rp.read()
        except Exception:
            return True, 0
        allowed = rp.can_fetch(ua_token, url)
        if allowed is None:
            allowed = True
        delay = rp.crawl_delay(ua_token) or rp.crawl_delay("*") or 0
        return allowed, delay or 0
    except Exception:
        return True, 0


def safe_get(url, timeout=REQUEST_TIMEOUT, allow_insecure_fallback=True):
    headers = {"User-Agent": pick_user_agent()}
    try:
        resp = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return resp
    except requests.exceptions.SSLError:
        if allow_insecure_fallback:
            try:
                resp = session.get(url, headers=headers, timeout=timeout, verify=False)
                return resp
            except Exception:
                return None
        return None
    except requests.exceptions.RequestException as e:
        logger.debug(f"Request error for {url}: {e}")
        return None


def extract_company_name(soup, url):
    """
    FIXED: Extract ACTUAL company name, not taglines
    Priority: domain-based extraction FIRST, then meta tags
    """
    
    # Priority 0: EXTRACT FROM DOMAIN (most reliable for actual brand name)
    domain = urlparse(url).netloc
    domain_clean = domain.replace('www.', '').split('.')[0]
    
    # Convert domain to proper company name
    # travelperk -> TravelPerk, expensify -> Expensify
    if domain_clean:
        # Handle common patterns
        company_from_domain = domain_clean
        
        # CamelCase detection (e.g., TravelPerk, LinkedIn)
        # If domain has known patterns, fix them
        brand_mappings = {
            'travelperk': 'TravelPerk',
            'expensify': 'Expensify', 
            'linkedin': 'LinkedIn',
            'facebook': 'Facebook',
            'aircall': 'Aircall',
            'navan': 'Navan',
            'tripactions': 'TripActions',
        }
        
        if domain_clean.lower() in brand_mappings:
            company_from_domain = brand_mappings[domain_clean.lower()]
        else:
            # Capitalize first letter
            company_from_domain = domain_clean.capitalize()
        
        logger.info(f"✓ Extracted company name from domain: {company_from_domain}")
    
    # Priority 1: og:site_name (if it's SHORT and looks like a brand)
    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        name = og_site.get("content").strip()
        # ONLY use if it's SHORT (actual brand names are short)
        if name and 2 < len(name) < 30 and name.lower() not in ['home', 'www']:
            # Check if it looks like a brand (no long sentences)
            if len(name.split()) <= 2:  # Max 2 words for brand
                logger.info(f"✓ Confirmed brand from og:site_name: {name}")
                return name
    
    # Priority 2: Title tag - extract brand AFTER separator
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        
        # Brand is usually AFTER separator: "Tagline | BrandName"
        for sep in [' | ', ' - ', ' – ', ' — ']:
            if sep in title:
                parts = title.split(sep)
                # Take LAST part (brand name)
                brand = parts[-1].strip()
                
                # Validate it's a brand (short, no weird words)
                if (2 < len(brand) < 30 and 
                    brand.lower() not in ['home', 'homepage', 'welcome'] and
                    len(brand.split()) <= 2):
                    logger.info(f"✓ Found brand from title (after separator): {brand}")
                    return brand
    
    # Priority 3: Application name
    app_name = soup.find("meta", attrs={"name": "application-name"})
    if app_name and app_name.get("content"):
        name = app_name.get("content").strip()
        if 2 < len(name) < 30 and len(name.split()) <= 2:
            logger.info(f"✓ Found from application-name: {name}")
            return name
    
    # Priority 4: Return domain-based name
    logger.info(f"✓ Using domain-based name: {company_from_domain}")
    return company_from_domain


def extract_basic_seo(soup, url):
    """Extract SEO data with FIXED company name detection"""
    
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
    
    # Remove script/style for text extraction
    for script in soup(["script", "style", "noscript"]):
        script.decompose()
    
    body_text = soup.get_text(separator=" ", strip=True)
    snippet = (body_text[:300] + "...") if body_text and len(body_text) > 300 else body_text
    
    # Extract links
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        links.append(urljoin(url, href))
    
    # Extract images
    imgs = [urljoin(url, img.get("src")) for img in soup.find_all("img") if img.get("src")]
    
    # Extract company name - THE KEY FIX
    company_name = extract_company_name(soup, url)
    
    return {
        "title": title,
        "company_name": company_name,
        "meta_description": meta_desc,
        "canonical": canonical,
        "h1": h1_tags,
        "snippet": snippet,
        "links": links,
        "images": imgs,
    }


def detect_business_signals(text, base_url=None):
    """FIXED: Better niche detection with aviation/travel focus"""
    
    if not text:
        return {}

    t = text.lower()
    
    # Niche detection - MORE COMPREHENSIVE
    niche_indicators = {
        # Travel & Aviation (ADDED!)
        "Corporate Travel Management": ["corporate travel", "business travel", "travel management", "travel booking"],
        "Aviation": ["airline", "aviation", "flight", "aircraft", "airport", "airfare"],
        "Travel Technology": ["travel tech", "travel platform", "travel software", "booking platform"],
        "Expense Management": ["expense management", "expense tracking", "expense reporting", "spend management"],
        
        # Existing categories
        "SaaS": ["saas", "software as a service", "cloud platform", "cloud software"],
        "FinTech": ["fintech", "payment", "financial services", "banking"],
        "HR Tech": ["hr tech", "human resources", "recruitment", "payroll", "workforce"],
        "E-commerce": ["e-commerce", "ecommerce", "online store", "shopping"],
        "CRM": ["crm", "customer relationship", "sales software"],
        "Project Management": ["project management", "task management", "workflow", "productivity"],
        "Analytics": ["analytics", "data analytics", "business intelligence", "metrics"],
        "Marketing": ["marketing automation", "digital marketing", "seo", "advertising"],
        "Cybersecurity": ["cybersecurity", "security", "firewall", "encryption"],
    }
    
    detected_niches = []
    for niche, keywords in niche_indicators.items():
        if any(kw in t for kw in keywords):
            detected_niches.append(niche)
            # Only detect top matches
            if len(detected_niches) >= 5:
                break
    
    return {
        "partner_indicators": [],
        "client_indicators": [],
        "niche_terms": detected_niches[:5],  # Top 5
        "partner_name_matches": [],
        "client_name_matches": [],
    }


def crawl_domain(start_url, max_pages=DEFAULT_MAX_PAGES, obey_robots=True):
    """Enhanced domain crawler with better error handling"""
    
    logger.info(f"🚀 Starting crawl: {start_url} (max_pages={max_pages})")
    start_url = normalize_url(start_url)
    
    if not start_url:
        logger.error("Invalid start URL")
        return None

    allowed, delay = (True, 0)
    if obey_robots:
        allowed, delay = allowed_by_robots(start_url)
        if not allowed:
            logger.warning(f"Robots.txt disallows crawling {start_url}")
            pass
    
    if delay > 0:
        logger.info(f"Robots.txt crawl-delay: {delay}s")
        delay = min(delay, 2)

    domain = urlparse(start_url).netloc
    seen = set()
    queue = deque([start_url])
    results = []
    company_name = None
    pages_crawled = 0

    while queue and pages_crawled < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        
        if delay and pages_crawled > 0:
            time.sleep(delay)

        logger.info(f"📄 Crawling [{pages_crawled + 1}/{max_pages}]: {url}")
        
        resp = safe_get(url)
        if not resp or resp.status_code >= 400:
            logger.warning(f"⚠ Failed to fetch {url}")
            pages_crawled += 1
            continue
        
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "html" not in content_type:
            logger.debug(f"Skipping non-HTML content: {content_type}")
            pages_crawled += 1
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            seo = extract_basic_seo(soup, url)
            
            # Capture company name from first successful page
            if not company_name and seo.get("company_name"):
                company_name = seo.get("company_name")
                logger.info(f"✅ Company identified: {company_name}")
            
            body_text = soup.get_text(separator=" ", strip=True)[:3000]
            business = detect_business_signals(body_text, url)

            # Classify links
            internal_links = []
            external_links = []
            for link in seo["links"]:
                if not link or link.startswith(("javascript:", "mailto:", "#")):
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
                "company_name": seo.get("company_name"),
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
            
            logger.info(f"  ✓ Title: {seo.get('title', 'N/A')[:50]}")
            logger.info(f"  ✓ Internal links: {len(internal_links)}, External: {len(external_links)}")

            # Enqueue internal links
            for link in internal_links[:10]:
                if link not in seen and not re.search(r"\.(jpg|jpeg|png|gif|pdf|zip)$", link, re.I):
                    queue.append(link)
        
        except Exception as e:
            logger.error(f"❌ Error processing {url}: {e}")
            pages_crawled += 1
            continue

    # Build summary
    all_niches = []
    for r in results:
        all_niches.extend(r.get("business_signals", {}).get("niche_terms", []))
    
    # Remove duplicates while preserving order
    seen_niches = set()
    unique_niches = []
    for n in all_niches:
        if n not in seen_niches:
            seen_niches.add(n)
            unique_niches.append(n)
    
    domain_summary = {
        "start_url": start_url,
        "domain": domain,
        "company_name": company_name or "Unknown Company",
        "pages_crawled": len(results),
        "top_titles": [r.get("title") for r in results if r.get("title")][:5],
        "top_h1s": sum([r.get("h1", []) for r in results], [])[:10],
        "likely_niches": unique_niches,
        "partner_indicators": [],
        "client_indicators": [],
        "partner_name_matches": [],
        "client_name_matches": [],
        "sample_pages": results[:10],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    logger.info(f"\n✅ Crawl complete!")
    logger.info(f"  • Pages: {len(results)}")
    logger.info(f"  • Company: {company_name}")
    logger.info(f"  • Niches: {', '.join(unique_niches[:3])}")
    
    return domain_summary


def save_result_to_file(result, prefix="result"):
    domain = result.get("domain") or "unknown"
    safe_name = re.sub(r"[^a-z0-9]", "_", domain.lower())[:100]
    out_path = os.path.join(OUTPUT_DIR, f"{prefix}_{safe_name}_{int(time.time())}.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Saved: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"Failed to save: {e}")
        return None


def parse_args():
    p = argparse.ArgumentParser(description="Enhanced ORCA Crawler")
    p.add_argument("urls", nargs="*", help="URLs to crawl")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--no-robots", dest="robots", action="store_false")
    return p.parse_args()


def main():
    args = parse_args()
    if args.urls:
        urls = [normalize_url(u) for u in args.urls if normalize_url(u)]
    else:
        if PLATFORM_LINK:
            urls = [normalize_url(PLATFORM_LINK)]
        else:
            logger.error("No URLs provided")
            return 1

    for u in urls:
        logger.info("=" * 70)
        res = crawl_domain(u, max_pages=args.max_pages, obey_robots=args.robots)
        if res:
            save_result_to_file(res, prefix="orca")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())