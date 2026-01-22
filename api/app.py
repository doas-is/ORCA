"""
Flask API Server for ORCA
Main application entry point
"""
from flask import Flask
from flask_cors import CORS
from config import Config
from routes import api_bp
import logging
import sys
import io

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('api.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for frontend - Allow all origins during development
    CORS(app, 
         resources={r"/api/*": {"origins": "*"}},
         methods=["GET", "POST", "OPTIONS"],
         allow_headers=["Content-Type"],
         supports_credentials=False)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'ORCA API'}, 200
    
    logger.info("ORCA API Server initialized successfully")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )