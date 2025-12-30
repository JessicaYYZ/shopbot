"""
Stats API endpoints
"""
from flask import Blueprint, jsonify, current_app

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get system statistics
    
    Response JSON:
    {
        "success": true,
        "stats": {
            "products": 10,
            "embeddings": 10,
            "categories": 5
        }
    }
    """
    try:
        database = current_app.agent.database
        vector_store = current_app.agent.vector_store
        
        # Get product count
        product_count = database.count_products()
        
        # Get embedding count
        embedding_count = vector_store.get_embedding_count()
        
        # Get category count
        products = database.search_products()
        category_count = len(set(p.category for p in products))
        
        return jsonify({
            'success': True,
            'stats': {
                'products': product_count,
                'embeddings': embedding_count,
                'categories': category_count
            }
        })
    
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get stats',
            'message': str(e)
        }), 500

