import json
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from typing import Dict, List, Optional, Tuple
import time
from openai import OpenAI
from dataclasses import dataclass, asdict
from enum import Enum
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==================== CONFIGURATION ====================
@dataclass
class Config:
    """Centralized configuration - loads from environment variables"""
    GOOGLE_API_KEY: str
    GOOGLE_CSE_ID: str
    GROQ_API_KEY: str
    RAPIDAPI_KEY: str
    RAPIDAPI_HOST: str
    
    # Scoring weights (must sum to 100)
    WEIGHT_AI: int = 35
    WEIGHT_KEYWORDS: int = 20
    WEIGHT_MODEL: int = 25
    WEIGHT_SOCIAL: int = 10
    WEIGHT_CONTENT: int = 10
    
    # Thresholds
    THRESHOLD_DIRECT: int = 70
    THRESHOLD_STRONG: int = 50
    THRESHOLD_MODERATE: int = 30
    THRESHOLD_AI_VETO: int = 20
    
    # Blocked domains
    BLOCKED_DOMAINS: List[str] = None
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create Config instance from environment variables"""
        # Required API keys
        google_api_key = os.getenv('GOOGLE_API_KEY')
        google_cse_id = os.getenv('GOOGLE_CSE_ID')
        groq_api_key = os.getenv('GROQ_API_KEY')
        rapidapi_key = os.getenv('RAPIDAPI_KEY')
        rapidapi_host = os.getenv('RAPIDAPI_HOST', 'scrapeninja.p.rapidapi.com')
        
        # Validate required keys
        missing_keys = []
        if not google_api_key:
            missing_keys.append('GOOGLE_API_KEY')
        if not google_cse_id:
            missing_keys.append('GOOGLE_CSE_ID')
        if not groq_api_key:
            missing_keys.append('GROQ_API_KEY')
        if not rapidapi_key:
            missing_keys.append('RAPIDAPI_KEY')
        
        if missing_keys:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")
        
        return cls(
            GOOGLE_API_KEY=google_api_key,
            GOOGLE_CSE_ID=google_cse_id,
            GROQ_API_KEY=groq_api_key,
            RAPIDAPI_KEY=rapidapi_key,
            RAPIDAPI_HOST=rapidapi_host
        )
    
    def __post_init__(self):
        if self.BLOCKED_DOMAINS is None:
            self.BLOCKED_DOMAINS = [
                'g2.com', 'capterra.com', 'trustpilot.com', 'gartner.com',
                'alternativeto.net', 'producthunt.com', 'crunchbase.com',
                'linkedin.com', 'forbes.com', 'techcrunch.com', 'medium.com',
                'reddit.com', 'clutch.co', 'wikipedia.org', 'youtube.com',
                'facebook.com', 'twitter.com', 'instagram.com'
            ]


class CompetitorTier(Enum):
    """Competitor classification tiers"""
    DIRECT = ("🥇 DIRECT", 70)
    STRONG = ("🥈 STRONG", 50)
    MODERATE = ("🥉 MODERATE", 30)
    WEAK = ("⚪ WEAK", 0)
    
    @classmethod
    def from_score(cls, score: float) -> 'CompetitorTier':
        if score >= 70:
            return cls.DIRECT
        elif score >= 50:
            return cls.STRONG
        elif score >= 30:
            return cls.MODERATE
        return cls.WEAK


# ==================== AI SERVICE ====================
class AIService:
    """Centralized AI operations using Groq"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "llama-3.3-70b-versatile"
    
    def extract_business_context(self, company_data: Dict) -> Dict[str, str]:
        """AI-powered extraction of niche, sector, and location from company data"""
        description = company_data.get('company', {}).get('description', '')
        name = company_data.get('company', {}).get('name', '')
        domain = company_data.get('domain', '')
        
        # Gather context from evidence
        evidence_snippets = [e.get('snippet', '') for e in company_data.get('evidence', [])[:5]]
        context = f"{name}\n{description}\n" + "\n".join(evidence_snippets[:3])
        
        prompt = f"""Analyze this company and extract key business information:

Company: {name}
Domain: {domain}
Description: {description}

Context snippets:
{chr(10).join(evidence_snippets[:3])}

Extract and return ONLY valid JSON with these fields:
{{
  "niche": "specific market niche (e.g., 'corporate travel management', 'expense tracking software')",
  "sector": "industry sector (e.g., 'SaaS', 'FinTech', 'Healthcare')",
  "location": "headquarters location in format 'City, Country' or 'International' if unclear"
}}

Be specific and concise. If unclear, use best guess."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a business analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{[^{}]*\}', result_text)
            
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"⚠️  AI extraction failed: {e}")
        
        # Fallback
        return {
            "niche": self._extract_niche_fallback(description),
            "sector": "Technology" if any(w in description.lower() for w in ['software', 'platform', 'saas']) else "Services",
            "location": "International"
        }
    
    def _extract_niche_fallback(self, description: str) -> str:
        """Simple keyword-based niche extraction as fallback"""
        desc_lower = description.lower()
        
        # Common patterns
        if 'travel' in desc_lower and 'corporate' in desc_lower:
            return 'corporate travel management'
        elif 'expense' in desc_lower and 'management' in desc_lower:
            return 'expense management'
        elif 'crm' in desc_lower or 'customer relationship' in desc_lower:
            return 'customer relationship management'
        elif 'hr' in desc_lower or 'human resource' in desc_lower:
            return 'human resources software'
        
        return 'business software'
    
    def generate_search_queries(self, niche: str, sector: str) -> List[str]:
        """Generate targeted search queries using AI"""
        prompt = f"""Generate 8 focused search queries to find "{niche}" companies in "{sector}".

Requirements:
- Focus on finding actual company websites, not review sites
- Use product/solution-focused language
- Include pricing/demo queries for commercial intent
- Keep queries concise (2-5 words)

Return ONLY the queries, one per line, no numbering."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Return only search queries, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            queries = [q.strip().strip('"\'') for q in response.choices[0].message.content.strip().split('\n') if q.strip()]
            return queries[:8]
            
        except Exception:
            # Fallback queries
            return [
                f'{niche} software',
                f'{niche} platform',
                f'{sector} {niche}',
                f'best {niche} tools',
                f'{niche} solution',
                f'{niche} pricing'
            ]
    
    def compare_competitors(self, source_desc: str, target_desc: str, source_name: str, target_name: str) -> Dict:
        """AI-powered competitor analysis"""
        prompt = f"""Compare these companies as potential competitors:

SOURCE: {source_name}
{source_desc[:500]}

TARGET: {target_name}
{target_desc[:500]}

Score 0-100:
- 80-100: Direct competitor (same market/product)
- 60-79: Strong competitor (overlapping services)
- 40-59: Moderate competitor (adjacent market)
- 20-39: Weak/tangential
- 0-19: NOT a competitor

Return JSON: {{"score": <int>, "is_competitor": <bool>, "reasoning": "<brief explanation>"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a business analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{[^{}]*\}', result_text)
            
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'score': min(100, max(0, result.get('score', 50))),
                    'is_competitor': bool(result.get('is_competitor', True)),
                    'reasoning': result.get('reasoning', 'Analysis completed')[:200]
                }
        except Exception:
            pass
        
        return {'score': 50, 'is_competitor': True, 'reasoning': 'Analysis unavailable'}


# ==================== COMPETITOR FINDER ====================
class CompetitorFinder:
    """Main competitor discovery engine"""
    
    def __init__(self, config: Config):
        self.config = config
        self.ai = AIService(config.GROQ_API_KEY)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # State
        self.found_competitors = []
        self.found_domains = set()
        self.ai_rejections = []
        self.source_data = None
        self.source_domain = None
        self.source_keywords = []
        self.source_model = {}
    
    def discover(self, company_data: Dict, target: int = 10) -> Dict:
        """Main discovery pipeline"""
        print(f"\n{'='*80}")
        print(f"🚀 INTELLIGENT COMPETITOR DISCOVERY")
        print(f"{'='*80}\n")
        
        self.source_data = company_data
        self.source_domain = company_data.get('domain', '').replace('www.', '').lower()
        
        # Extract proper company name from input
        source_name = self._extract_source_company_name(company_data)
        self.source_data['company']['name'] = source_name  # Update with clean name
        
        # Extract business context using AI
        print("   🤖 Analyzing source company...", end=' ')
        context = self.ai.extract_business_context(company_data)
        print("✓")
        
        print(f"   Company: {source_name}")
        print(f"   Domain: {self.source_domain}")
        print(f"   Niche: {context['niche']}")
        print(f"   Sector: {context['sector']}")
        print(f"   Location: {context['location']}")
        print(f"   Target: {target} competitors\n")
        
        # Prepare source analysis
        self.source_keywords = self._extract_keywords(company_data['company']['description'])
        self.source_model = self._analyze_business_model(company_data)
        
        # Generate queries
        print("   🔍 Generating search queries...", end=' ')
        queries = self._prepare_queries(context, target)
        print(f"✓ {len(queries)} queries\n")
        print(f"{'─'*80}\n")
        
        # Search and analyze
        for i, query_obj in enumerate(queries, 1):
            if len(self.found_competitors) >= target:
                break
            
            self._process_query(query_obj, i, len(queries), target)
        
        # Finalize results
        return self._build_results(context, target)
    
    def _prepare_queries(self, context: Dict, target: int) -> List[Dict]:
        """Prepare search queries with geo-targeting"""
        queries = self.ai.generate_search_queries(context['niche'], context['sector'])
        query_objects = [{'query': q, 'local': False} for q in queries]
        
        # Add local query if location is specific
        location = context['location']
        if location and location != "International" and ',' in location:
            city = location.split(',')[0].strip()
            local_query = f"{context['niche']} {city}"
            query_objects.insert(0, {'query': local_query, 'local': True})
            print(f"   🏠 Local query: '{local_query}'")
        
        return query_objects
    
    def _process_query(self, query_obj: Dict, index: int, total: int, target: int):
        """Process a single search query"""
        query = query_obj['query']
        is_local = query_obj['local']
        
        label = "🏠 LOCAL" if is_local else "🌍 INTL"
        print(f"🔍 {label} Query {index}/{total}: {query}")
        
        results = self._search_google(query, is_local)
        print(f"   → {len(results)} results\n")
        
        for result in results:
            if len(self.found_competitors) >= target:
                break
            
            self._process_result(result)
    
    def _process_result(self, result: Dict):
        """Process a single search result"""
        domain = result['domain']
        print(f"   🌐 {domain}")
        
        # Quick filter
        if not self._quick_filter(domain, result['url'], result['title'], result['snippet']):
            print()
            return
        
        # Crawl and extract
        print(f"      📡 Crawling...", end=' ')
        data = self._extract_competitor_data(result)
        
        if not data:
            print("✗")
            print(f"      ❌ Failed to crawl\n")
            return
        
        print("✓")
        print(f"      ⚙️  {data['company']['name']}")
        
        # Score
        print(f"      🎯 Scoring...", end=' ')
        score, breakdown, accepted = self._score_competitor(data)
        print("✓")
        
        tier = CompetitorTier.from_score(score)
        print(f"      {'─'*60}")
        print(f"      📊 SCORE: {score:.1f}/100 → {tier.value[0]}")
        print(f"      {'─'*60}")
        
        if not accepted:
            print(f"      🚫 AI VETO: {breakdown['ai_analysis']['reasoning']}")
            print(f"      ❌ REJECTED\n")
            self.ai_rejections.append({
                'name': data['company']['name'],
                'domain': domain,
                'reason': breakdown['ai_analysis']['reasoning'],
                'ai_score': breakdown['ai_analysis']['score']
            })
            return
        
        # Show breakdown
        print(f"         • AI: {breakdown['ai_analysis']['points']:.1f}/{self.config.WEIGHT_AI}")
        print(f"         • Keywords: {breakdown['keyword_overlap']['points']:.1f}/{self.config.WEIGHT_KEYWORDS}")
        print(f"         • Model: {breakdown['business_model']['points']:.1f}/{self.config.WEIGHT_MODEL}")
        print(f"         • Social: {breakdown['social_presence']['points']:.1f}/{self.config.WEIGHT_SOCIAL}")
        print(f"         • Content: {breakdown['content_quality']['points']:.1f}/{self.config.WEIGHT_CONTENT}")
        
        if score >= self.config.THRESHOLD_STRONG:
            data['score'] = score
            data['tier'] = tier.value[0]
            data['breakdown'] = breakdown
            self.found_competitors.append(data)
            self.found_domains.add(domain)
            print(f"      ✅ ACCEPTED ({len(self.found_competitors)})")
        else:
            print(f"      ❌ Score too low")
        
        print()
    
    def _quick_filter(self, domain: str, url: str, title: str, snippet: str) -> bool:
        """Quick filtering before crawling"""
        # Check if it's the source company
        if domain == self.source_domain or self.source_domain in domain or domain in self.source_domain:
            print(f"      🚫 Source company (skipping self)")
            return False
        
        if any(blocked in domain for blocked in self.config.BLOCKED_DOMAINS):
            print(f"      ❌ Blocked domain")
            return False
        
        if domain in self.found_domains:
            print(f"      ⏭️  Duplicate")
            return False
        
        bad_paths = ['/jobs/', '/careers/', '/blog/', '/article/', '/news/']
        if any(path in url.lower() for path in bad_paths):
            print(f"      ❌ Content page")
            return False
        
        print(f"      ✅ Passed")
        return True
    
    def _search_google(self, query: str, local_only: bool = False) -> List[Dict]:
        """Search Google with optional geo-targeting"""
        try:
            params = {
                'key': self.config.GOOGLE_API_KEY,
                'cx': self.config.GOOGLE_CSE_ID,
                'q': query,
                'num': 10
            }
            
            r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
            items = r.json().get('items', [])
            
            return [{
                'title': i['title'],
                'url': i['link'],
                'domain': urllib.parse.urlparse(i['link']).netloc.replace('www.', ''),
                'snippet': i.get('snippet', ''),
                'is_local_search': local_only
            } for i in items]
        except Exception:
            return []
    
    def _extract_competitor_data(self, result: Dict) -> Optional[Dict]:
        """Extract data from competitor website"""
        html = self._crawl_url(result['url'])
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract name from multiple sources (priority order)
        name = None
        
        # 1. Try og:site_name (most reliable for company name)
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            name = og_site.get('content').strip()
        
        # 2. Try JSON-LD structured data
        if not name:
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    data = json.loads(json_ld.string)
                    if isinstance(data, dict):
                        name = data.get('name') or data.get('legalName')
                    elif isinstance(data, list):
                        name = data[0].get('name') if data else None
                except:
                    pass
        
        # 3. Try Twitter card site name
        if not name:
            twitter_site = soup.find('meta', attrs={'name': 'twitter:site'})
            if twitter_site and twitter_site.get('content'):
                name = twitter_site.get('content').strip().lstrip('@')
        
        # 4. Try page title (clean it up)
        if not name:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Remove common suffixes
                for suffix in [' | ', ' - ', ' – ', ' — ']:
                    if suffix in title:
                        name = title.split(suffix)[0].strip()
                        break
                if not name:
                    name = title
        
        # 5. Last resort: use domain name (cleaned)
        if not name:
            name = result['domain'].replace('.com', '').replace('.io', '').replace('-', ' ').title()
        
        # Clean and truncate
        name = name[:100] if name else 'Unknown Company'
        
        # Extract description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = ''
        if meta_desc:
            description = meta_desc.get('content', '').strip()
        else:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                description = og_desc.get('content', '').strip()
        
        return {
            'input_url': result['url'],
            'domain': result['domain'],
            'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'company': {
                'name': name,
                'description': description,
                'location': '',
                'is_local': result['is_local_search']
            },
            'social': {},
            'evidence': [],
            'snippet': result['snippet']
        }
    
    def _crawl_url(self, url: str) -> Optional[str]:
        """Crawl URL with fallback"""
        # Try ScrapeNinja
        try:
            headers = {
                'x-rapidapi-key': self.config.RAPIDAPI_KEY,
                'x-rapidapi-host': self.config.RAPIDAPI_HOST,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"https://{self.config.RAPIDAPI_HOST}/scrape",
                headers=headers,
                json={"url": url},
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                html = result.get('body', '')
                if html and len(html) > 500:
                    return html
        except Exception:
            pass
        
        # Fallback
        try:
            response = self.session.get(url, timeout=10, allow_redirects=True)
            if response.status_code == 200 and len(response.text) > 500:
                return response.text
        except Exception:
            pass
        
        return None
    
    def _extract_source_company_name(self, company_data: Dict) -> str:
        """Extract clean source company name from input JSON"""
        # Try multiple sources in order of reliability
        
        # 1. Check social media profiles (often most accurate)
        social = company_data.get('social', {})
        if social.get('linkedin'):
            linkedin_url = social['linkedin']
            # Extract from LinkedIn URL like https://www.linkedin.com/company/travelperk
            match = re.search(r'/company/([^/]+)', linkedin_url)
            if match:
                name = match.group(1).replace('-', ' ').title()
                if len(name) > 3 and len(name) < 50:
                    return name
        
        # 2. Try to extract from domain
        domain = company_data.get('domain', '')
        if domain:
            # Remove common TLDs and clean up
            clean_domain = domain.replace('www.', '').split('.')[0]
            # Convert to proper case (e.g., 'travelperk' -> 'TravelPerk')
            if clean_domain:
                name = clean_domain.title()
                if len(name) > 2:
                    return name
        
        # 3. Fallback to existing name (but clean it)
        existing_name = company_data.get('company', {}).get('name', '')
        if existing_name:
            # If it's too long or looks like a tagline, try to clean it
            if len(existing_name) < 50 and '|' not in existing_name and ' for ' not in existing_name.lower():
                return existing_name
            # Try to extract brand name from title
            parts = existing_name.split('|')[0].split('-')[0].strip()
            if parts and len(parts) < 50:
                return parts
        
        return "Unknown Company"
    
    def _extract_keywords(self, text: str, top_n: int = 25) -> List[str]:
        """Extract keywords from text"""
        if not text:
            return []
        
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]
        
        freq = {}
        for kw in keywords:
            freq[kw] = freq.get(kw, 0) + 1
        
        sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_kw[:top_n]]
    
    def _analyze_business_model(self, data: Dict) -> Dict:
        """Analyze business model characteristics"""
        description = data['company']['description'].lower()
        
        return {
            'is_saas': any(w in description for w in ['saas', 'software as a service', 'cloud', 'platform']),
            'is_b2b': any(w in description for w in ['b2b', 'business', 'enterprise', 'corporate']),
            'is_enterprise': 'enterprise' in description,
            'has_api': 'api' in description
        }
    
    def _score_competitor(self, competitor_data: Dict) -> Tuple[float, Dict, bool]:
        """Score competitor with AI influence"""
        breakdown = {}
        
        # 1. AI Analysis
        ai_result = self.ai.compare_competitors(
            self.source_data['company']['description'],
            competitor_data['company']['description'],
            self.source_data['company']['name'],
            competitor_data['company']['name']
        )
        
        # AI Veto check
        if not ai_result['is_competitor'] and ai_result['score'] < self.config.THRESHOLD_AI_VETO:
            return 0, {'ai_analysis': ai_result}, False
        
        ai_points = (ai_result['score'] / 100) * self.config.WEIGHT_AI
        breakdown['ai_analysis'] = {
            'score': ai_result['score'],
            'points': round(ai_points, 1),
            'max': self.config.WEIGHT_AI,
            'reasoning': ai_result['reasoning']
        }
        
        # 2. Keyword Overlap
        target_keywords = self._extract_keywords(competitor_data['company']['description'])
        
        if self.source_keywords and target_keywords:
            source_set = set(self.source_keywords)
            target_set = set(target_keywords)
            overlap = len(source_set & target_set) / len(source_set | target_set) * 100
            keyword_points = min(overlap / 5, self.config.WEIGHT_KEYWORDS)
        else:
            overlap = 0
            keyword_points = 0
        
        breakdown['keyword_overlap'] = {
            'score': round(overlap, 1),
            'points': round(keyword_points, 1),
            'max': self.config.WEIGHT_KEYWORDS
        }
        
        # 3. Business Model
        target_model = self._analyze_business_model(competitor_data)
        matches = sum(1 for k in self.source_model if self.source_model[k] == target_model[k])
        model_score = (matches / len(self.source_model)) * 100
        model_points = (model_score / 100) * self.config.WEIGHT_MODEL
        
        breakdown['business_model'] = {
            'score': round(model_score, 1),
            'points': round(model_points, 1),
            'max': self.config.WEIGHT_MODEL
        }
        
        # 4. Social & Content (simplified)
        social_points = self.config.WEIGHT_SOCIAL * 0.5  # Placeholder
        content_points = self.config.WEIGHT_CONTENT * 0.5  # Placeholder
        
        breakdown['social_presence'] = {'points': round(social_points, 1), 'max': self.config.WEIGHT_SOCIAL}
        breakdown['content_quality'] = {'points': round(content_points, 1), 'max': self.config.WEIGHT_CONTENT}
        
        total_score = ai_points + keyword_points + model_points + social_points + content_points
        
        return total_score, breakdown, True
    
    def _build_results(self, context: Dict, target: int) -> Dict:
        """Build final results dictionary"""
        self.found_competitors.sort(key=lambda x: x['score'], reverse=True)
        
        tiers = {tier: sum(1 for c in self.found_competitors if c['score'] >= tier.value[1]) 
                for tier in CompetitorTier}
        
        avg_score = sum(c['score'] for c in self.found_competitors) / len(self.found_competitors) if self.found_competitors else 0
        
        stats = {
            'total_found': len(self.found_competitors),
            'direct': tiers[CompetitorTier.DIRECT],
            'strong': tiers[CompetitorTier.STRONG] - tiers[CompetitorTier.DIRECT],
            'moderate': tiers[CompetitorTier.MODERATE] - tiers[CompetitorTier.STRONG],
            'weak': len(self.found_competitors) - tiers[CompetitorTier.MODERATE],
            'average_score': avg_score,
            'ai_rejections': len(self.ai_rejections)
        }
        
        print(f"\n{'='*80}")
        print(f"✅ DISCOVERY COMPLETE")
        print(f"{'='*80}")
        print(f"   Total: {stats['total_found']} | Direct: {stats['direct']} | Strong: {stats['strong']}")
        print(f"   Average Score: {stats['average_score']:.1f}/100")
        print(f"   AI Rejections: {stats['ai_rejections']}")
        print(f"{'='*80}\n")
        
        return {
            'source_company': self.source_data['company']['name'],
            'analysis_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'context': context,
            'statistics': stats,
            'competitors': self.found_competitors,
            'ai_rejections': self.ai_rejections
        }


# ==================== MAIN ====================
def main():
    print("\n" + "="*80)
    print("🚀 INTELLIGENT COMPETITOR DISCOVERY SYSTEM v3.0")
    print("="*80)
    print("\nFeatures:")
    print("  ✓ AI-powered business context extraction")
    print("  ✓ Dynamic niche/sector detection")
    print("  ✓ Smart query generation")
    print("  ✓ Configurable scoring weights")
    print("  ✓ Improved company name extraction")
    print("  ✓ Environment-based configuration")
    print("="*80 + "\n")
    
    # Load configuration from environment
    try:
        config = Config.from_env()
        print("✅ Configuration loaded from environment variables\n")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease ensure your .env file contains:")
        print("  - GOOGLE_API_KEY")
        print("  - GOOGLE_CSE_ID")
        print("  - GROQ_API_KEY")
        print("  - RAPIDAPI_KEY")
        print("  - RAPIDAPI_HOST (optional, defaults to scrapeninja.p.rapidapi.com)")
        return
    
    # Load source data
    try:
        with open("travelperk_com_crawl_1759678430.json", 'r', encoding='utf-8') as f:
            company_data = json.load(f)
        print(f"✅ Loaded source data\n")
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    # Run discovery
    finder = CompetitorFinder(config)
    results = finder.discover(company_data, target=10)
    
    # Save results
    output_file = f"competitors_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Results saved: {output_file}\n")


if __name__ == "__main__":
    main()