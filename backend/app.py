"""
Flask REST API for ShopBot - Backend Only
Serves as API backend for React frontend
"""
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Import backend components
from src.models.openai_client import OpenAIClient
from src.models.vector_store import VectorStore
from src.data.database import Database
from src.core.agent import ShoppingAgent
from backend.api.chat import chat_bp
from backend.api.products import products_bp
from backend.api.stats import stats_bp

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure CORS - Allow React frontend to access API
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration - Default to Flipkart database
app.config['DATABASE_PATH'] = os.getenv("DATABASE_PATH", "data/flipkart_products.db")
app.config['VECTOR_STORE_PATH'] = os.getenv("VECTOR_STORE_PATH", "vector_store_flipkart/")
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY",
                                     "dev-secret-key-change-in-production")
print(f"Database path: {app.config['DATABASE_PATH']}")

# Initialize components
print("\n🔧 Initializing ShopBot Backend API...")

openai_client = OpenAIClient()
vector_store = VectorStore(app.config['VECTOR_STORE_PATH'])
database = Database(app.config['DATABASE_PATH'])

# Check for embeddings
embedding_count = vector_store.get_embedding_count()
product_count = database.count_products()

if embedding_count == 0:
    print("\n⚠️  Warning: No embeddings found")
    print("Run: python scripts/generate_embeddings.py\n")

print(f"✅ Found {product_count} products")
print(f"✅ Found {embedding_count} embeddings\n")

# Initialize agent (make it accessible to blueprints)
app.agent = ShoppingAgent(openai_client, vector_store, database)

# Register blueprints
app.register_blueprint(chat_bp)
app.register_blueprint(products_bp)
app.register_blueprint(stats_bp)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ShopBot API',
        'version': '1.0.0'
    })


@app.route('/')
def index():
    """API info endpoint"""
    return jsonify({
        'message': 'ShopBot REST API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/health',
            'chat': '/api/chat',
            'reset': '/api/reset',
            'stats': '/api/stats',
            'products': '/api/products',
        },
        'frontend': 'http://localhost:3000',
        'docs': 'See README.md for API documentation'
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == "__main__":
    # Check if database exists
    if not os.path.exists(app.config['DATABASE_PATH']):
        print(f"❌ Database not found at {app.config['DATABASE_PATH']}")
        print("Please run: python scripts/setup_db.py")
        exit(1)

    print("🚀 Starting ShopBot REST API Server...")
    print("📍 API available at: http://localhost:5001")
    print("📍 Frontend should run at: http://localhost:3000")
    print("📖 API Docs: http://localhost:5001/\n")

    app.run(
        host='0.0.0.0',
        port=5001,
        debug=os.getenv("FLASK_DEBUG", "False").lower() == "true"
    )
