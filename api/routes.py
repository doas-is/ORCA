"""
API Routes for ORCA
Handles all endpoint logic
"""
from flask import Blueprint, request, jsonify
from services import CrawlerService, CompetitorService
import logging
import traceback

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

# Service instances
crawler_service = CrawlerService()
competitor_service = CompetitorService()

# Explicit OPTIONS handlers for preflight requests
@api_bp.route('/analyze-url', methods=['OPTIONS'])
def analyze_url_options():
    """Handle preflight request for analyze-url"""
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
    return response, 204

@api_bp.route('/discover-competitors', methods=['OPTIONS'])
def discover_competitors_options():
    """Handle preflight request for discover-competitors"""
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
    return response, 204

@api_bp.route('/analyze-url', methods=['POST'])
def analyze_url():
    """
    Analyze a company URL using crawler_core.py
    
    Request body:
    {
        "url": "https://example.com",
        "max_pages": 30  // optional
    }
    
    Response:
    {
        "success": true,
        "data": {
            "domain": "example.com",
            "company": {
                "name": "Example Inc",
                "description": "...",
                "niche": "...",
                "sector": "..."
            },
            ...
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        url = data['url']
        max_pages = data.get('max_pages', 30)
        
        logger.info(f"[ANALYZE] Starting URL analysis: {url}")
        
        # Run crawler
        result = crawler_service.analyze_url(url, max_pages)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to analyze URL. Please check the URL and try again.'
            }), 500
        
        logger.info(f"✅ Analysis complete for {url}")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in analyze_url: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/discover-competitors', methods=['POST'])
def discover_competitors():
    """
    Discover competitors using competitors_agent.py
    
    Request body:
    {
        "company_data": {
            "domain": "example.com",
            "company": {...},
            ...
        },
        "target": 10  // optional, number of competitors to find
    }
    
    Response:
    {
        "success": true,
        "data": {
            "source_company": "Example Inc",
            "context": {...},
            "statistics": {...},
            "competitors": [...]
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'company_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Company data is required'
            }), 400
        
        company_data = data['company_data']
        target = data.get('target', 10)
        
        logger.info(f"🔍 Starting competitor discovery for {company_data.get('domain', 'unknown')}")
        
        # Run competitor discovery
        result = competitor_service.discover(company_data, target)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to discover competitors. Please try again.'
            }), 500
        
        logger.info(f"✅ Discovered {result['statistics']['total_found']} competitors")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in discover_competitors: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """
    Check status of long-running task (optional, for future use)
    """
    # Placeholder for future implementation with task queue
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': 'processing',
        'progress': 50
    }), 200


@api_bp.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@api_bp.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500