"""
Products API endpoints
"""
from flask import Blueprint, jsonify, request, current_app

products_bp = Blueprint('products', __name__)


@products_bp.route('/api/products', methods=['GET'])
def get_products():
    """
    Get all products with optional filtering
    
    Query Parameters:
    - category: Filter by category
    - min_price: Minimum price
    - max_price: Maximum price
    - limit: Number of products to return (default: 50)
    
    Response JSON:
    {
        "success": true,
        "products": [...],
        "count": 10
    }
    """
    try:
        # Get query parameters
        category = request.args.get('category')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        limit = request.args.get('limit', default=50, type=int)
        
        # Get database from app context
        database = current_app.agent.database
        
        # Build filters
        filters = {}
        if category:
            filters['category'] = category
        if min_price is not None:
            filters['min_price'] = min_price
        if max_price is not None:
            filters['max_price'] = max_price
        
        # Get products
        products = database.search_products(**filters)[:limit]
        
        # Format response
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'title': product.title,
                'price': product.price,
                'rating': product.rating,
                'review_count': product.review_count,
                'category': product.category,
                'image_path': product.image_path,
                'description': product.description,
                'features': product.features
            })
        
        return jsonify({
            'success': True,
            'products': products_data,
            'count': len(products_data)
        })
    
    except Exception as e:
        print(f"Error getting products: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get products',
            'message': str(e)
        }), 500


@products_bp.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    Get a single product by ID
    
    Response JSON:
    {
        "success": true,
        "product": {...}
    }
    """
    try:
        database = current_app.agent.database
        product = database.get_product(product_id)
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
        
        return jsonify({
            'success': True,
            'product': {
                'id': product.id,
                'title': product.title,
                'price': product.price,
                'rating': product.rating,
                'review_count': product.review_count,
                'category': product.category,
                'image_path': product.image_path,
                'description': product.description,
                'features': product.features
            }
        })
    
    except Exception as e:
        print(f"Error getting product: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get product',
            'message': str(e)
        }), 500


@products_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """
    Get all product categories
    
    Response JSON:
    {
        "success": true,
        "categories": [...]
    }
    """
    try:
        database = current_app.agent.database
        
        # Get all products and extract unique categories
        products = database.search_products()
        categories = list(set(p.category for p in products))
        categories.sort()
        
        return jsonify({
            'success': True,
            'categories': categories
        })
    
    except Exception as e:
        print(f"Error getting categories: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get categories',
            'message': str(e)
        }), 500

