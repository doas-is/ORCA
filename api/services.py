"""
Enhanced Service Layer with better error handling
"""
import sys
import os
import json
import logging
from typing import Dict, Optional
import traceback

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import crawler_core
from competitors_agent import CompetitorFinder, Config as CompetitorConfig

logger = logging.getLogger(__name__)


class CrawlerService:
    """Enhanced crawler service"""
    
    def analyze_url(self, url: str, max_pages: int = 30) -> Optional[Dict]:
        """Analyze URL with enhanced error handling"""
        try:
            logger.info(f"[CRAWLER] Starting crawl: {url} (max {max_pages} pages)")
            
            # Validate URL
            if not url or not url.startswith('http'):
                raise ValueError("Invalid URL format")
            
            # Run crawler
            result = crawler_core.crawl_domain(url, max_pages=max_pages, obey_robots=True)
            
            if not result:
                logger.error(f"Crawler returned no results for {url}")
                raise Exception("Crawler failed to fetch data")
            
            logger.info(f"[CRAWLER] Pages crawled: {result.get('pages_crawled', 0)}")
            logger.info(f"[CRAWLER] Company name: {result.get('company_name', 'Unknown')}")
            
            # Transform to API format
            company_data = self._transform_crawler_output(result)
            
            logger.info(f"[SUCCESS] Analysis complete for {company_data.get('domain')}")
            return company_data
            
        except Exception as e:
            logger.error(f"[ERROR] Crawler service failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _transform_crawler_output(self, crawler_result: Dict) -> Dict:
        """Transform crawler output to API format"""
        try:
            domain = crawler_result.get('domain', '')
            
            # Extract company name - NOW USES THE FIXED company_name FIELD
            company_name = crawler_result.get('company_name', 'Unknown')
            
            # Additional validation
            if not company_name or company_name == 'Unknown' or len(company_name) < 2:
                # Try from top titles
                if crawler_result.get('top_titles'):
                    first_title = crawler_result['top_titles'][0]
                    if first_title:
                        company_name = first_title.split('|')[0].split('-')[0].strip()
                
                # Last resort: domain
                if not company_name or len(company_name) < 2:
                    company_name = domain.split('.')[0].title()
            
            logger.info(f"[TRANSFORM] Company name: {company_name}")
            
            # Build description
            description_parts = []
            
            # Add niches
            if crawler_result.get('likely_niches'):
                niches = crawler_result['likely_niches'][:3]
                if niches:
                    description_parts.append(f"Specializes in {', '.join(niches)}")
            
            # Add meta descriptions from sample pages
            sample_pages = crawler_result.get('sample_pages', [])
            for page in sample_pages[:3]:
                meta_desc = page.get('meta_description')
                if meta_desc and len(meta_desc) > 30:
                    description_parts.append(meta_desc)
                    break
            
            # Add H1s if no meta description
            if not description_parts and crawler_result.get('top_h1s'):
                h1_text = ' '.join(crawler_result['top_h1s'][:2])
                if h1_text and len(h1_text) > 20:
                    description_parts.append(h1_text)
            
            description = '. '.join(description_parts)[:500] if description_parts else "Business services and solutions provider"
            
            logger.info(f"[TRANSFORM] Description length: {len(description)}")
            
            # Build evidence
            evidence = []
            for page in sample_pages[:5]:
                if page.get('snippet'):
                    evidence.append({
                        'url': page.get('url', ''),
                        'snippet': page.get('snippet', ''),
                        'title': page.get('title', '')
                    })
            
            # Detect sector
            niches_lower = [n.lower() for n in crawler_result.get('likely_niches', [])]
            desc_lower = description.lower()
            
            sector = "Technology"
            if any(term in niches_lower or term in desc_lower for term in ['saas', 'software', 'platform']):
                sector = "SaaS"
            elif any(term in niches_lower or term in desc_lower for term in ['fintech', 'financial', 'banking']):
                sector = "FinTech"
            elif any(term in niches_lower or term in desc_lower for term in ['health', 'medical', 'healthcare']):
                sector = "Healthcare"
            elif any(term in niches_lower or term in desc_lower for term in ['travel', 'booking']):
                sector = "Travel"
            
            # Determine niche
            niche = ', '.join(crawler_result.get('likely_niches', [])[:3]) if crawler_result.get('likely_niches') else 'Business Services'
            
            # Build final structure
            transformed_data = {
                'domain': domain,
                'start_url': crawler_result.get('start_url', ''),
                'company': {
                    'name': company_name,
                    'description': description,
                    'sector': sector,
                    'niche': niche
                },
                'evidence': evidence,
                'metadata': {
                    'pages_crawled': crawler_result.get('pages_crawled', 0),
                    'timestamp': crawler_result.get('timestamp', ''),
                    'partner_indicators': crawler_result.get('partner_indicators', []),
                    'client_indicators': crawler_result.get('client_indicators', [])
                },
                'social': {},
            }
            
            logger.info(f"[TRANSFORM] ✅ Successfully transformed data")
            logger.info(f"[TRANSFORM] Final: {company_name} | {sector} | {niche}")
            
            return transformed_data
            
        except Exception as e:
            logger.error(f"[ERROR] Transform failed: {e}")
            logger.error(traceback.format_exc())
            raise


class CompetitorService:
    """Enhanced competitor service"""
    
    def __init__(self):
        """Initialize with config validation"""
        try:
            logger.info("[INIT] Loading competitor configuration...")
            self.config = CompetitorConfig.from_env()
            logger.info("[INIT] ✅ Competitor service ready")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize: {e}")
            raise
    
    def discover(self, company_data: Dict, target: int = 10) -> Optional[Dict]:
        """Discover competitors with enhanced validation"""
        try:
            # Validate input
            logger.info("[DISCOVER] Validating company data...")
            self._validate_company_data(company_data)
            
            company_name = company_data.get('company', {}).get('name', 'Unknown')
            domain = company_data.get('domain', 'unknown')
            
            logger.info(f"[DISCOVER] Starting discovery for {company_name} ({domain})")
            logger.info(f"[DISCOVER] Target: {target} competitors")
            
            # Create finder
            logger.info("[DISCOVER] Initializing CompetitorFinder...")
            finder = CompetitorFinder(self.config)
            
            # Run discovery
            logger.info("[DISCOVER] Running competitor discovery...")
            results = finder.discover(company_data, target=target)
            
            if not results:
                raise Exception("Discovery returned no results")
            
            found = results.get('statistics', {}).get('total_found', 0)
            logger.info(f"[SUCCESS] ✅ Found {found} competitors")
            
            return results
            
        except Exception as e:
            logger.error(f"[ERROR] Competitor service failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _validate_company_data(self, company_data: Dict):
        """Validate company data structure"""
        
        if not isinstance(company_data, dict):
            raise ValueError("company_data must be a dictionary")
        
        # Check required top-level fields
        if 'domain' not in company_data:
            raise ValueError("Missing required field: domain")
        
        if 'company' not in company_data:
            raise ValueError("Missing required field: company")
        
        company = company_data['company']
        
        if not isinstance(company, dict):
            raise ValueError("company must be a dictionary")
        
        # Check required company fields
        if 'name' not in company or not company['name']:
            raise ValueError("Missing or empty company.name")
        
        if 'description' not in company or not company['description']:
            raise ValueError("Missing or empty company.description")
        
        # Validate description length
        if len(company['description']) < 20:
            logger.warning(f"⚠️ Short description ({len(company['description'])} chars)")
        
        logger.info("[VALIDATE] ✅ Company data is valid")
        logger.info(f"[VALIDATE] Name: {company['name']}")
        logger.info(f"[VALIDATE] Description: {len(company['description'])} chars")
        logger.info(f"[VALIDATE] Domain: {company_data['domain']}")