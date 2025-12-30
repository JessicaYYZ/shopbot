"""
Query processing and intent classification - Optimized for Flipkart catalog
"""

import re
import json
from typing import Dict, Optional, List, Any
from ..models.openai_client import OpenAIClient

# Flipkart catalog categories for better matching
MAIN_CATEGORIES = [
    'clothing', 'jewellery', 'jewelry', 'automotive', 'footwear', 'home decor',
    'beauty', 'personal care', 'kitchen', 'dining', 'computers', 'watches',
    'mobiles', 'mobile accessories', 'home furnishing', 'toys', 'baby care',
    'bags', 'wallets', 'belts', 'tools', 'sports', 'fitness', 'furniture',
    'cameras', 'electronics'
]

SUB_CATEGORIES = [
    "women's clothing", "men's clothing", "kids' clothing", "accessories",
    "necklaces", "chains", "rings", "wrist watches", "bangles", "bracelets",
    "fragrances", "perfume", "laptop accessories", "mobile accessories",
    "coffee mugs", "showpieces", "bed linen", "curtains", "footwear",
    "shoes", "sandals", "heels", "sneakers", "formal shoes"
]


class IntentClassifier:
    """Classifies user intent using OpenAI API"""
    
    def __init__(self, openai_client: OpenAIClient):
        self.openai = openai_client
    
    def classify(self, query: str, has_image: bool = False) -> str:
        """Classify user intent"""
        if has_image:
            return "product_search"
        
        messages = [{
            "role": "system",
            "content": "You are an intent classifier for an e-commerce assistant. Respond with exactly one word."
        }, {
            "role": "user",
            "content": f"""Classify: "{query}"

Reply ONE of:
- 'scenario_shopping' if user asks for products for an EVENT, ACTIVITY, OCCASION, or USE CASE (e.g., "going camping", "preparing for a wedding", "beach vacation essentials", "gym starter kit", "home office setup")
- 'product_search' if user wants to find/buy a SPECIFIC product type (e.g., "blue running shoes", "leather wallet", "gold necklace")
- 'general_conversation' for greetings, questions about the assistant, or non-shopping queries"""
        }]
        
        response = self.openai.generate_text(messages, max_tokens=10)
        response_lower = response.lower().strip()
        if "scenario" in response_lower:
            return "scenario_shopping"
        if "general" in response_lower:
            return "general_conversation"
        return "product_search"


class FollowUpAnalyzer:
    """Analyzes follow-up queries to determine if they refine previous search or start new one"""
    
    def __init__(self, openai_client: OpenAIClient):
        self.openai = openai_client
        
        # Keywords indicating refinement/filtering
        self.refinement_indicators = [
            'cheaper', 'expensive', 'under', 'below', 'different color', 'another',
            'more', 'less', 'other', 'instead', 'better', 'similar', 'alternative',
            'formal', 'casual', 'brand', 'size', 'discount', 'deal', 'offer',
            'blue', 'red', 'black', 'white',  # colors suggest filtering
            'leather', 'cotton', 'silk',  # materials suggest filtering
        ]
        
        # Keywords indicating product discussion
        self.discussion_indicators = [
            'first one', 'second one', 'third one', 'last one', 'this one', 'that one',
            'tell me more', 'about the', 'describe', 'details', 'review', 'rating',
            'which is better', 'compare', 'difference between', 'recommend', 'opinion'
        ]
        
        # Keywords indicating new search
        self.new_search_indicators = [
            'now show', 'instead show', 'search for', 'find me', 'i want',
            'looking for', 'need to buy', 'show me', 'get me'
        ]
    
    def analyze(self, current_query: str, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze if current query is:
        - new_search: Completely new product request
        - refine_search: Filter/modify previous search results
        - product_discussion: Questions about shown products
        - general_chat: Non-product conversation
        """
        if not conversation_context.get("has_history"):
            return {
                "action": "new_search",
                "confidence": "high",
                "reasoning": "No conversation history"
            }
        
        query_lower = current_query.lower()
        last_search = conversation_context.get("last_search_query", "")
        last_products = conversation_context.get("last_products_shown", [])
        
        # Quick pattern matching for obvious cases
        if any(indicator in query_lower for indicator in self.discussion_indicators):
            if last_products:
                return {
                    "action": "product_discussion",
                    "confidence": "high",
                    "reasoning": "User asking about specific products from previous results"
                }
        
        # Check if query is very short (likely a refinement)
        if len(current_query.split()) <= 4 and last_products:
            if any(indicator in query_lower for indicator in self.refinement_indicators):
                return {
                    "action": "refine_search",
                    "confidence": "high",
                    "reasoning": "Short query with refinement keywords and active product context"
                }
        
        # Use LLM for complex decision making
        return self._llm_analyze_followup(current_query, conversation_context)
    
    def _llm_analyze_followup(self, current_query: str, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to analyze follow-up intent"""
        last_search = conversation_context.get("last_search_query", "None")
        recent_turns = conversation_context.get("recent_turns", [])
        last_products = conversation_context.get("last_products_shown", [])
        
        # Format recent conversation
        conversation_summary = []
        for turn in recent_turns[-2:]:
            conversation_summary.append(f"User: {turn['user']}")
            if turn['has_products']:
                conversation_summary.append(f"Assistant: [Showed {turn['num_products']} products]")
        
        context_str = "\n".join(conversation_summary) if conversation_summary else "No recent conversation"
        
        # Format last products
        products_str = ""
        if last_products:
            products_str = "Products currently shown:\n"
            for i, p in enumerate(last_products, 1):
                products_str += f"{i}. {p['title'][:60]} - ₹{p['price']:,.0f}\n"
        
        messages = [{
            "role": "system",
            "content": """You are an expert at understanding user intent in shopping conversations.
Analyze if the user's current message is:
- new_search: Asking for completely different products (different category/type)
- refine_search: Adding filters/requirements to previous search (price, color, style, etc.)
- product_discussion: Asking questions about already shown products
- general_chat: Unrelated to shopping

Return ONLY valid JSON with this structure:
{
    "action": "new_search|refine_search|product_discussion|general_chat",
    "confidence": "high|medium|low",
    "reasoning": "brief explanation"
}"""
        }, {
            "role": "user",
            "content": f"""Recent conversation:
{context_str}

Last search query: "{last_search}"

{products_str}

Current user message: "{current_query}"

What should we do? JSON only:"""
        }]
        
        try:
            response = self.openai.generate_text(messages, max_tokens=150, temperature=0.2)
            # Clean response
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            result = json.loads(response)
            return result
        except Exception as e:
            # Fallback to new_search on error
            return {
                "action": "new_search",
                "confidence": "low",
                "reasoning": f"Error in analysis: {str(e)}"
            }


class QueryProcessor:
    """Extract entities from product search queries - optimized for Flipkart catalog"""
    
    def __init__(self, openai_client: OpenAIClient):
        self.openai = openai_client
        
        # Common colors for quick extraction
        self.colors = [
            'red', 'blue', 'green', 'black', 'white', 'yellow', 'pink', 'purple',
            'orange', 'brown', 'grey', 'gray', 'gold', 'silver', 'beige', 'navy',
            'maroon', 'cream', 'multicolor', 'multi-color'
        ]
        
        # Common materials/fabrics
        self.materials = [
            'cotton', 'silk', 'leather', 'denim', 'polyester', 'wool', 'linen',
            'synthetic', 'metal', 'gold', 'silver', 'platinum', 'stainless steel'
        ]
    
    def refine_entities(self, new_query: str, base_entities: Dict, base_query: str) -> Dict:
        """Refine existing search entities with new constraints from follow-up query"""
        # Extract entities from new query
        new_entities = self.extract_entities(new_query)
        
        # Start with base entities (handle None case)
        refined = (base_entities or {}).copy()
        
        # Override with new constraints where specified
        for key, value in new_entities.items():
            if value is not None:
                refined[key] = value
        
        # Handle special refinement cases
        new_query_lower = new_query.lower()
        
        # Price refinements
        if any(word in new_query_lower for word in ['cheaper', 'less expensive', 'lower price']):
            if refined.get("price_max"):
                # Reduce max price by 20%
                refined["price_max"] = refined["price_max"] * 0.8
            elif refined.get("price_min"):
                # If only min was set, set max to current min
                refined["price_max"] = refined["price_min"]
                refined["price_min"] = refined["price_min"] * 0.5
        
        if any(word in new_query_lower for word in ['expensive', 'premium', 'luxury']):
            if refined.get("price_min"):
                # Increase min price by 50%
                refined["price_min"] = refined["price_min"] * 1.5
            refined["features"] = refined.get("features", []) + ["premium", "luxury"]
        
        # Style refinements
        style_keywords = {
            'formal': ['formal', 'professional', 'office', 'business'],
            'casual': ['casual', 'everyday', 'regular', 'comfortable'],
            'party': ['party', 'evening', 'festive', 'celebration'],
            'sporty': ['sport', 'athletic', 'gym', 'fitness', 'active']
        }
        
        for style, keywords in style_keywords.items():
            if any(kw in new_query_lower for kw in keywords):
                refined["features"] = refined.get("features", []) + [style]
        
        return refined
    
    def extract_entities(self, query: str) -> Dict:
        """Extract category, price, brand, features, etc."""
        entities = {
            "category": None,
            "price_min": None,
            "price_max": None,
            "brand": None,
            "features": [],
            "color": None,
            "material": None,
            "gender": None
        }
        
        query_lower = query.lower()
        
        # Extract price information (supports both $ and ₹)
        price_patterns = [
            (r"under [₹$]?(\d+(?:,\d+)*)", "max"),
            (r"below [₹$]?(\d+(?:,\d+)*)", "max"),
            (r"less than [₹$]?(\d+(?:,\d+)*)", "max"),
            (r"within [₹$]?(\d+(?:,\d+)*)", "max"),
            (r"budget [₹$]?(\d+(?:,\d+)*)", "max"),
            (r"between [₹$]?(\d+(?:,\d+)*) (?:and|to|-) [₹$]?(\d+(?:,\d+)*)", "range"),
            (r"[₹$](\d+(?:,\d+)*)\s*(?:to|-)\s*[₹$]?(\d+(?:,\d+)*)", "range")
        ]
        
        for pattern, price_type in price_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if price_type == "max":
                    price_str = match.group(1).replace(',', '')
                    entities["price_max"] = float(price_str)
                elif price_type == "range":
                    entities["price_min"] = float(match.group(1).replace(',', ''))
                    entities["price_max"] = float(match.group(2).replace(',', ''))
                break
        
        # Quick extraction for common attributes
        # Gender
        if any(w in query_lower for w in ["women's", "women", "ladies", "female", "girl"]):
            entities["gender"] = "women"
        elif any(w in query_lower for w in ["men's", "men", "male", "boy", "gents"]):
            entities["gender"] = "men"
        elif any(w in query_lower for w in ["kids", "children", "baby"]):
            entities["gender"] = "kids"
        
        # Color
        for color in self.colors:
            if color in query_lower:
                entities["color"] = color
                break
        
        # Material
        for material in self.materials:
            if material in query_lower:
                entities["material"] = material
                break
        
        # Category detection from keywords
        entities["category"] = self._detect_category(query_lower)
        
        # Use LLM for complex entity extraction only if needed
        if not entities["category"] or not entities.get("features"):
            llm_entities = self._llm_extract_entities(query)
            # Only update None values
            for key, value in llm_entities.items():
                if entities.get(key) is None and value is not None:
                    entities[key] = value
        
        return entities
    
    def _detect_category(self, query: str) -> Optional[str]:
        """Fast category detection from query keywords"""
        category_keywords = {
            "clothing": ["shirt", "dress", "jeans", "pants", "top", "kurta", "saree", "t-shirt", "jacket", "sweater"],
            "jewellery": ["necklace", "ring", "earring", "bracelet", "bangle", "pendant", "chain", "anklet"],
            "footwear": ["shoes", "sandals", "heels", "sneakers", "boots", "slippers", "flats"],
            "watches": ["watch", "smartwatch", "wrist watch"],
            "bags": ["bag", "handbag", "backpack", "purse", "wallet", "clutch"],
            "electronics": ["laptop", "phone", "mobile", "tablet", "headphones", "earbuds", "speaker"],
            "beauty": ["makeup", "lipstick", "foundation", "skincare", "perfume", "fragrance"],
            "home": ["furniture", "sofa", "bed", "table", "chair", "decor", "curtain", "bedsheet"]
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in query for kw in keywords):
                return category
        return None
    
    def _llm_extract_entities(self, query: str) -> Dict:
        """Use LLM to extract entities for complex queries"""
        messages = [{
            "role": "user",
            "content": f"""Extract product search parameters from this query:
Query: "{query}"

Our catalog includes: Clothing, Jewellery, Footwear, Watches, Electronics, Beauty, Home Decor, Kitchen, Sports, Toys.

Extract and return ONLY valid JSON with these fields (use null if not found):
{{
    "category": "product category from our catalog",
    "brand": "brand name if mentioned",
    "features": ["feature1", "feature2"],
    "color": "color if mentioned",
    "occasion": "casual/formal/party/wedding if mentioned"
}}

JSON only, no other text:"""
        }]
        
        try:
            response = self.openai.generate_text(messages, max_tokens=150)
            # Clean response and parse JSON
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            return json.loads(response)
        except:
            return {}


class ScenarioShoppingProcessor:
    """Processes scenario-based shopping requests (e.g., 'going camping', 'wedding preparation')"""
    
    def __init__(self, openai_client: OpenAIClient):
        self.openai = openai_client
    
    def analyze_scenario(self, query: str, user_profile: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze scenario and return list of exactly 5 product categories needed"""
        gender_hint = ""
        if user_profile and user_profile.get('gender'):
            gender_hint = f"\nUser gender: {user_profile['gender']} - tailor product categories accordingly."
        
        messages = [{
            "role": "system",
            "content": f"""You are an expert shopping advisor. Given a scenario/occasion/activity, identify essential product categories.{gender_hint}

STRICT RULES:
1. Return EXACTLY 5 categories - no more, no less
2. Each category must be DIRECTLY RELEVANT and USEFUL for the user's specific scenario
3. Categories must be DISTINCT and serve DIFFERENT purposes (e.g., footwear, bag, top, accessory, grooming)
4. NEVER include similar items (e.g., "shoes" and "boots" are too similar - pick one)
5. Each category should be a specific, searchable product type

Return JSON:
{{"scenario_name": "brief name", "categories": ["category1", "category2", "category3", "category4", "category5"]}}"""
        }, {
            "role": "user",
            "content": f"""Scenario: "{query}"

Return EXACTLY 5 distinct product categories as JSON. No explanation, JSON only."""
        }]
        
        try:
            response = self.openai.generate_text(messages, max_tokens=300, temperature=0.3)
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            result = json.loads(response)
            # Limit to 5 categories
            if 'categories' in result:
                result['categories'] = result['categories'][:5]
            return result
        except Exception as e:
            return {"scenario_name": "Shopping", "categories": [], "error": str(e)}
    
    def parse_refinement_request(self, query: str, current_items: List[Dict]) -> Dict[str, Any]:
        """Parse user's refinement request to identify which items to replace and new requirements"""
        items_summary = "\n".join([f"{i+1}. {item['category']}: {item['product_title'][:50]}" 
                                   for i, item in enumerate(current_items)])
        
        messages = [{
            "role": "system",
            "content": """You analyze refinement requests for scenario shopping. 
The user has a list of recommended products and wants to change some of them.
Identify which items (by number or category) need replacement and the new requirements."""
        }, {
            "role": "user",
            "content": f"""Current recommendations:
{items_summary}

User request: "{query}"

Return JSON:
{{
    "items_to_replace": [list of 1-based item numbers to replace],
    "new_requirements": {{"item_number": "new requirement description"}}
}}

If user refers to items by category name, map to the correct number. JSON only:"""
        }]
        
        try:
            response = self.openai.generate_text(messages, max_tokens=200, temperature=0.2)
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            return json.loads(response)
        except:
            return {"items_to_replace": [], "new_requirements": {}}

