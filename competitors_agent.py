import json
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from typing import Dict, List, Optional, Tuple
import time
from google import genai
from google.genai import types
from dataclasses import dataclass
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIGURATION ====================
@dataclass
class Config:
    """Centralized configuration"""
    GEMINI_API_KEY: str
    
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
        """Create Config from environment variables"""
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not gemini_api_key:
            raise ValueError("Missing environment variable: GEMINI_API_KEY")
        
        return cls(GEMINI_API_KEY=gemini_api_key)
    
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
    """Competitor tiers"""
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
    """AI operations using Google Gemini"""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        # Use Gemini 2.5 Flash Lite - better rate limits for free tier
        self.model = 'gemini-2.5-flash-lite'
        
        # Generation config for more deterministic responses
        self.generation_config = types.GenerateContentConfig(
            temperature=0.3,
            top_p=0.8,
            top_k=40,
            max_output_tokens=1024,
        )
    
    def _call_with_retry(self, prompt: str, config: types.GenerateContentConfig, max_retries: int = 3) -> str:
        """Call API with retry logic for rate limits"""
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )
                return response.text.strip()
            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    # Extract retry delay from error if available
                    import re
                    delay_match = re.search(r'retry in (\d+)', error_str)
                    delay = int(delay_match.group(1)) if delay_match else 20
                    
                    if attempt < max_retries - 1:
                        print(f"      ⏳ Rate limit hit, waiting {delay}s...", flush=True)
                        time.sleep(delay + 2)  # Add 2s buffer
                        continue
                raise e
        raise Exception("Max retries exceeded")
    
    def extract_business_context(self, company_data: Dict) -> Dict[str, str]:
        """Extract niche, sector, location from company data"""
        description = company_data.get('company', {}).get('description', '')
        name = company_data.get('company', {}).get('name', '')
        domain = company_data.get('domain', '')
        
        existing_niche = company_data.get('company', {}).get('niche')
        if existing_niche and len(existing_niche) > 3:
            print(f"   ℹ Using existing niche: {existing_niche}")
        
        evidence_snippets = [e.get('snippet', '') for e in company_data.get('evidence', [])[:5]]
        
        prompt = f"""Analyze this company:

Company: {name}
Domain: {domain}
Description: {description}

Context:
{chr(10).join(evidence_snippets[:3])}

Return ONLY valid JSON:
{{
  "niche": "specific market (e.g., 'corporate travel management', 'expense tracking')",
  "sector": "industry (e.g., 'SaaS', 'FinTech', 'Healthcare')",
  "location": "HQ location 'City, Country' or 'International'"
}}

Be specific. If unclear, guess based on context."""

        try:
            result_text = self._call_with_retry(prompt, self.generation_config)
            
            # Remove markdown code blocks if present
            result_text = re.sub(r'```json\s*|\s*```', '', result_text)
            json_match = re.search(r'\{[^{}]*\}', result_text)
            
            if json_match:
                result = json.loads(json_match.group())
                if existing_niche and len(existing_niche) > len(result.get('niche', '')):
                    result['niche'] = existing_niche
                return result
            
        except Exception as e:
            print(f"⚠️ AI extraction failed: {e}")
        
        return {
            "niche": existing_niche or self._extract_niche_fallback(description),
            "sector": company_data.get('company', {}).get('sector', 'Technology'),
            "location": "International"
        }
    
    def _extract_niche_fallback(self, description: str) -> str:
        """Fallback niche extraction"""
        desc_lower = description.lower()
        
        if 'travel' in desc_lower and 'corporate' in desc_lower:
            return 'corporate travel management'
        elif 'expense' in desc_lower:
            return 'expense management'
        elif 'crm' in desc_lower:
            return 'customer relationship management'
        elif 'hr' in desc_lower:
            return 'human resources software'
        
        return 'business software'
    
    def generate_search_queries(self, niche: str, sector: str) -> List[str]:
        """Generate search queries"""
        prompt = f"""Generate 8 search queries to find "{niche}" companies in "{sector}".

Requirements:
- Find actual company websites, not review sites
- Use product/solution language
- Include pricing/demo queries
- Keep concise (2-5 words)

Return ONLY queries, one per line, no numbering."""

        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.8,
                top_k=40,
                max_output_tokens=1024,
            )
            
            result_text = self._call_with_retry(prompt, config)
            
            queries = [q.strip().strip('"\'') for q in result_text.split('\n') if q.strip()]
            return queries[:8]
            
        except Exception as e:
            print(f"⚠️ Query generation failed: {e}")
            return [
                f'{niche} software',
                f'{niche} platform',
                f'{sector} {niche}',
                f'best {niche} tools',
                f'{niche} solution pricing',
                f'top {niche} companies',
                f'{niche} alternatives',
                f'{sector} software {niche}'
            ]
    
    def compare_competitors(self, source_desc: str, target_desc: str, source_name: str, target_name: str) -> Dict:
        """AI competitor analysis"""
        
        if not target_desc or len(target_desc) < 10:
            return {
                'score': 30,
                'is_competitor': False,
                'reasoning': 'Insufficient data to determine competitiveness'
            }
        
        prompt = f"""Compare these companies:

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

Return ONLY JSON (no markdown): {{"score": <int>, "is_competitor": <bool>, "reasoning": "<brief>"}}"""

        try:
            config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
                max_output_tokens=1024,
            )
            
            result_text = self._call_with_retry(prompt, config)
            
            # Remove markdown code blocks if present
            result_text = re.sub(r'```json\s*|\s*```', '', result_text)
            result_text = result_text.strip()
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[^{}]*\}', result_text)
            
            if json_match:
                result = json.loads(json_match.group())
                
                # Validate result has required fields
                if 'score' in result and 'reasoning' in result:
                    return {
                        'score': min(100, max(0, int(result.get('score', 50)))),
                        'is_competitor': bool(result.get('is_competitor', True)),
                        'reasoning': result.get('reasoning', 'Analysis completed')[:200]
                    }
            
            # If we couldn't parse JSON, return what we got
            print(f"      ⚠️ Could not parse AI response: {result_text[:100]}")
            return {
                'score': 50,
                'is_competitor': True,
                'reasoning': 'AI response parsing failed'
            }
            
        except Exception as e:
            print(f"⚠️ AI comparison failed: {e}")
            return {
                'score': 50,
                'is_competitor': True,
                'reasoning': f'AI error: {str(e)[:80]}'
            }


# ==================== COMPETITOR FINDER ====================
class CompetitorFinder:
    """Main competitor discovery engine - DuckDuckGo only"""
    
    def __init__(self, config: Config):
        self.config = config
        self.ai = AIService(config.GEMINI_API_KEY)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
        print(f"🚀 INTELLIGENT COMPETITOR DISCOVERY (DuckDuckGo + Gemini)")
        print(f"{'='*80}\n")
        
        self.source_data = company_data
        self.source_domain = company_data.get('domain', '').replace('www.', '').lower()
        
        source_name = company_data.get('company', {}).get('name', 'Unknown')
        if source_name == 'Unknown' or len(source_name) < 3:
            source_name = self.source_domain.split('.')[0].title()
        
        print(f"   🤖 Analyzing source company...", end=' ')
        context = self.ai.extract_business_context(company_data)
        print("✓")
        
        print(f"   Company: {source_name}")
        print(f"   Domain: {self.source_domain}")
        print(f"   Niche: {context['niche']}")
        print(f"   Sector: {context['sector']}")
        print(f"   Location: {context['location']}")
        print(f"   Target: {target} competitors\n")
        
        desc = company_data.get('company', {}).get('description', '')
        self.source_keywords = self._extract_keywords(desc)
        self.source_model = self._analyze_business_model(company_data)
        
        print(f"   🔍 Generating search queries...", end=' ')
        queries = self._prepare_queries(context, target)
        print(f"✓ {len(queries)} queries\n")
        print(f"{'─'*80}\n")
        
        for i, query_obj in enumerate(queries, 1):
            if len(self.found_competitors) >= target:
                break
            
            self._process_query(query_obj, i, len(queries), target)
            
            # Polite delay between searches
            if i < len(queries):
                time.sleep(2)
        
        return self._build_results(context, target, source_name)
    
    def _prepare_queries(self, context: Dict, target: int) -> List[Dict]:
        """Prepare search queries"""
        queries = self.ai.generate_search_queries(context['niche'], context['sector'])
        query_objects = [{'query': q, 'local': False} for q in queries]
        
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
        
        label = "🏠 LOCAL" if is_local else "🌐 INTL"
        print(f"🔎 {label} Query {index}/{total}: {query}")
        
        results = self._search_duckduckgo(query, is_local)
        print(f"   → {len(results)} results")
        
        if not results:
            print(f"   ⚠️ No results from DuckDuckGo\n")
            return
        
        print()
        
        for result in results:
            if len(self.found_competitors) >= target:
                break
            
            self._process_result(result)
    
    def _process_result(self, result: Dict):
        """Process a search result"""
        domain = result['domain']
        print(f"   🌐 {domain}")
        
        if not self._quick_filter(domain, result['url'], result['title'], result['snippet']):
            print()
            return
        
        print(f"      📡 Crawling...", end=' ', flush=True)
        data = self._extract_competitor_data(result)
        
        if not data:
            print("✗")
            print(f"      ❌ Failed to crawl\n")
            return
        
        print("✓")
        print(f"      ⚙️ {data['company']['name']}")
        
        print(f"      🎯 Scoring...", end=' ', flush=True)
        score, breakdown, accepted = self._score_competitor(data)
        print("✓")
        
        # Add small delay to avoid rate limits
        time.sleep(3)
        
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
        
        print(f"         • AI: {breakdown['ai_analysis']['points']:.1f}/{self.config.WEIGHT_AI}")
        print(f"         • Keywords: {breakdown['keyword_overlap']['points']:.1f}/{self.config.WEIGHT_KEYWORDS}")
        print(f"         • Model: {breakdown['business_model']['points']:.1f}/{self.config.WEIGHT_MODEL}")
        print(f"         • Social: {breakdown['social_presence']['points']:.1f}/{self.config.WEIGHT_SOCIAL}")
        print(f"         • Content: {breakdown['content_quality']['points']:.1f}/{self.config.WEIGHT_CONTENT}")
        
        if score >= self.config.THRESHOLD_MODERATE:
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
        """Quick filtering"""
        if domain == self.source_domain or self.source_domain in domain or domain in self.source_domain:
            print(f"      🚫 Source company")
            return False
        
        if any(blocked in domain for blocked in self.config.BLOCKED_DOMAINS):
            print(f"      ❌ Blocked domain")
            return False
        
        if domain in self.found_domains:
            print(f"      ⭕ Duplicate")
            return False
        
        bad_paths = ['/jobs/', '/careers/', '/blog/', '/article/', '/news/']
        if any(path in url.lower() for path in bad_paths):
            print(f"      ❌ Content page")
            return False
        
        print(f"      ✅ Passed")
        return True
    
    def _search_duckduckgo(self, query: str, local_only: bool = False) -> List[Dict]:
        """Search DuckDuckGo HTML (no API key needed)"""
        try:
            print(f"      → Searching DuckDuckGo...", end=' ', flush=True)
            
            # DuckDuckGo HTML search
            url = "https://html.duckduckgo.com/html/"
            params = {'q': query}
            
            response = self.session.post(url, data=params, timeout=15)
            
            if response.status_code != 200:
                print(f"✗ (HTTP {response.status_code})")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse search results
            for result in soup.select('.result'):
                title_elem = result.select_one('.result__a')
                snippet_elem = result.select_one('.result__snippet')
                
                if not title_elem:
                    continue
                
                result_url = title_elem.get('href', '')
                if not result_url or result_url.startswith('/'):
                    continue
                
                # Extract domain
                try:
                    domain = urllib.parse.urlparse(result_url).netloc.replace('www.', '')
                except:
                    continue
                
                if not domain:
                    continue
                
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'url': result_url,
                    'domain': domain,
                    'snippet': snippet_elem.get_text(strip=True) if snippet_elem else '',
                    'is_local_search': local_only
                })
                
                if len(results) >= 10:
                    break
            
            print(f"✓ ({len(results)})")
            return results
            
        except Exception as e:
            print(f"✗ ({e})")
            return []
    
    def _extract_competitor_data(self, result: Dict) -> Optional[Dict]:
        """Extract competitor data from crawled page"""
        html = self._crawl_url(result['url'])
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract name - prioritize domain-based extraction
        name = None
        
        # Try og:site_name first
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            candidate = og_site.get('content').strip()
            # Validate it's not a long title/description
            if len(candidate) < 50 and not any(word in candidate.lower() for word in ['what', 'how', 'why', 'everything', 'guide', 'learn']):
                name = candidate
        
        # Try title tag, but extract company name from end
        if not name:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Try splitting from the end (company names usually at end)
                for suffix in [' | ', ' - ', ' – ', ' — ', ' : ']:
                    if suffix in title:
                        parts = title.split(suffix)
                        # Take the last part (usually company name)
                        candidate = parts[-1].strip()
                        # Validate it's short and not a description
                        if len(candidate) < 50 and not any(word in candidate.lower() for word in ['what', 'how', 'why', 'everything', 'guide', 'learn', 'blog', 'article']):
                            name = candidate
                            break
        
        # Fallback to domain-based name
        if not name or len(name) < 2 or len(name) > 50:
            domain = result['domain']
            # Extract company name from domain
            domain_parts = domain.split('.')
            base = domain_parts[0]
            # Clean up common patterns
            base = base.replace('-', ' ').replace('_', ' ')
            # Capitalize properly
            name = ' '.join(word.capitalize() for word in base.split())
        
        name = name[:100]
        
        # Extract description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = ''
        if meta_desc:
            description = meta_desc.get('content', '').strip()
        else:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                description = og_desc.get('content', '').strip()
        
        if not description or len(description) < 20:
            paragraphs = soup.find_all('p', limit=5)
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:
                    description = text[:300]
                    break
        
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
        """Crawl URL (direct requests only, no RapidAPI)"""
        try:
            response = self.session.get(url, timeout=15, allow_redirects=True)
            if response.status_code == 200 and len(response.text) > 500:
                return response.text
        except Exception:
            pass
        
        return None
    
    def _extract_keywords(self, text: str, top_n: int = 25) -> List[str]:
        """Extract keywords from text"""
        if not text:
            return []
        
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]
        
        freq = {}
        for kw in keywords:
            freq[kw] = freq.get(kw, 0) + 1
        
        sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_kw[:top_n]]
    
    def _analyze_business_model(self, data: Dict) -> Dict:
        """Analyze business model"""
        description = data.get('company', {}).get('description', '').lower()
        
        return {
            'is_saas': any(w in description for w in ['saas', 'software as a service', 'cloud', 'platform']),
            'is_b2b': any(w in description for w in ['b2b', 'business', 'enterprise', 'corporate']),
            'is_enterprise': 'enterprise' in description,
            'has_api': 'api' in description
        }
    
    def _score_competitor(self, competitor_data: Dict) -> Tuple[float, Dict, bool]:
        """Score competitor using multi-factor analysis"""
        breakdown = {}
        
        # 1. AI Analysis
        ai_result = self.ai.compare_competitors(
            self.source_data.get('company', {}).get('description', ''),
            competitor_data['company']['description'],
            self.source_data.get('company', {}).get('name', 'Unknown'),
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
            'reasoning': ai_result['reasoning'],
            'is_competitor': ai_result['is_competitor']
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
        
        # 3. Business Model Match
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
        social_points = self.config.WEIGHT_SOCIAL * 0.5
        content_points = self.config.WEIGHT_CONTENT * 0.5
        
        breakdown['social_presence'] = {'points': round(social_points, 1), 'max': self.config.WEIGHT_SOCIAL}
        breakdown['content_quality'] = {'points': round(content_points, 1), 'max': self.config.WEIGHT_CONTENT}
        
        # Total score
        total_score = ai_points + keyword_points + model_points + social_points + content_points
        
        return total_score, breakdown, True
    
    def _build_results(self, context: Dict, target: int, source_name: str) -> Dict:
        """Build final results"""
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
            'source_company': source_name,
            'analysis_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'context': context,
            'statistics': stats,
            'competitors': self.found_competitors,
            'ai_rejections': self.ai_rejections
        }


# ==================== MAIN ====================
def main():
    print("\n" + "="*80)
    print("🚀 INTELLIGENT COMPETITOR DISCOVERY v4.0 (DuckDuckGo + Gemini)")
    print("="*80 + "\n")
    
    try:
        config = Config.from_env()
        print("✅ Configuration loaded (Using Google Gemini API)\n")
    except ValueError as e:
        print(f"❌ {e}")
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