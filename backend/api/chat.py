"""
Chat API endpoints
"""
import base64
from io import BytesIO
from flask import Blueprint, request, jsonify, current_app
from PIL import Image

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat messages with optional image and user profile
    
    Request JSON:
    {
        "message": "string (optional)",
        "image": "base64 string (optional)",
        "user_profile": {
            "id": "string",
            "name": "string",
            "gender": "string",
            "age": number,
            "interests": ["string"],
            "preferences": "string",
            "budget": "string",
            "style": "string"
        }
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        message = data.get('message', '')
        image_data = data.get('image', None)
        user_profile = data.get('user_profile', None)
        
        if not message and not image_data:
            return jsonify({
                'success': False,
                'error': 'Either message or image must be provided'
            }), 400
        
        # Process image if provided
        image = None
        if image_data:
            try:
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                
                image_bytes = base64.b64decode(image_data)
                image = Image.open(BytesIO(image_bytes))
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid image data: {str(e)}'
                }), 400
        
        agent = current_app.agent
        
        # Process with agent, including user profile for personalization
        if image:
            result = agent.process(message or "", image=image, user_profile=user_profile)
        else:
            result = agent.process(message, user_profile=user_profile)
        
        response_data = {
            'success': True,
            'response': result.response,
            'products': []
        }
        
        if result.products:
            for product in result.products:
                # Extract product_url from specifications if available
                product_url = ''
                if hasattr(product, 'specifications') and product.specifications:
                    product_url = product.specifications.get('Flipkart Link', '')
                
                product_dict = {
                    'id': product.id,
                    'title': product.title,
                    'price': product.price,
                    'rating': product.rating,
                    'review_count': product.review_count,
                    'category': product.category,
                    'brand': product.brand,
                    'image_path': product.image_path,
                    'description': product.description,
                    'tags': product.tags if hasattr(product, 'tags') else [],
                    'product_url': product_url,
                    'reviews': []
                }
                
                if hasattr(product, 'reviews') and product.reviews:
                    for review in product.reviews[:3]:
                        if isinstance(review, dict):
                            product_dict['reviews'].append(review)
                        elif hasattr(review, '__dict__'):
                            product_dict['reviews'].append({
                                'reviewer_name': review.reviewer_name,
                                'rating': review.rating,
                                'comment': review.comment,
                                'date': review.date,
                                'verified_purchase': review.verified_purchase,
                                'helpful_count': review.helpful_count
                            })
                
                response_data['products'].append(product_dict)
        
        return jsonify(response_data)
    
    except Exception as e:
        print(f"Error processing chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@chat_bp.route('/api/reset', methods=['POST'])
def reset():
    """Reset conversation history"""
    try:
        agent = current_app.agent
        agent.reset_conversation()
        
        return jsonify({
            'success': True,
            'message': 'Conversation reset successfully'
        })
    
    except Exception as e:
        print(f"Error resetting conversation: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to reset conversation',
            'message': str(e)
        }), 500
