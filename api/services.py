"""
Service Layer - Wraps Python agents for API use
"""
import sys
import os
import json
import logging
from typing import Dict, Optional
import traceback

# Add parent directory to path to import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path is set
import crawler_core
from competitors_agent import CompetitorFinder, Config as CompetitorConfig

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service wrapper for crawler_core.py"""
    
    def analyze_url(self, url: str, max_pages: int = 30) -> Optional[Dict]:
        """
        Analyze a URL using crawler_core
        
        Args:
            url: The URL to analyze
            max_pages: Maximum pages to crawl
            
        Returns:
            Dictionary with analysis results or None on failure
        """
        try:
            logger.info(f"[CRAWLER] Crawling {url} (max {max_pages} pages)")
            
            # Run crawler
            result = crawler_core.crawl_domain(url, max_pages=max_pages, obey_robots=True)
            
            if not result:
                logger.error(f"Crawler returned no results for {url}")
                return None
            
            logger.info(f"[CRAWLER] Raw result keys: {result.keys()}")
            
            # Transform crawler output to expected format
            company_data = self._transform_crawler_output(result)
            
            logger.info(f"[SUCCESS] Crawler analysis complete: {company_data.get('domain')}")
            logger.info(f"[CRAWLER] Transformed data keys: {company_data.keys()}")
            
            return company_data
            
        except Exception as e:
            logger.error(f"Error in crawler service: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _transform_crawler_output(self, crawler_result: Dict) -> Dict:
        """
        Transform crawler_core output to format expected by competitors_agent
        
        Args:
            crawler_result: Raw output from crawl_domain()
            
        Returns:
            Transformed data compatible with CompetitorFinder
        """
        try:
            domain = crawler_result.get('domain', '')
            
            # Extract company name from domain or top titles
            company_name = domain.split('.')[0].title()
            if crawler_result.get('top_titles'):
                # Try to extract cleaner name from first title
                first_title = crawler_result['top_titles'][0]
                if first_title and len(first_title) < 50:
                    company_name = first_title.split('|')[0].split('-')[0].strip()
            
            # Build description from available data
            description_parts = []
            
            # Add niche terms
            if crawler_result.get('likely_niches'):
                description_parts.append(f"Specializes in {', '.join(crawler_result['likely_niches'][:3])}")
            
            # Add H1s for context
            if crawler_result.get('top_h1s'):
                h1_text = ' '.join(crawler_result['top_h1s'][:3])
                if h1_text and len(h1_text) > 20:
                    description_parts.append(h1_text)
            
            # Add meta descriptions from sample pages
            sample_pages = crawler_result.get('sample_pages', [])
            for page in sample_pages[:3]:
                meta_desc = page.get('meta_description')
                if meta_desc and len(meta_desc) > 30:
                    description_parts.append(meta_desc)
                    break
            
            description = '. '.join(description_parts)[:500] if description_parts else "Business services provider"
            
            # Build evidence array from sample pages
            evidence = []
            for page in sample_pages[:5]:
                if page.get('snippet'):
                    evidence.append({
                        'url': page.get('url', ''),
                        'snippet': page.get('snippet', ''),
                        'title': page.get('title', '')
                    })
            
            # Detect sector
            sector = "Technology"
            niches_lower = [n.lower() for n in crawler_result.get('likely_niches', [])]
            if any(term in niches_lower for term in ['saas', 'software', 'platform']):
                sector = "SaaS"
            elif any(term in niches_lower for term in ['fintech', 'financial']):
                sector = "FinTech"
            elif any(term in niches_lower for term in ['health', 'medical']):
                sector = "Healthcare"
            
            # Build final structure - ENSURE all required fields are present
            transformed_data = {
                'domain': domain,
                'start_url': crawler_result.get('start_url', ''),
                'company': {
                    'name': company_name,
                    'description': description,
                    'sector': sector,
                    'niche': ', '.join(crawler_result.get('likely_niches', [])[:3]) if crawler_result.get('likely_niches') else 'Business Services'
                },
                'evidence': evidence,
                'metadata': {
                    'pages_crawled': crawler_result.get('pages_crawled', 0),
                    'timestamp': crawler_result.get('timestamp', ''),
                    'partner_indicators': crawler_result.get('partner_indicators', []),
                    'client_indicators': crawler_result.get('client_indicators', [])
                },
                'social': {},  # Could be populated from crawler if available
            }
            
            logger.info(f"[TRANSFORM] Successfully transformed data for {domain}")
            return transformed_data
            
        except Exception as e:
            logger.error(f"Error transforming crawler output: {e}")
            logger.error(traceback.format_exc())
            raise


class CompetitorService:
    """Service wrapper for competitors_agent.py"""
    
    def __init__(self):
        """Initialize competitor service with configuration"""
        try:
            logger.info("[INIT] Initializing CompetitorService...")
            self.config = CompetitorConfig.from_env()
            logger.info("[INIT] Competitor service initialized with env config")
        except Exception as e:
            logger.error(f"❌ Failed to initialize competitor config: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def discover(self, company_data: Dict, target: int = 10) -> Optional[Dict]:
        """
        Discover competitors using competitors_agent
        
        Args:
            company_data: Company data from crawler service
            target: Number of competitors to find
            
        Returns:
            Dictionary with competitor discovery results or None on failure
        """
        try:
            # Validate company_data structure
            logger.info(f"[DISCOVER] Validating company data...")
            self._validate_company_data(company_data)
            
            logger.info(f"[DISCOVER] Starting competitor discovery for {company_data.get('domain')}")
            logger.info(f"[DISCOVER] Company name: {company_data.get('company', {}).get('name')}")
            logger.info(f"[DISCOVER] Description length: {len(company_data.get('company', {}).get('description', ''))}")
            
            # Create finder instance - THIS IS WHERE THE ERROR LIKELY OCCURS
            logger.info(f"[DISCOVER] Creating CompetitorFinder instance...")
            try:
                finder = CompetitorFinder(self.config)
                logger.info(f"[DISCOVER] CompetitorFinder created successfully")
            except Exception as finder_error:
                logger.error(f"❌ Failed to create CompetitorFinder: {finder_error}")
                logger.error(f"❌ Full error: {traceback.format_exc()}")
                raise
            
            # Run discovery
            logger.info(f"[DISCOVER] Calling finder.discover()...")
            results = finder.discover(company_data, target=target)
            
            if not results:
                logger.error("Competitor finder returned no results")
                return None
            
            logger.info(f"[SUCCESS] Found {results['statistics']['total_found']} competitors")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in competitor service: {e}")
            logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
            # Re-raise to see full error in API response
            raise
    
    def _validate_company_data(self, company_data: Dict):
        """Validate company_data has all required fields"""
        required_fields = ['domain', 'company']
        missing = [f for f in required_fields if f not in company_data]
        
        if missing:
            raise ValueError(f"Missing required fields in company_data: {missing}")
        
        company = company_data.get('company', {})
        required_company_fields = ['name', 'description']
        missing_company = [f for f in required_company_fields if not company.get(f)]
        
        if missing_company:
            raise ValueError(f"Missing required company fields: {missing_company}")
        
        logger.info("[VALIDATE] ✅ Company data structure is valid")