import os
import re
import json
import time
import statistics
import urllib.parse
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# optional OpenAI-style client (may be Groq, openai, etc.)

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

# -------------------- CONFIG --------------------

@dataclass
class IntelConfig:
    RAPIDAPI_KEY: str
    GROQ_API_KEY: Optional[str]
    TRUSTPILOT_HOST: str = "trustpilot-reviews.p.rapidapi.com"
    JSEARCH_HOST: str = "jsearch.p.rapidapi.com"
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    @classmethod
    def from_env(cls) -> 'IntelConfig':
        rapidapi = os.getenv("RAPIDAPI_KEY", "")
        groq = os.getenv("GROQ_API_KEY", "") or None
        if not rapidapi:
            raise ValueError("Missing RAPIDAPI_KEY environment variable.")
        return cls(RAPIDAPI_KEY=rapidapi, GROQ_API_KEY=groq)

# -------------------- AI ANALYST --------------------

class AIAnalyst:
    """
    Wrapper around an LLM (OpenAI/Groq style) to produce strict JSON outputs.
    """

    def __init__(self, api_key: Optional[str], base_url: Optional[str] = None):
        self.available = False
        self.model = "gpt-4o-mini"
        self.client = None
        if OpenAI and api_key:
            try:
                kwargs = {"api_key": api_key}
                if base_url:
                    kwargs["base_url"] = base_url
                self.client = OpenAI(**kwargs)
                self.available = True
            except Exception:
                self.available = False

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 800, temperature: float = 0.2) -> Dict:
        if not self.available:
            return {'error': 'llm_unavailable'}
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            text = resp.choices[0].message.content.strip()
            if '```json' in text:
                text = text.split('```json', 1)[1].split('```', 1)[0].strip()
            elif text.startswith('```') and '```' in text[3:]:
                text = text.split('```', 2)[1].strip()
            parsed = json.loads(text)
            return parsed
        except Exception as e:
            return {'error': 'llm_call_failed', 'exception': str(e)}

    def _heuristic_hiring_analysis(self, jobs: List[Dict], company_name: str) -> Dict:
        titles = [j.get('job_title') or j.get('title') or '' for j in jobs]
        title_text = " ".join(titles).lower()
        words = re.findall(r"[a-zA-Z\+\#]{2,}", title_text)
        stop = {"and", "the", "with", "for", "senior", "jr", "sr", "ii", "iii"}
        freq = {}
        for w in words:
            if w in stop or len(w) < 3:
                continue
            freq[w] = freq.get(w, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:8]
        skills_in_demand = [t[0] for t in top]
        top_titles = sorted({t.strip() for t in titles if t.strip()}, key=lambda s: -len(s))[:5]
        return {
            'data_available': bool(jobs),
            'analysis': f"Found {len(jobs)} job postings for {company_name}.",
            'skills_in_demand': skills_in_demand,
            'growth_areas': skills_in_demand[:3],
            'talent_strategy': 'Focus hiring on top skill clusters.',
            'urgency_level': 'high' if len(jobs) > 10 else 'medium' if len(jobs) > 0 else 'low',
            'specific_insights': {'total_jobs_analyzed': len(jobs), 'top_titles': top_titles}
        }

    def _heuristic_review_analysis(self, reviews: List[Dict], company_name: str) -> Dict:
        ratings = []
        texts = []
        for r in reviews:
            try:
                rating = r.get('rating') or r.get('review_rating')
                if rating is not None:
                    ratings.append(float(rating))
            except Exception:
                pass
            texts.append(" ".join(filter(None, [
                str(r.get('review_title', '')), 
                str(r.get('review_text', '')),
                str(r.get('summary', '')),
                str(r.get('pros', '')),
                str(r.get('cons', ''))
            ])))
        avg = round(statistics.mean(ratings), 2) if ratings else 0.0
        big_text = " ".join(texts).lower()
        complaints = []
        for kw in ['management', 'pay', 'salary', 'promotion', 'work-life', 'benefits', 'culture', 'communication', 'support', 'service', 'delivery', 'quality']:
            if kw in big_text:
                complaints.append(kw)
        return {
            'data_available': bool(reviews),
            'analysis': f"Average rating {avg} based on {len(reviews)} reviews. Top themes: {', '.join(complaints[:5]) or 'Not enough themes found'}.",
            'top_complaints': complaints[:8],
            'weaknesses_to_exploit': complaints[:5],
            'sentiment_score': avg,
            'positioning_opportunity': 'Highlight strengths where reviews are weak.',
            'specific_insights': {'total_reviews_analyzed': len(reviews), 'actual_average_rating': avg}
        }

    def analyze_hiring_trends(self, jobs: List[Dict], company_name: str) -> Dict:
        if not jobs:
            return {'data_available': False, 'analysis': 'NO HIRING DATA FOUND', 'skills_in_demand': [], 'growth_areas': [], 'talent_strategy': 'No job postings', 'urgency_level': 'unknown'}
        
        system_prompt = (
            "You are a concise data-first recruiter & market analyst. RETURN ONLY VALID JSON (no surrounding text). "
            "Schema: {data_available: bool, analysis: str, skills_in_demand: list, growth_areas: list, "
            "talent_strategy: str, urgency_level: 'high'|'medium'|'low', specific_insights: object}."
        )
        brief_jobs = []
        for j in jobs[:200]:
            brief_jobs.append({
                'title': j.get('job_title') or j.get('title') or 'Not found',
                'company': j.get('company_name') or j.get('employer_name') or 'Not found',
                'location': j.get('location_name') or j.get('job_city') or '',
                'type': j.get('job_employment_type') or '',
                'posted_at': j.get('age_in_days') or j.get('job_posted_at_datetime_utc') or ''
            })
        user_prompt = f"Analyze these {len(brief_jobs)} job postings for {company_name}. DATA: {json.dumps(brief_jobs, ensure_ascii=False)}"
        resp = self._call_llm(system_prompt, user_prompt, max_tokens=900, temperature=0.2)
        if isinstance(resp, dict) and not resp.get('error'):
            return resp
        return self._heuristic_hiring_analysis(jobs, company_name)

    def analyze_reviews(self, reviews: List[Dict], company_name: str) -> Dict:
        if not reviews:
            return {'data_available': False, 'analysis': 'NO REVIEW DATA FOUND', 'top_complaints': [], 'weaknesses_to_exploit': [], 'sentiment_score': 0, 'positioning_opportunity': 'No review data'}
        
        system_prompt = (
            "You are a sentiment analyst. RETURN ONLY VALID JSON. "
            "Schema: {data_available: bool, analysis: str, top_complaints: list, weaknesses_to_exploit: list, sentiment_score: number, positioning_opportunity: str, specific_insights: object}."
        )
        brief_reviews = []
        ratings = []
        for r in reviews[:200]:
            rating = r.get('rating') or r.get('review_rating')
            try:
                if rating is not None:
                    ratings.append(float(rating))
            except Exception:
                pass
            brief_reviews.append({
                'rating': rating,
                'title': (r.get('review_title') or r.get('summary') or '')[:200],
                'text': (r.get('review_text') or r.get('pros') or '')[:400],
                'date': (r.get('review_date') or '')[:40]
            })
        avg = round(statistics.mean(ratings), 2) if ratings else 0.0
        user_prompt = f"Analyze these reviews for {company_name}. REVIEWS: {json.dumps(brief_reviews, ensure_ascii=False)}"
        resp = self._call_llm(system_prompt, user_prompt, max_tokens=1200, temperature=0.2)
        if isinstance(resp, dict) and not resp.get('error'):
            resp.setdefault('sentiment_score', avg)
            return resp
        return self._heuristic_review_analysis(reviews, company_name)

    def strategic_synthesis(self, intel: Dict, reports: List[Dict]) -> Dict:
        system_prompt = (
            "You are a strategic planner. RETURN ONLY JSON. "
            "Schema: {data_available: bool, immediate_actions: list, competitive_advantages: list, market_gaps: list, "
            "6_month_strategy: str, threats_to_monitor: list, messaging_angles: list, data_confidence: str}."
        )
        context = {'summary': intel, 'reports': reports}
        user_prompt = f"Synthesize strategy from this competitor intelligence. DATA: {json.dumps(context, ensure_ascii=False)}"
        resp = self._call_llm(system_prompt, user_prompt, max_tokens=1600, temperature=0.2)
        if isinstance(resp, dict) and not resp.get('error'):
            return resp
        
        total_jobs = sum(r.get('jobs', {}).get('total', 0) for r in reports)
        total_reviews = sum(r.get('reviews', {}).get('total', 0) for r in reports)
        return {
            'data_available': bool(reports),
            'immediate_actions': ["Audit hiring gaps", "Design messaging addressing complaints", "Run compensation benchmarks"],
            'competitive_advantages': ['Faster hiring', 'Better onboarding'],
            'market_gaps': ['Engineering talent shortage', 'Mid-level talent gaps'],
            '6_month_strategy': f"Focus on hiring & messaging. Jobs: {total_jobs}, reviews: {total_reviews}.",
            'threats_to_monitor': ['Pricing changes', 'Talent poaching'],
            'messaging_angles': ['Career growth', 'Compensation transparency'],
            'data_confidence': 'low' if total_jobs + total_reviews < 10 else 'medium' if total_jobs + total_reviews < 50 else 'high'
        }

# -------------------- JSearchCollector (FIXED) --------------------

class JSearchCollector:
    def __init__(self, api_key: str, host: str = "jsearch.p.rapidapi.com", user_agent: str = None):
        self.api_key = api_key
        self.host = host
        self.base_url = f"https://{self.host}"
        self.session = requests.Session()
        self.session.headers.update({
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
            "User-Agent": user_agent or "Mozilla/5.0"
        })

    def search_jobs(self, company: str, days: int = 30) -> List[Dict]:
        """
        FIXED: Search for jobs at a specific company using JSearch API.
        Uses proper query formatting and filters results by employer name.
        Reduced to single optimized query to avoid rate limits.
        Added country parameter.
        Increased num_pages for more results per call.
        """
        results = []
        
        # Use single optimized query
        queries = [f'jobs at {company}']
        
        for query in queries:
            try:
                # Proper parameters matching JSearch API documentation
                params = {
                    "query": query,
                    "page": "1",
                    "num_pages": "2",  # Get more results in one call
                    "date_posted": "month" if days <= 30 else "all",
                    "country": "us"  # Focus on US jobs for better relevance
                }
                
                # Use the correct endpoint
                url = f"{self.base_url}/search"
                
                print(f"      → JSearch query: '{query}' with params {params}")
                r = self.session.get(url, params=params, timeout=15)
                
                if r.status_code != 200:
                    print(f"      ✗ API returned status {r.status_code}")
                    if r.status_code == 429:
                        print("      ℹ Rate limit hit. Consider upgrading plan or waiting.")
                    continue
                
                data = self._safe_json(r)
                
                # Check for API errors
                if data.get('status') == 'error':
                    print(f"      ✗ API error: {data.get('error', 'Unknown')}")
                    continue
                
                # Extract jobs from response
                jobs = data.get('data', [])
                
                if not jobs:
                    print(f"      ℹ No jobs found for query '{query}'")
                    continue
                
                print(f"      ✓ API returned {len(jobs)} jobs")
                
                # Filter jobs by employer name (case-insensitive partial match)
                company_lower = company.lower()
                for job in jobs:
                    employer = (job.get('employer_name') or '').lower()
                    
                    # Check if company name is in employer name
                    if company_lower in employer or employer in company_lower:
                        # Avoid duplicates
                        job_id = job.get('job_id')
                        if job_id and job_id not in [j.get('job_id') for j in results]:
                            results.append(job)
                            print(f"      ✓ Match: {job.get('job_title', 'N/A')} at {job.get('employer_name', 'N/A')}")
                
                time.sleep(1)  # Increased rate limiting delay
                
            except requests.exceptions.Timeout:
                print(f"      ✗ Request timeout for query '{query}'")
                continue
            except requests.exceptions.RequestException as e:
                print(f"      ✗ Request failed for query '{query}': {e}")
                continue
            except Exception as e:
                print(f"      ✗ Unexpected error for query '{query}': {e}")
                continue
        
        print(f"      → Total unique jobs found: {len(results)}")
        return results[:50]  # Limit to 50 jobs

    def _safe_json(self, resp: requests.Response) -> Dict:
        try:
            return resp.json()
        except Exception as e:
            print(f"      ✗ JSON parsing failed: {e}")
            return {}

# -------------------- TrustPilotCollector --------------------

class TrustPilotCollector:
    """
    TrustPilot collector using RapidAPI 'trustpilot-reviews' endpoint.
    Multiple discovery strategies:
    1. Business search by company name
    2. Direct domain lookup
    3. Web scraping fallback
    """

    def __init__(self, api_key: str, host: str = "trustpilot-reviews.p.rapidapi.com", user_agent: str = None):
        self.api_key = api_key
        self.host = host
        self.base_url = f"https://{self.host}"
        self.user_agent = user_agent or "Mozilla/5.0"
        self.session = requests.Session()
        self.session.headers.update({
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
            "User-Agent": self.user_agent
        })

    def get_company_reviews(self, company_name: str, domain: str = None, limit: int = 20) -> List[Dict]:
        """
        Main entry point: tries multiple strategies to fetch reviews.
        """
        print(f"      🔍 TrustPilot search: '{company_name}' (domain: {domain or 'N/A'})")
        
        # Strategy 0: If we have a domain, try direct lookup first (most reliable)
        if domain:
            domain_clean = domain.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0].split(':')[0]
            print(f"      → Trying direct domain lookup: {domain_clean}")
            
            # Try to get business info by domain
            business_info = self._get_business_by_domain(domain_clean)
            if business_info:
                business_id = business_info.get('id') or business_info.get('business_id') or business_info.get('businessUnitId')
                print(f"      → Found business_id: {business_id}")
                
                if business_id:
                    reviews = self._fetch_business_reviews(business_id, limit)
                    if reviews:
                        print(f"      ✓ Retrieved {len(reviews)} reviews via domain lookup")
                        return reviews[:limit]
        
        # Strategy 1: Search by business name with various API endpoints
        print(f"      → Trying business name search variations...")
        business_data = self._search_business(company_name)
        if business_data:
            # business_data could be ID or full business object
            if isinstance(business_data, dict):
                business_id = business_data.get('id') or business_data.get('business_id') or business_data.get('businessUnitId')
                print(f"      → Found business via search: {business_data.get('displayName', 'Unknown')} (ID: {business_id})")
            else:
                business_id = business_data
                print(f"      → Found business_id: {business_id}")
            
            if business_id:
                reviews = self._fetch_business_reviews(business_id, limit)
                if reviews:
                    print(f"      ✓ Retrieved {len(reviews)} reviews via business search")
                    return reviews[:limit]
        
        # Strategy 2: Try scraping with company name variations
        print(f"      → Trying web scraping fallback...")
        reviews = self._scrape_trustpilot(company_name, domain, limit)
        if reviews:
            print(f"      ✓ Retrieved {len(reviews)} reviews via scraping")
            return reviews[:limit]
        
        print(f"      ✗ No TrustPilot data found for '{company_name}'")
        return []

    def _get_business_by_domain(self, domain: str) -> Optional[Dict]:
        """Get business info directly by domain - most reliable method."""
        endpoints_to_try = [
            (f"/trustpilot-business-info", {"domain": domain}),
            (f"/business/info", {"domain": domain}),
            (f"/business/lookup", {"domain": domain}),
            (f"/trustpilot-business-info", {"website": domain}),
        ]
        
        for endpoint, params in endpoints_to_try:
            try:
                r = self.session.get(f"{self.base_url}{endpoint}", params=params, timeout=12)
                if r.status_code == 200:
                    data = self._safe_json(r)
                    # Could be nested or direct
                    business = data.get('data') or data.get('business') or data
                    if business and isinstance(business, dict):
                        return business
            except Exception as e:
                continue
        
        return None

    def _search_business(self, query: str) -> Optional[Dict]:
        """Search for business and return full business object with ID."""
        # Try multiple query variations
        queries = [query]
        # Add cleaned version without common suffixes
        clean = re.sub(r'(,?\s*(Inc\.?|LLC|Corp\.?|Ltd\.?|Limited|S\.A\.R\.L\.?|SA)\s*$)', '', query, flags=re.I).strip()
        if clean != query:
            queries.append(clean)
        
        endpoints = [
            "/trustpilot-business-search",
            "/business/search",
            "/search/business",
            "/business-units/search"
        ]
        
        for q in queries:
            for endpoint in endpoints:
                try:
                    params = {"query": q, "limit": 10}
                    r = self.session.get(f"{self.base_url}{endpoint}", params=params, timeout=12)
                    
                    if r.status_code != 200:
                        # Try alternative param name
                        r = self.session.get(f"{self.base_url}{endpoint}", params={"name": q, "limit": 10}, timeout=12)
                        if r.status_code != 200:
                            continue
                    
                    data = self._safe_json(r)
                    businesses = data.get('data') or data.get('businesses') or data.get('businessUnits') or data.get('results') or []
                    
                    if isinstance(businesses, list) and businesses:
                        # Try to find best match
                        query_lower = q.lower()
                        
                        # Look for exact match
                        for biz in businesses:
                            name = (biz.get('name') or biz.get('displayName') or biz.get('businessName') or '').lower()
                            if query_lower == name:
                                print(f"      → Exact match found: {biz.get('name') or biz.get('displayName')}")
                                return biz
                        
                        # Look for strong partial match
                        for biz in businesses:
                            name = (biz.get('name') or biz.get('displayName') or biz.get('businessName') or '').lower()
                            if query_lower in name or name in query_lower:
                                print(f"      → Partial match found: {biz.get('name') or biz.get('displayName')}")
                                return biz
                        
                        # Return first result as fallback
                        print(f"      → Using first result: {businesses[0].get('name') or businesses[0].get('displayName')}")
                        return businesses[0]
                        
                except Exception as e:
                    continue
        
        return None

    def _fetch_business_reviews(self, business_id_or_obj: Any, limit: int = 20) -> List[Dict]:
        """Fetch reviews for a business. Handles both ID strings and business objects."""
        # Extract ID if we got a full business object
        if isinstance(business_id_or_obj, dict):
            business_id = (business_id_or_obj.get('id') or 
                          business_id_or_obj.get('business_id') or 
                          business_id_or_obj.get('businessUnitId') or
                          business_id_or_obj.get('identifyingName'))
        else:
            business_id = business_id_or_obj
        
        if not business_id:
            return []
        
        print(f"      → Fetching reviews for business_id: {business_id}")
        
        endpoints_and_params = [
            ("/trustpilot-business-reviews", {"business_id": business_id, "page": 1, "per_page": limit}),
            ("/trustpilot-business-reviews", {"businessId": business_id, "page": 1}),
            ("/business/reviews", {"business_id": business_id, "limit": limit}),
            ("/business/reviews", {"id": business_id, "limit": limit}),
            ("/reviews/business", {"business_id": business_id}),
            (f"/business/{business_id}/reviews", {"limit": limit}),
        ]
        
        for endpoint, params in endpoints_and_params:
            try:
                r = self.session.get(f"{self.base_url}{endpoint}", params=params, timeout=15)
                
                if r.status_code != 200:
                    continue
                
                data = self._safe_json(r)
                
                # Handle various response structures
                reviews = None
                
                # Try direct keys
                reviews = (data.get('data') or 
                          data.get('reviews') or 
                          data.get('results') or
                          data.get('items'))
                
                # Sometimes nested deeper
                if not reviews and isinstance(data, dict):
                    for key in data.keys():
                        if isinstance(data[key], dict):
                            reviews = (data[key].get('reviews') or 
                                     data[key].get('data') or
                                     data[key].get('items'))
                            if reviews:
                                break
                
                # Check if we got a list
                if isinstance(reviews, list) and reviews:
                    print(f"      → Found {len(reviews)} reviews in response")
                    normalized = []
                    for r_obj in reviews[:limit]:
                        normalized_review = self._normalize_review(r_obj)
                        # Debug: print first review structure
                        if len(normalized) == 0:
                            print(f"      → Sample review rating: {normalized_review.get('review_rating')}, title: {normalized_review.get('review_title')[:50] if normalized_review.get('review_title') else 'N/A'}")
                        normalized.append(normalized_review)
                    return normalized
                    
            except Exception as e:
                print(f"      ✗ Review fetch attempt failed: {e}")
                continue
        
        return []

    def _scrape_trustpilot(self, company_name: str, domain: str = None, limit: int = 20) -> List[Dict]:
        """Fallback: scrape TrustPilot website with better slug generation."""
        try:
            # Generate potential slugs
            slugs = []
            
            # If we have domain, use it
            if domain:
                domain_clean = domain.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0].split(':')[0]
                slugs.append(domain_clean)
                # Also try without TLD
                base = domain_clean.split('.')[0]
                slugs.append(base)
            
            # Create slug from company name
            slug = company_name.lower()
            # Remove common suffixes
            slug = re.sub(r'(,?\s*(inc\.?|llc|corp\.?|ltd\.?|limited|s\.a\.r\.l\.?|sa|gmbh)\s*$)', '', slug, flags=re.I)
            slug = slug.replace(' ', '-').replace(',', '').replace('.', '')
            slug = re.sub(r'[^a-z0-9\-]', '', slug)
            slugs.append(slug)
            
            # Try common patterns
            for slug_candidate in slugs:
                urls = [
                    f"https://www.trustpilot.com/review/{slug_candidate}",
                    f"https://www.trustpilot.com/review/www.{slug_candidate}.com",
                    f"https://uk.trustpilot.com/review/{slug_candidate}",
                    f"https://www.trustpilot.com/review/{slug_candidate}.com",
                ]
                
                for url in urls:
                    try:
                        headers = {"User-Agent": self.user_agent}
                        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                        if r.status_code == 200 and 'trustpilot.com/review/' in r.url:
                            print(f"      → Successfully loaded: {r.url}")
                            reviews = self._parse_review_html(r.text)
                            if reviews:
                                return reviews[:limit]
                    except Exception:
                        continue
        except Exception as e:
            print(f"      ✗ Scraping failed: {e}")
        
        return []

    def _parse_review_html(self, html: str) -> List[Dict]:
        """Parse reviews from TrustPilot HTML with better rating extraction."""
        soup = BeautifulSoup(html, "html.parser")
        reviews = []
        
        # Look for review cards - TrustPilot uses specific data attributes
        for card in soup.find_all(['article', 'div', 'section'], attrs={'data-service-review-card-paper': True}):
            try:
                review_data = self._extract_review_from_card(card)
                if review_data:
                    reviews.append(review_data)
            except Exception:
                continue
        
        # Fallback: look for any article or div with review-like structure
        if not reviews:
            for card in soup.find_all(['article', 'div'], attrs={'class': re.compile(r'review|paper-card|styles_reviewCard', re.I)}):
                try:
                    review_data = self._extract_review_from_card(card)
                    if review_data:
                        reviews.append(review_data)
                except Exception:
                    continue
        
        print(f"      → Parsed {len(reviews)} reviews from HTML")
        return reviews

    def _extract_review_from_card(self, card) -> Optional[Dict]:
        """Extract review data from a single card element."""
        rating = None
        
        # Try multiple rating extraction methods
        # Method 1: Look for data-service-review-rating
        rating_elem = card.find(attrs={'data-service-review-rating': True})
        if rating_elem:
            try:
                rating = int(rating_elem.get('data-service-review-rating'))
            except:
                pass
        
        # Method 2: Look for star images with alt text
        if not rating:
            img = card.find('img', attrs={'alt': re.compile(r'Rated \d', re.I)})
            if img:
                alt = img.get('alt', '')
                match = re.search(r'Rated (\d)', alt)
                if match:
                    rating = int(match.group(1))
        
        # Method 3: Look for aria-label with rating
        if not rating:
            rated = card.find(attrs={'aria-label': re.compile(r'Rated \d|(\d) out of', re.I)})
            if rated:
                label = rated.get('aria-label', '')
                match = re.search(r'(\d)\s*out of|Rated (\d)', label)
                if match:
                    rating = int(match.group(1) or match.group(2))
        
        # Method 4: Count star elements
        if not rating:
            stars = card.find_all(attrs={'name': re.compile(r'star', re.I)})
            if stars:
                rating = len([s for s in stars if 'star-fill' in str(s) or 'filled' in str(s).lower()])
        
        # Get title
        title = ''
        title_elem = card.find(['h2', 'h3', 'h4'], attrs={'data-service-review-title-typography': True})
        if not title_elem:
            title_elem = card.find(['h2', 'h3', 'h4', 'a'])
        if title_elem:
            title = title_elem.get_text().strip()
        
        # Get review text
        text = ''
        text_elem = card.find(['p', 'div'], attrs={'data-service-review-text-typography': True})
        if not text_elem:
            text_elem = card.find(['p', 'div'], attrs={'class': re.compile(r'review.*text|content', re.I)})
        if text_elem:
            text = text_elem.get_text().strip()
        
        # Get date
        date = ''
        date_elem = card.find('time')
        if date_elem:
            date = date_elem.get('datetime', '') or date_elem.get_text().strip()
        
        # Only return if we have at least rating or text
        if rating or text or title:
            return {
                'review_rating': rating,
                'review_title': title,
                'review_text': text,
                'review_date': date
            }
        
        return None

    def _normalize_review(self, r: Dict) -> Dict:
        """Normalize review data to consistent format."""
        return {
            'review_rating': r.get('review_rating') or r.get('rating') or r.get('stars'),
            'review_title': r.get('review_title') or r.get('title') or r.get('headline') or '',
            'review_text': r.get('review_text') or r.get('text') or r.get('content') or '',
            'review_date': r.get('review_date') or r.get('date') or r.get('createdAt') or '',
            'review_likes': r.get('review_likes') or r.get('likes') or 0,
            'author_name': r.get('author_title') or r.get('author_name') or r.get('displayName') or '',
            'author_reviews': r.get('author_reviews_number') or 0
        }

    def _safe_json(self, resp: requests.Response) -> Dict:
        try:
            return resp.json()
        except Exception:
            return {}

# -------------------- PricingAnalyzer --------------------

class PricingAnalyzer:
    def analyze(self, competitor_data: Dict) -> Dict:
        description = competitor_data.get('company', {}).get('description', '') or ''
        evidence = ' '.join([e.get('snippet', '') for e in competitor_data.get('evidence', [])]) if competitor_data.get('evidence') else ''
        text = (description + " " + evidence).lower()
        has_free = any(w in text for w in ['free trial', 'free plan', 'freemium', 'free tier'])
        has_enterprise = 'enterprise' in text or 'custom pricing' in text
        has_tiers = any(w in text for w in ['starter', 'professional', 'premium', 'basic', 'pro'])

        if has_free and has_tiers:
            model = "freemium"
        elif has_enterprise and has_tiers:
            model = "tiered_enterprise"
        elif has_enterprise:
            model = "enterprise_only"
        elif has_tiers:
            model = "tiered"
        else:
            model = "unknown"
        
        return {
            'pricing_model': model,
            'has_free_tier': has_free,
            'has_enterprise': has_enterprise,
            'transparency': 'low' if ('contact' in text and 'pricing' in text) else 'medium'
        }

# -------------------- CompetitorIntelligence --------------------

class CompetitorIntelligence:
    def __init__(self, config: IntelConfig):
        self.config = config
        self.jsearch = JSearchCollector(config.RAPIDAPI_KEY, host=config.JSEARCH_HOST, user_agent=config.USER_AGENT)
        self.trustpilot = TrustPilotCollector(config.RAPIDAPI_KEY, host=config.TRUSTPILOT_HOST, user_agent=config.USER_AGENT)
        self.pricing = PricingAnalyzer()
        self.ai = AIAnalyst(config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1" if config.GROQ_API_KEY else None)

    def gather_intelligence(self, competitors: List[Dict], source_company: str) -> Dict:
        print("\n" + "=" * 80)
        print("🕵️  COMPETITOR INTELLIGENCE GATHERING (TrustPilot Edition)")
        print("=" * 80 + "\n")
        intel_reports = []
        
        for i, comp in enumerate(competitors, 1):
            try:
                name = comp['company']['name']
            except Exception:
                name = comp.get('name') or comp.get('company') or "Unknown"
            domain = comp.get('domain', '')
            
            print(f"📊 [{i}/{len(competitors)}] Analyzing: {name}")
            report = self._analyze_competitor(name, domain, comp)
            intel_reports.append(report)
            print()
            time.sleep(0.5)
        
        print("🧠 Synthesizing strategic insights...")
        strategy = self._generate_strategy(intel_reports)
        
        results = {
            'analysis_date': datetime.utcnow().isoformat() + 'Z',
            'source_company': source_company,
            'competitors_analyzed': len(intel_reports),
            'intelligence_reports': intel_reports,
            'strategic_recommendations': strategy,
            'market_overview': self._market_overview(intel_reports),
            'data_quality_summary': self._data_quality_summary(intel_reports)
        }
        
        print("\n✅ INTELLIGENCE GATHERING COMPLETE\n")
        return results

    def _analyze_competitor(self, company_name: str, domain: str, comp_obj: Dict) -> Dict:
        print("   🔍 Scraping jobs (JSearch)...")
        jobs = []
        try:
            jobs = self.jsearch.search_jobs(company_name)
        except Exception as e:
            print(f"   ✗ JSearch failed: {e}")
        print(f"   ✓ Found: {len(jobs)} jobs")

        print("   💬 Fetching reviews (TrustPilot)...")
        reviews = []
        try:
            reviews = self.trustpilot.get_company_reviews(company_name, domain=domain, limit=40)
        except Exception as e:
            print(f"   ✗ TrustPilot collector error: {e}")
        print(f"   ✓ Found: {len(reviews)} reviews")

        print("   💰 Analyzing pricing...", end=' ')
        pricing = self.pricing.analyze(comp_obj)
        print(f"✓ {pricing['pricing_model']}")
        
        print("   🤖 AI analysis (hiring + sentiment)...")
        hiring = self.ai.analyze_hiring_trends(jobs, company_name)
        sentiment = self.ai.analyze_reviews(reviews, company_name)
        
        return {
            'company': company_name,
            'domain': domain,
            'tier': comp_obj.get('tier', 'N/A'),
            'score': comp_obj.get('score', 0),
            'raw_data': {
                'jobs_found': len(jobs),
                'reviews_found': len(reviews),
                'sample_job_titles': [j.get('job_title', '') for j in jobs[:5]],
                'sample_review_ratings': [r.get('review_rating') for r in reviews[:5]]
            },
            'jobs': {
                'total': len(jobs),
                'recent_roles': [j.get('job_title') or j.get('title') for j in jobs[:8]],
                'locations': list({(j.get('location_name') or j.get('job_city') or 'N/A') for j in jobs}),
            },
            'hiring_analysis': hiring,
            'reviews': {
                'total': len(reviews),
                'avg_rating': self._avg_rating(reviews),
                'sample_titles': [r.get('review_title', '')[:60] for r in reviews[:5]]
            },
            'sentiment_analysis': sentiment,
            'pricing_intel': pricing,
            'data_quality': {
                'has_jobs': len(jobs) > 0,
                'has_reviews': len(reviews) > 0,
                'confidence': 'high' if (len(jobs) > 5 and len(reviews) > 5) else 'medium' if (len(jobs) > 0 or len(reviews) > 0) else 'low',
                'ai_used_real_data': hiring.get('data_available', False) or sentiment.get('data_available', False)
            }
        }

    def _generate_strategy(self, reports: List[Dict]) -> Dict:
        total_jobs = sum(r['jobs']['total'] for r in reports)
        total_reviews = sum(r['reviews']['total'] for r in reports)
        intel_summary = {
            'hiring_analysis': {
                'total_jobs_found': total_jobs,
                'companies_with_jobs': sum(1 for r in reports if r['jobs']['total'] > 0)
            },
            'sentiment_analysis': {
                'total_reviews_found': total_reviews,
                'companies_with_reviews': sum(1 for r in reports if r['reviews']['total'] > 0)
            }
        }
        return self.ai.strategic_synthesis(intel_summary, reports)

    def _market_overview(self, reports: List[Dict]) -> Dict:
        total_jobs = sum(r['jobs']['total'] for r in reports)
        total_reviews = sum(r['reviews']['total'] for r in reports)
        return {
            'total_competitors': len(reports),
            'total_jobs_found': total_jobs,
            'total_reviews_found': total_reviews,
            'companies_with_jobs': sum(1 for r in reports if r['jobs']['total'] > 0),
            'companies_with_reviews': sum(1 for r in reports if r['reviews']['total'] > 0)
        }

    def _data_quality_summary(self, reports: List[Dict]) -> Dict:
        total = len(reports)
        with_jobs = sum(1 for r in reports if r['jobs']['total'] > 0)
        with_reviews = sum(1 for r in reports if r['reviews']['total'] > 0)
        return {
            'total_companies': total,
            'companies_with_job_data': f"{with_jobs}/{total} ({with_jobs/total*100:.1f}%)" if total else "0/0",
            'companies_with_review_data': f"{with_reviews}/{total} ({with_reviews/total*100:.1f}%)" if total else "0/0",
            'total_jobs_found': sum(r['jobs']['total'] for r in reports),
            'total_reviews_found': sum(r['reviews']['total'] for r in reports),
            'data_quality_verdict': 'GOOD' if (with_jobs > total/2 or with_reviews > total/2) else 'PARTIAL' if (with_jobs > 0 or with_reviews > 0) else 'POOR'
        }

    def _avg_rating(self, reviews: List[Dict]) -> float:
        if not reviews:
            return 0.0
        values = []
        for r in reviews:
            try:
                val = r.get('review_rating') or r.get('rating')
                if val is not None:
                    values.append(float(val))
            except Exception:
                continue
        return round(statistics.mean(values), 2) if values else 0.0

# -------------------- MAIN --------------------

def main():
    print("\n" + "=" * 80)
    print("🕵️  COMPETITOR INTELLIGENCE AGENT (TrustPilot Edition)")
    print("=" * 80 + "\n")

    try:
        config = IntelConfig.from_env()
    except Exception as e:
        print("❌ Configuration error:", e)
        return

    import glob
    files = glob.glob("competitors_*.json")
    if not files:
        print("❌ No competitor discovery results found. Run discovery agent first.")
        return

    latest = max(files)
    try:
        with open(latest, 'r', encoding='utf-8') as f:
            discovery = json.load(f)
    except Exception as e:
        print("❌ Failed to load discovery file:", e)
        return

    competitors = discovery.get('competitors', [])[:12]
    source = discovery.get('source_company', 'Unknown')

    agent = CompetitorIntelligence(config)
    intel = agent.gather_intelligence(competitors, source)

    out_name = f"intelligence_trustpilot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_name, 'w', encoding='utf-8') as of:
        json.dump(intel, of, indent=2, ensure_ascii=False)
    print(f"💾 Intelligence saved: {out_name}")

if __name__ == "__main__":
    main()
