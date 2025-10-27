"""
Multi-API SEO Analyzer
Integrates 5 different SEO APIs for comprehensive website analysis:
1. Website Analyzer - Technical SEO audit
2. Keyword Finder - Keyword research and opportunities
3. On-Page SEO - Content and meta analysis
4. Referral Domain Finder - Backlink sources
5. New Backlinks Finder - Recent backlink activity
"""
import os
import json
import time
from datetime import datetime
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# API Configuration
SEO_WEBSITE_ANALYSER_API_KEY = os.getenv("SEO_WEBSITE_ANALYSER_API_KEY")
SEO_WEBSITE_ANALYSER_API_HOST = os.getenv("SEO_WEBSITE_ANALYSER_API_HOST")
KEYWORD_FINDER_API_URL = os.getenv("KEYWORD_FINDER_API_URL")
ONPAGE_SEO_URL = os.getenv("ONPAGE_SEO_URL")
REFERRAL_DOMAIN_FINDER_URL = os.getenv("REFERRAL_DOMAIN_FINDER_URL")
NEW_BACKLINKS_FINDER_URL = os.getenv("NEW_BACKLINKS_FINDER_URL")
SEO_ANALYZER_API_URL = os.getenv("SEO_ANALYZER_API_URL")
SEO_ANALYZER_API_KEY = os.getenv("SEO_ANALYZER_API_KEY")
SEO_ANALYZER_API_HOST = os.getenv("SEO_ANALYZER_API_HOST")

# Domain list and output
SEO_ANALYSIS_LINKS = os.getenv("SEO_ANALYSIS_LINKS")
OUTPUT_FILE = os.getenv("OUTPUT_SEO_FILE", "outputs/seo_analysis.json")

# Debug mode
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

def log(message, level="INFO"):
    """Enhanced logging"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def current_timestamp():
    return datetime.utcnow().isoformat()

def clean_domain(url):
    """Extract clean domain from URL"""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    return domain.replace("www.", "")

def save_json(data, path):
    """Save dictionary to JSON"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        log(f"Successfully saved to {path}")
        return True
    except Exception as e:
        log(f"Failed to save JSON: {e}", "ERROR")
        return False

def load_existing_json(path):
    """Load existing JSON or create empty structure"""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Failed to load existing JSON: {e}", "WARN")
    return {"timestamp": current_timestamp(), "domains_analyzed": []}


# API 1: Website Analyzer - Technical SEO Audit
def call_website_analyzer(domain):
    """
    Technical SEO audit - analyzes site structure, meta tags, speed, etc.
    Usually endpoint format: GET /analyze or /audit
    Common params: url, domain
    """
    if not SEO_WEBSITE_ANALYSER_API_HOST:
        log("Website Analyzer API URL not configured", "WARN")
        return {}
    
    clean_url = domain if domain.startswith("http") else f"https://{domain}"
    
    possible_endpoints = [
        f"{SEO_WEBSITE_ANALYSER_API_HOST}/analyze",
        f"{SEO_WEBSITE_ANALYSER_API_HOST}/audit",
        f"{SEO_WEBSITE_ANALYSER_API_HOST}/seo-audit",
        SEO_WEBSITE_ANALYSER_API_HOST,
    ]
    
    headers = {
        "x-rapidapi-key": SEO_WEBSITE_ANALYSER_API_KEY,
        "x-rapidapi-host": SEO_WEBSITE_ANALYSER_API_HOST.replace("https://", "").replace("http://", "").split("/")[0]
    }
    
    param_combinations = [
        {"url": clean_url},
        {"domain": clean_domain(domain)},
        {"website": clean_url},
        {"site": clean_url}
    ]
    
    for endpoint in possible_endpoints:
        for params in param_combinations:
            try:
                log(f"Trying Website Analyzer: {endpoint} with params {list(params.keys())}")
                r = requests.get(endpoint, headers=headers, params=params, timeout=30)
                
                if r.status_code == 429:
                    log("Rate limit exceeded, waiting 60 seconds...", "WARN")
                    time.sleep(60)
                    r = requests.get(endpoint, headers=headers, params=params, timeout=30)
                
                if DEBUG:
                    log(f"Status: {r.status_code}, Response preview: {r.text[:200]}")
                
                if r.status_code == 200:
                    data = r.json()
                    if data and (isinstance(data, dict) or isinstance(data, list)):
                        log("✓ Website Analyzer API successful")
                        return data
            except Exception as e:
                if DEBUG:
                    log(f"Attempt failed: {e}", "DEBUG")
                continue
    
    log("Website Analyzer API failed all attempts", "ERROR")
    return {}



# API 2: Keyword Finder - Keyword Research
def call_keyword_finder(domain, seed_keyword=""):
    """
    Keyword research - finds related keywords, search volume, competition
    Common params: keyword, domain, location, language
    """
    if not KEYWORD_FINDER_API_URL:
        log("Keyword Finder API URL not configured", "WARN")
        return {}
    
    if not seed_keyword:
        seed_keyword = clean_domain(domain).split(".")[0]
    
    headers = {
        "x-rapidapi-key": SEO_WEBSITE_ANALYSER_API_KEY,
        "x-rapidapi-host": KEYWORD_FINDER_API_URL.replace("https://", "").replace("http://", "").split("/")[0]
    }
    
    param_combinations = [
        {"keyword": seed_keyword, "domain": clean_domain(domain)},
        {"q": seed_keyword, "site": domain},
        {"keyword": seed_keyword},
        {"query": seed_keyword, "url": domain}
    ]
    
    for params in param_combinations:
        try:
            log(f"Trying Keyword Finder with params: {list(params.keys())}")
            r = requests.get(KEYWORD_FINDER_API_URL, headers=headers, params=params, timeout=30)
            
            if r.status_code == 429:
                log("Rate limit exceeded, waiting 60 seconds...", "WARN")
                time.sleep(60)
                r = requests.get(KEYWORD_FINDER_API_URL, headers=headers, params=params, timeout=30)
            
            if DEBUG:
                log(f"Status: {r.status_code}, Response preview: {r.text[:200]}")
            
            if r.status_code == 200:
                data = r.json()
                if data:
                    log("✓ Keyword Finder API successful")
                    return data
        except Exception as e:
            if DEBUG:
                log(f"Attempt failed: {e}", "DEBUG")
            continue
    
    log("Keyword Finder API failed all attempts", "WARN")
    return {}


# API 3: On-Page SEO - Content Analysis
def call_onpage_seo(domain):
    """
    On-page SEO analysis - title, meta, headings, content quality
    Common params: url, page, website
    """
    if not ONPAGE_SEO_URL:
        log("On-Page SEO API URL not configured", "WARN")
        return {}
    
    clean_url = domain if domain.startswith("http") else f"https://{domain}"
    
    headers = {
        "x-rapidapi-key": SEO_WEBSITE_ANALYSER_API_KEY,
        "x-rapidapi-host": ONPAGE_SEO_URL.replace("https://", "").replace("http://", "").split("/")[0]
    }
    
    param_combinations = [
        {"url": clean_url},
        {"page": clean_url},
        {"website": clean_url},
        {"domain": clean_domain(domain)}
    ]
    
    for params in param_combinations:
        try:
            log(f"Trying On-Page SEO with params: {list(params.keys())}")
            r = requests.get(ONPAGE_SEO_URL, headers=headers, params=params, timeout=30)
            
            if r.status_code == 429:
                log("Rate limit exceeded, waiting 60 seconds...", "WARN")
                time.sleep(60)
                r = requests.get(ONPAGE_SEO_URL, headers=headers, params=params, timeout=30)
            
            if DEBUG:
                log(f"Status: {r.status_code}, Response preview: {r.text[:200]}")
            
            if r.status_code == 200:
                data = r.json()
                if data:
                    log("✓ On-Page SEO API successful")
                    return data
        except Exception as e:
            if DEBUG:
                log(f"Attempt failed: {e}", "DEBUG")
            continue
    
    log("On-Page SEO API failed all attempts", "WARN")
    return {}



# API 4: Referral Domain Finder - Backlink Sources
def call_referral_domain_finder(domain):
    """
    Find referring domains - discovers websites linking to your site
    Common params: domain, url, target
    """
    if not REFERRAL_DOMAIN_FINDER_URL:
        log("Referral Domain Finder API URL not configured", "WARN")
        return {}
    
    target_domain = clean_domain(domain)
    
    headers = {
        "x-rapidapi-key": SEO_WEBSITE_ANALYSER_API_KEY,
        "x-rapidapi-host": REFERRAL_DOMAIN_FINDER_URL.replace("https://", "").replace("http://", "").split("/")[0]
    }
    
    param_combinations = [
        {"domain": target_domain},
        {"target": target_domain},
        {"url": domain},
        {"website": target_domain}
    ]
    
    for params in param_combinations:
        try:
            log(f"Trying Referral Domain Finder with params: {list(params.keys())}")
            r = requests.get(REFERRAL_DOMAIN_FINDER_URL, headers=headers, params=params, timeout=30)
            
            if r.status_code == 429:
                log("Rate limit exceeded, waiting 60 seconds...", "WARN")
                time.sleep(60)
                r = requests.get(REFERRAL_DOMAIN_FINDER_URL, headers=headers, params=params, timeout=30)
            
            if DEBUG:
                log(f"Status: {r.status_code}, Response preview: {r.text[:200]}")
            
            if r.status_code == 200:
                data = r.json()
                if data:
                    log("✓ Referral Domain Finder API successful")
                    return data
        except Exception as e:
            if DEBUG:
                log(f"Attempt failed: {e}", "DEBUG")
            continue
    
    log("Referral Domain Finder API failed all attempts", "WARN")
    return {}



# API 5: New Backlinks Finder - Recent Backlinks
def call_new_backlinks_finder(domain):
    """
    Find new/recent backlinks - tracks newly acquired backlinks
    Common params: domain, url, target, days
    """
    if not NEW_BACKLINKS_FINDER_URL:
        log("New Backlinks Finder API URL not configured", "WARN")
        return {}
    
    target_domain = clean_domain(domain)
    
    headers = {
        "x-rapidapi-key": SEO_WEBSITE_ANALYSER_API_KEY,
        "x-rapidapi-host": NEW_BACKLINKS_FINDER_URL.replace("https://", "").replace("http://", "").split("/")[0]
    }
    
    param_combinations = [
        {"domain": target_domain, "days": 30},
        {"target": target_domain},
        {"url": domain, "period": "30d"},
        {"website": target_domain}
    ]
    
    for params in param_combinations:
        try:
            log(f"Trying New Backlinks Finder with params: {list(params.keys())}")
            r = requests.get(NEW_BACKLINKS_FINDER_URL, headers=headers, params=params, timeout=30)
            
            if r.status_code == 429:
                log("Rate limit exceeded, waiting 60 seconds...", "WARN")
                time.sleep(60)
                r = requests.get(NEW_BACKLINKS_FINDER_URL, headers=headers, params=params, timeout=30)
            
            if DEBUG:
                log(f"Status: {r.status_code}, Response preview: {r.text[:200]}")
            
            if r.status_code == 200:
                data = r.json()
                if data:
                    log("✓ New Backlinks Finder API successful")
                    return data
        except Exception as e:
            if DEBUG:
                log(f"Attempt failed: {e}", "DEBUG")
            continue
    
    log("New Backlinks Finder API failed all attempts", "WARN")
    return {}



# Data analysis
def parse_website_analyzer_data(data):
    """Extract metrics from website analyzer response"""
    metrics = {
        "overall_score": 0,
        "page_speed": 0,
        "mobile_friendly": True,
        "https_enabled": False,
        "title": "",
        "description": "",
        "h1_count": 0,
        "meta_tags": []
    }
    
    try:
        if isinstance(data, dict):
            metrics["overall_score"] = data.get("score") or data.get("seo_score") or data.get("overall_score") or 0
            metrics["page_speed"] = data.get("speed") or data.get("page_speed") or data.get("performance") or 0
            metrics["mobile_friendly"] = data.get("mobile_friendly") or data.get("mobile") or True
            metrics["https_enabled"] = data.get("https") or data.get("ssl") or False
            metrics["title"] = data.get("title") or data.get("page_title") or ""
            metrics["description"] = data.get("description") or data.get("meta_description") or ""
            
            if "h1" in data:
                metrics["h1_count"] = len(data["h1"]) if isinstance(data["h1"], list) else 1
            
            log(f"Extracted metrics: Score={metrics['overall_score']}, Speed={metrics['page_speed']}")
    except Exception as e:
        log(f"Error parsing website analyzer data: {e}", "ERROR")
    
    return metrics

def parse_keyword_data(data):
    """Extract keyword opportunities"""
    keywords = {
        "total_keywords": 0,
        "high_value_keywords": [],
        "keyword_density": {},
        "suggested_keywords": []
    }
    
    try:
        if isinstance(data, dict):
            keyword_list = data.get("keywords") or data.get("data") or data.get("results") or []
            
            if isinstance(keyword_list, list):
                keywords["total_keywords"] = len(keyword_list)
                
                for kw in keyword_list[:10]:  # Top 10
                    if isinstance(kw, dict):
                        keyword_info = {
                            "keyword": kw.get("keyword") or kw.get("term") or "",
                            "volume": kw.get("volume") or kw.get("search_volume") or kw.get("searchVolume") or 0,
                            "difficulty": kw.get("difficulty") or kw.get("kd") or kw.get("rankingDifficulty") or 0,
                            "cpc": kw.get("cpc") or kw.get("broadCostPerClick") or kw.get("phraseCostPerClick") or kw.get("exactCostPerClick") or 0
                        }
                        
                        # Flag high-value keywords (high volume, low difficulty)
                        if keyword_info["volume"] > 1000 and keyword_info["difficulty"] < 30:
                            keywords["high_value_keywords"].append(keyword_info)
                        
                        keywords["suggested_keywords"].append(keyword_info)
            
            log(f"Found {keywords['total_keywords']} keywords, {len(keywords['high_value_keywords'])} high-value")
    except Exception as e:
        log(f"Error parsing keyword data: {e}", "ERROR")
    
    return keywords

def parse_backlink_data(referral_data, new_backlinks_data):
    """Combine and parse backlink information"""
    backlinks = {
        "total_referring_domains": 0,
        "new_backlinks_count": 0,
        "top_referring_domains": [],
        "recent_backlinks": [],
        "domain_authority_avg": 0
    }
    
    try:
        if isinstance(referral_data, dict):
            domains = referral_data.get("domains") or referral_data.get("referring_domains") or referral_data.get("referrers") or []
            if isinstance(domains, list):
                backlinks["total_referring_domains"] = len(domains)
                if domains and "refdomain" in domains[0]:
                    backlinks["top_referring_domains"] = [d["refdomain"] for d in domains[:10]]
                else:
                    backlinks["top_referring_domains"] = domains[:10]
        
        if isinstance(new_backlinks_data, dict):
            new_links = new_backlinks_data.get("backlinks") or new_backlinks_data.get("new_backlinks") or []
            if isinstance(new_links, list):
                backlinks["new_backlinks_count"] = len(new_links)
                backlinks["recent_backlinks"] = new_links[:10]
        
        log(f"Backlinks: {backlinks['total_referring_domains']} domains, {backlinks['new_backlinks_count']} new")
    except Exception as e:
        log(f"Error parsing backlink data: {e}", "ERROR")
    
    return backlinks

def identify_issues(metrics, onpage_data):
    """Identify SEO issues from collected data"""
    issues = {
        "critical": [],
        "moderate": [],
        "minor": []
    }
    
    title = metrics.get("title", "")
    if not title:
        issues["critical"].append("Missing page title")
    elif len(title) > 60:
        issues["moderate"].append(f"Title too long ({len(title)} chars, optimal: 50-60)")
    elif len(title) < 30:
        issues["minor"].append(f"Title too short ({len(title)} chars)")
    
    desc = metrics.get("description", "")
    if not desc:
        issues["critical"].append("Missing meta description")
    elif len(desc) > 160:
        issues["moderate"].append(f"Meta description too long ({len(desc)} chars)")
    
    h1_count = metrics.get("h1_count", 0)
    if h1_count == 0:
        issues["critical"].append("Missing H1 tag")
    elif h1_count > 1:
        issues["moderate"].append(f"Multiple H1 tags ({h1_count})")
    
    if not metrics.get("https_enabled"):
        issues["critical"].append("Website not using HTTPS")
    
    speed = metrics.get("page_speed", 0)
    if speed < 50:
        issues["moderate"].append(f"Poor page speed score ({speed}/100)")
    elif speed < 70:
        issues["minor"].append(f"Page speed could be improved ({speed}/100)")
    
    return issues

def generate_recommendations(metrics, keywords, backlinks, issues):
    # Generate actionable recommendations using RapidAPI AI endpoint if available, fallback to static
    recommendations = []
    
    if SEO_ANALYZER_API_URL and SEO_ANALYZER_API_KEY and SEO_ANALYZER_API_HOST:
        try:
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""
                            You are an SEO expert. Analyze the following SEO data and provide a list of 5-10 actionable, smart recommendations tailored to the data. Focus on improving rankings, traffic, and user experience. Be specific and prioritize based on severity.

                            Data:
                            Metrics: {json.dumps(metrics, indent=2)}
                            Keywords: {json.dumps(keywords, indent=2)}
                            Backlinks: {json.dumps(backlinks, indent=2)}
                            Issues: {json.dumps(issues, indent=2)}

                            Output as a bullet point list.
                            """
                    }
                ],
                "web_access": False
            }
            headers = {
                "x-rapidapi-key": SEO_ANALYZER_API_KEY,
                "x-rapidapi-host": SEO_ANALYZER_API_HOST,
                "Content-Type": "application/json"
            }
            
            log(f"Trying RapidAPI AI endpoint for recommendations")
            r = requests.post(SEO_ANALYZER_API_URL, json=payload, headers=headers, timeout=30)
            
            if r.status_code == 429:
                log("Rate limit exceeded, waiting 60 seconds...", "WARN")
                time.sleep(60)
                r = requests.post(SEO_ANALYZER_API_URL, json=payload, headers=headers, timeout=30)
            
            if DEBUG:
                log(f"Status: {r.status_code}, Response preview: {r.text[:200]}")
            
            if r.status_code == 200:
                data = r.json()
                rec_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                recommendations = [rec.strip() for rec in rec_text.split("\n") if rec.strip().startswith("-") or rec.strip().startswith("*") or rec.strip()]
                log("Generated recommendations using RapidAPI AI")
            else:
                log(f"RapidAPI AI request failed with status {r.status_code}", "ERROR")
        except Exception as e:
            log(f"Failed to generate recommendations with RapidAPI AI: {e}", "ERROR")
    
    if not recommendations:
        log("Falling back to static recommendations")
        score = metrics.get("overall_score", 0)
        if score < 50:
            recommendations.append("🔴 CRITICAL: Multiple major SEO issues detected. Immediate action required.")
        elif score < 70:
            recommendations.append("🟡 WARNING: Several SEO improvements needed for better rankings.")
        else:
            recommendations.append("🟢 GOOD: Solid SEO foundation. Focus on content and link building.")
        
        if issues["critical"]:
            recommendations.append(f"⚠️ Fix {len(issues['critical'])} critical issues immediately")
        
        if any("title" in str(i).lower() for i in issues["critical"] + issues["moderate"]):
            recommendations.append("Optimize page title: Make it unique, descriptive, 50-60 characters")
        
        if keywords["high_value_keywords"]:
            recommendations.append(f"Target {len(keywords['high_value_keywords'])} high-value keywords with low competition")
        
        if backlinks["total_referring_domains"] < 10:
            recommendations.append("Build backlinks: Low referring domain count detected")
        
        if backlinks["new_backlinks_count"] == 0:
            recommendations.append("No recent backlink activity - consider outreach campaign")
        
        if metrics.get("page_speed", 0) < 70:
            recommendations.append("Improve page speed: Optimize images, enable caching, minify CSS/JS")
    
    return recommendations




# Main

def analyze_domain(domain, seed_keyword=""):
    """Comprehensive domain analysis using all 5 APIs"""
    log(f"\n{'='*70}")
    log(f"Starting comprehensive analysis for: {domain}")
    log(f"{'='*70}\n")
    
    api_responses = {}
    
    log("Step 1/5: Technical SEO Audit...")
    api_responses["website_analyzer"] = call_website_analyzer(domain)
    time.sleep(5)
    
    log("Step 2/5: Keyword Research...")
    api_responses["keyword_finder"] = call_keyword_finder(domain, seed_keyword)
    time.sleep(5)
    
    log("Step 3/5: On-Page SEO Analysis...")
    api_responses["onpage_seo"] = call_onpage_seo(domain)
    time.sleep(5)
    
    log("Step 4/5: Referral Domain Discovery...")
    api_responses["referral_domains"] = call_referral_domain_finder(domain)
    time.sleep(5)
    
    log("Step 5/5: New Backlinks Check...")
    api_responses["new_backlinks"] = call_new_backlinks_finder(domain)
    
    log("\nProcessing and analyzing data...\n")
    
    metrics = parse_website_analyzer_data(api_responses["website_analyzer"])
    keywords = parse_keyword_data(api_responses["keyword_finder"])
    backlinks = parse_backlink_data(
        api_responses["referral_domains"],
        api_responses["new_backlinks"]
    )
    issues = identify_issues(metrics, api_responses["onpage_seo"])
    recommendations = generate_recommendations(metrics, keywords, backlinks, issues)
    
    result = {
        "domain": domain,
        "analysis_timestamp": current_timestamp(),
        "technical_audit": metrics,
        "keyword_analysis": keywords,
        "backlink_profile": backlinks,
        "seo_issues": issues,
        "recommendations": recommendations,
        "api_status": {
            "website_analyzer": bool(api_responses["website_analyzer"]),
            "keyword_finder": bool(api_responses["keyword_finder"]),
            "onpage_seo": bool(api_responses["onpage_seo"]),
            "referral_domains": bool(api_responses["referral_domains"]),
            "new_backlinks": bool(api_responses["new_backlinks"])
        }
    }
    
    if DEBUG:
        result["raw_api_responses"] = api_responses
    
    log(f"\n{'='*70}")
    log(f"Analysis Complete for {domain}")
    log(f"{'='*70}")
    log(f"Overall Score: {metrics.get('overall_score', 0)}/100")
    log(f"Critical Issues: {len(issues['critical'])}")
    log(f"Keywords Found: {keywords['total_keywords']}")
    log(f"Referring Domains: {backlinks['total_referring_domains']}")
    log(f"Recommendations: {len(recommendations)}")
    log(f"{'='*70}\n")
    
    return result



# Main Entry Point
def main():
    log("="*70)
    log("SEO Multi-API Analyzer Started")
    log("="*70)
    
    if not SEO_WEBSITE_ANALYSER_API_KEY:
        log("❌ ERROR: SEO_WEBSITE_ANALYSER_API_KEY not found!", "ERROR")
        return
    
    missing_urls = []
    if not SEO_WEBSITE_ANALYSER_API_HOST:
        missing_urls.append("SEO_WEBSITE_ANALYSER_API_HOST")
    if not KEYWORD_FINDER_API_URL:
        missing_urls.append("KEYWORD_FINDER_API_URL")
    if not ONPAGE_SEO_URL:
        missing_urls.append("ONPAGE_SEO_URL")
    if not REFERRAL_DOMAIN_FINDER_URL:
        missing_urls.append("REFERRAL_DOMAIN_FINDER_URL")
    if not NEW_BACKLINKS_FINDER_URL:
        missing_urls.append("NEW_BACKLINKS_FINDER_URL")
    if not SEO_ANALYZER_API_URL or not SEO_ANALYZER_API_KEY or not SEO_ANALYZER_API_HOST:
        missing_urls.append("SEO_ANALYZER_API_URL, SEO_ANALYZER_API_KEY, or SEO_ANALYZER_API_HOST")
    
    if missing_urls:
        log(f"⚠️ WARNING: Missing API URLs: {', '.join(missing_urls)}", "WARN")
        log("Some analyses will be skipped. Add these to your .env file.", "WARN")
    
    if not SEO_ANALYSIS_LINKS:
        log("❌ ERROR: SEO_ANALYSIS_LINKS not found!", "ERROR")
        return
    
    domains = [d.strip() for d in SEO_ANALYSIS_LINKS.split() if d.strip()]
    
    if not domains:
        log("❌ ERROR: No domains to analyze!", "ERROR")
        return
    
    log(f"\n✓ Found {len(domains)} domains to analyze")
    for i, d in enumerate(domains, 1):
        log(f"  {i}. {d}")
    
    data = load_existing_json(OUTPUT_FILE)
    analyzed = []
    
    for i, domain in enumerate(domains, 1):
        try:
            log(f"\n\n{'#'*70}")
            log(f"DOMAIN {i}/{len(domains)}")
            log(f"{'#'*70}\n")
            
            domain_result = analyze_domain(domain)
            analyzed.append(domain_result)
            
        except Exception as e:
            log(f"❌ Failed to analyze {domain}: {e}", "ERROR")
            analyzed.append({
                "domain": domain,
                "error": str(e),
                "timestamp": current_timestamp()
            })
        
        if i < len(domains):
            log(f"\nWaiting 10 seconds before next domain...\n")
            time.sleep(10)
    
    data["timestamp"] = current_timestamp()
    data["domains_analyzed"] = analyzed
    data["total_domains"] = len(analyzed)
    data["successful_analyses"] = sum(1 for d in analyzed if "error" not in d)
    
    if save_json(data, OUTPUT_FILE):
        log(f"\n{'='*70}")
        log("✅ SEO ANALYSIS COMPLETE!")
        log(f"{'='*70}")
        log(f"Total Domains: {len(analyzed)}")
        log(f"Successful: {data['successful_analyses']}")
        log(f"Failed: {len(analyzed) - data['successful_analyses']}")
        log(f"Output File: {OUTPUT_FILE}")
        log(f"{'='*70}\n")

if __name__ == "__main__":
    main()