"""
Main Shopping Agent Orchestrator
"""

from typing import Optional, Dict, Any
from PIL import Image
from datetime import datetime

from ..models.openai_client import OpenAIClient
from ..models.vector_store import VectorStore
from ..data.database import Database
from ..data.schemas import AgentResponse, ConversationTurn
from .query_processor import IntentClassifier, QueryProcessor, FollowUpAnalyzer, ScenarioShoppingProcessor
from .search_engine import SearchEngine
from .response_generator import ResponseGenerator


class ConversationManager:
    """Manages conversation history and context"""
    
    def __init__(self, max_history: int = 10):
        self.history = []
        self.max_history = max_history
        self.last_search_query = None
        self.last_search_entities = None
        # Image search context - preserved for follow-ups
        self.last_search_type = None  # "text", "image", or "hybrid"
        self.last_image_description = None  # Product description from image analysis
        # Scenario shopping state
        self.scenario_active = False
        self.scenario_name = None
        self.scenario_categories = []
        self.scenario_items = []  # List of {category, product, product_title, product_id}
    
    def add_turn(self, user_input: str, agent_response: str, products=None, 
                 search_query=None, entities=None, search_type=None, image_description=None):
        """Add conversation turn with optional search context"""
        turn = ConversationTurn(
            user_input=user_input,
            agent_response=agent_response,
            products=products or [],
            timestamp=datetime.now()
        )
        self.history.append(turn)
        
        # Track last search context for follow-ups
        if products and len(products) > 0:
            self.last_search_query = search_query or user_input
            self.last_search_entities = entities
            if search_type:
                self.last_search_type = search_type
            if image_description:
                self.last_image_description = image_description
        
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def set_scenario(self, scenario_name: str, categories: list, items: list):
        """Set active scenario shopping state"""
        self.scenario_active = True
        self.scenario_name = scenario_name
        self.scenario_categories = categories
        self.scenario_items = items
    
    def update_scenario_item(self, index: int, new_item: dict):
        """Update a specific item in the scenario"""
        if 0 <= index < len(self.scenario_items):
            self.scenario_items[index] = new_item
    
    def clear_scenario(self):
        """Clear scenario shopping state"""
        self.scenario_active = False
        self.scenario_name = None
        self.scenario_categories = []
        self.scenario_items = []
    
    def get_context(self) -> str:
        """Return formatted conversation history"""
        if not self.history:
            return ""
        
        context_lines = []
        for turn in self.history[-3:]:
            context_lines.append(f"User: {turn.user_input}")
            context_lines.append(f"Assistant: {turn.agent_response[:100]}...")
        
        return "\n".join(context_lines)
    
    def get_structured_context(self) -> Dict[str, Any]:
        """Return structured conversation context for decision making"""
        if not self.history:
            return {
                "has_history": False,
                "recent_turns": [],
                "last_search_query": None,
                "last_search_entities": None,
                "last_search_type": None,
                "last_image_description": None,
                "last_products_shown": [],
                "scenario_active": False,
                "scenario_items": []
            }
        
        recent_turns = []
        for turn in self.history[-3:]:
            recent_turns.append({
                "user": turn.user_input,
                "assistant": turn.agent_response[:150],
                "has_products": len(turn.products) > 0,
                "num_products": len(turn.products)
            })
        
        last_products = []
        for turn in reversed(self.history):
            if turn.products and len(turn.products) > 0:
                last_products = [{"title": p.title, "price": p.price, "category": p.category} 
                               for p in turn.products[:3]]
                break
        
        return {
            "has_history": True,
            "recent_turns": recent_turns,
            "last_search_query": self.last_search_query,
            "last_search_entities": self.last_search_entities,
            "last_search_type": self.last_search_type,
            "last_image_description": self.last_image_description,
            "last_products_shown": last_products,
            "scenario_active": self.scenario_active,
            "scenario_name": self.scenario_name,
            "scenario_items": self.scenario_items
        }
    
    def clear(self):
        """Clear conversation history"""
        self.history = []
        self.last_search_query = None
        self.last_search_entities = None
        self.last_search_type = None
        self.last_image_description = None
        self.clear_scenario()


class ShoppingAgent:
    """
    Main agent that handles all three use cases:
    1. General conversation
    2. Text-based product recommendation
    3. Image-based product search
    """
    
    def __init__(self, openai_client: OpenAIClient, vector_store: VectorStore, 
                 database: Database):
        self.openai = openai_client
        self.vector_store = vector_store
        self.database = database
        
        self.intent_classifier = IntentClassifier(openai_client)
        self.query_processor = QueryProcessor(openai_client)
        self.followup_analyzer = FollowUpAnalyzer(openai_client)
        self.scenario_processor = ScenarioShoppingProcessor(openai_client)
        self.search_engine = SearchEngine(openai_client, vector_store, database)
        self.response_generator = ResponseGenerator(openai_client)
        self.conversation_manager = ConversationManager()
    
    def _format_user_context(self, user_profile: Optional[Dict[str, Any]]) -> str:
        """Format user profile into context string for AI personalization"""
        if not user_profile:
            return ""
        
        interests = user_profile.get('interests', [])
        interests_str = ', '.join(interests) if interests else 'general shopping'
        
        return f"""User Profile:
- Name: {user_profile.get('name', 'Guest')}
- Gender: {user_profile.get('gender', 'unknown')} [ENFORCE for fashion/apparel categories]
- Age: {user_profile.get('age', 'unknown')}
- Interests: {interests_str} [use as preference/suggestion only]
- Style Preferences: {user_profile.get('preferences', 'no specific preferences')}
- Budget Level: {user_profile.get('budget', 'flexible')}
- Personal Style: {user_profile.get('style', 'casual')}

IMPORTANT: Always prioritize what the user explicitly asks for in their query. Gender MUST be enforced for fashion/apparel/accessories categories - never show opposite gender items. Interests are suggestions to personalize tone or break ties between similar products, but never override the requested product category."""
    
    def _is_product_conversation_active(self) -> bool:
        """Check if recent conversation turns involved product searches."""
        if not self.conversation_manager.history:
            return False
        for turn in self.conversation_manager.history[-3:]:
            if turn.products and len(turn.products) > 0:
                return True
        return False
    
    def _enhance_query_with_profile(self, query: str, user_profile: Optional[Dict[str, Any]]) -> str:
        """Enhance search query with user profile context for better matching.
        Gender is enforced for relevant categories. Interests are treated as preferences."""
        if not user_profile:
            return query
        
        gender = user_profile.get('gender', '')
        query_lower = query.lower()
        
        # Expanded categories that benefit from gender/demographic context
        gender_relevant_keywords = [
            # Clothing & Apparel
            'fashion', 'clothes', 'wear', 'outfit', 'dress', 'clothing', 'apparel',
            'shirt', 'top', 'blouse', 'tshirt', 't-shirt', 'polo', 'sweater', 'jacket',
            'coat', 'blazer', 'hoodie', 'cardigan', 'vest', 'tank',
            'pants', 'jeans', 'trousers', 'shorts', 'skirt', 'leggings',
            'kurta', 'kurti', 'saree', 'sari', 'salwar', 'lehenga', 'sherwani', 'ethnic',
            'suit', 'formal', 'casual', 'party', 'wedding', 'festive', 'traditional',
            # Footwear
            'shoes', 'footwear', 'sneakers', 'sandals', 'heels', 'boots', 'loafers',
            'flats', 'slippers', 'flip flops', 'trainers', 'sports shoes', 'formal shoes',
            # Accessories
            'jewellery', 'jewelry', 'necklace', 'earring', 'bracelet', 'ring', 'pendant',
            'chain', 'bangle', 'anklet', 'watch', 'watches', 'smartwatch',
            'bag', 'bags', 'handbag', 'purse', 'clutch', 'wallet', 'backpack', 'tote',
            'belt', 'tie', 'scarf', 'hat', 'cap', 'sunglasses', 'glasses', 'eyewear',
            # Beauty & Personal Care
            'perfume', 'fragrance', 'cologne', 'deodorant', 'body spray',
            'beauty', 'skincare', 'makeup', 'cosmetics', 'lipstick', 'foundation',
            'grooming', 'shaving', 'razor', 'trimmer', 'haircare', 'hair',
            'lotion', 'cream', 'serum', 'face wash', 'moisturizer',
            # Sports & Fitness
            'sportswear', 'activewear', 'gym', 'fitness', 'yoga', 'running',
            'workout', 'athletic', 'jersey', 'track',
            # Innerwear & Loungewear
            'innerwear', 'underwear', 'lingerie', 'nightwear', 'sleepwear', 'loungewear',
            'pyjama', 'pajama', 'robe',
            # General style terms
            'style', 'trendy', 'designer', 'branded', 'gift', 'present', 'anniversary',
            'birthday', 'valentine', 'occasion'
        ]
        
        # Check if query is gender/demographic relevant
        # Also treat follow-up queries as relevant if we're in a product conversation
        is_gender_relevant = (
            any(kw in query_lower for kw in gender_relevant_keywords) or
            self._is_product_conversation_active()
        )
        
        # Expanded gender detection in query - don't override if already specified
        existing_gender_terms = [
            # Female terms
            "women's", "woman's", "womens", "women", "woman", "ladies", "lady", 
            "female", "feminine", "girls", "girl", "her", "she",
            # Male terms
            "men's", "man's", "mens", "men", "man", "gents", "gentleman",
            "male", "masculine", "boys", "boy", "his", "him",
            # Neutral/Other terms
            "kids", "kid", "children", "child", "baby", "infant", "toddler",
            "teen", "teenager", "youth", "junior", "unisex", "gender-neutral"
        ]
        has_gender = any(g in query_lower for g in existing_gender_terms)
        
        # Build structured enhancement
        if not is_gender_relevant or has_gender:
            return query
        
        # Map gender to target demographic hint
        gender_mapping = {
            'female': "women",
            'male': "men",
            'girl': "girls",
            'boy': "boys",
            'kid': "kids"
        }
        
        gender_key = gender.lower() if gender else ''
        target_demographic = gender_mapping.get(gender_key)
        
        # Build the enhanced query with gender enforcement (not overriding search intent)
        if target_demographic:
            # Enforce gender as a filter, keeping original query as primary focus
            # This ensures results match the user's gender without changing product category
            enhanced_query = f"{query} this product is for {target_demographic}"
            return enhanced_query
        
        return query
    
    def _apply_profile_to_entities(self, entities: Dict, user_profile: Optional[Dict[str, Any]], query: str) -> Dict:
        """Apply user profile preferences to search entities for filtering.
        Only applies gender if not already specified and query is gender-relevant."""
        if not user_profile or not entities:
            return entities or {}
        
        result = entities.copy()
        
        # Only apply profile gender if entities don't already have one
        if result.get("gender") is None:
            profile_gender = user_profile.get('gender', '').lower()
            if profile_gender:
                # Map profile gender to entity format
                gender_mapping = {
                    'female': 'women',
                    'male': 'men',
                    'girl': 'kids',
                    'boy': 'kids'
                }
                mapped_gender = gender_mapping.get(profile_gender, profile_gender)
                
                # Check if query is gender-relevant
                query_lower = query.lower()
                gender_relevant_keywords = [
                    'fashion', 'clothes', 'wear', 'outfit', 'dress', 'clothing',
                    'shirt', 'top', 'pants', 'jeans', 'jacket', 'shoes', 'footwear',
                    'sportswear', 'activewear', 'gym', 'fitness', 'sports',
                    'bag', 'watch', 'jewellery', 'jewelry', 'accessories',
                    'kurta', 'kurti', 'saree', 'ethnic', 'traditional'
                ]
                
                if any(kw in query_lower for kw in gender_relevant_keywords):
                    result["gender"] = mapped_gender
        
        return result
    
    def _build_profile_filter_context(self, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a structured filter context from user profile for search operations."""
        if not user_profile:
            return {}
        
        gender = user_profile.get('gender', '').lower()
        age = user_profile.get('age', '')
        
        filter_context = {}
        
        # Gender-based filtering
        gender_filters = {
            'female': {
                'include_keywords': ['women', "women's", 'ladies', 'female', 'feminine', 'her'],
                'exclude_keywords': ['men', "men's", 'male', 'boys', 'gents', 'masculine']
            },
            'male': {
                'include_keywords': ['men', "men's", 'gents', 'male', 'masculine', 'his'],
                'exclude_keywords': ['women', "women's", 'ladies', 'female', 'feminine', 'girls']
            },
            'girl': {
                'include_keywords': ['girls', "girls'", 'girl', 'young women', 'teen'],
                'exclude_keywords': ['boys', 'men', 'male', "men's"]
            },
            'boy': {
                'include_keywords': ['boys', "boys'", 'boy', 'young men', 'teen'],
                'exclude_keywords': ['girls', 'women', 'female', "women's"]
            }
        }
        
        if gender in gender_filters:
            filter_context['gender_include'] = gender_filters[gender]['include_keywords']
            filter_context['gender_exclude'] = gender_filters[gender]['exclude_keywords']
        
        # Age-based filtering
        if age:
            try:
                age_num = int(age)
                if age_num < 13:
                    filter_context['age_group'] = 'kids'
                elif age_num < 20:
                    filter_context['age_group'] = 'teen'
                elif age_num < 30:
                    filter_context['age_group'] = 'young_adult'
                elif age_num < 50:
                    filter_context['age_group'] = 'adult'
                else:
                    filter_context['age_group'] = 'mature'
            except (ValueError, TypeError):
                pass
        
        return filter_context
    
    def process(self, user_input: str, image: Optional[Image.Image] = None,
                user_profile: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Main entry point - routes to appropriate handler with conversation awareness
        """
        # Get conversation context
        conv_context = self.conversation_manager.get_structured_context()
        
        # First check if it's an image search (new image uploaded)
        if image is not None:
            return self.handle_image_search(user_input, image, user_profile)
        
        # Check if we're in an active scenario shopping session
        if conv_context.get("scenario_active") and conv_context.get("scenario_items"):
            # Check if this is a refinement request for the scenario
            if self._is_scenario_refinement(user_input, conv_context):
                return self.handle_scenario_refinement(user_input, user_profile, conv_context)
        
        # For text queries, analyze if it's a follow-up
        if conv_context["has_history"]:
            # Check if last search was image-based - handle follow-ups specially
            last_search_type = conv_context.get("last_search_type")
            last_image_description = conv_context.get("last_image_description")
            
            if last_search_type == "image" and last_image_description:
                # Check if this is a follow-up related to the image search
                followup_analysis = self.followup_analyzer.analyze(user_input, conv_context)
                action = followup_analysis.get("action", "new_search")
                
                if action in ["product_discussion", "refine_search"]:
                    # Handle as image search follow-up (preserves product type from image)
                    return self.handle_image_search_followup(user_input, user_profile, conv_context)
                elif action == "general_chat":
                    return self.handle_general_conversation(user_input, user_profile)
                # else: action == "new_search", fall through to normal classification
            else:
                # Text-based search follow-up handling
                followup_analysis = self.followup_analyzer.analyze(user_input, conv_context)
                action = followup_analysis.get("action", "new_search")
                
                # Handle based on follow-up action
                if action == "product_discussion":
                    return self.handle_product_discussion(user_input, user_profile, conv_context)
                elif action == "refine_search":
                    return self.handle_search_refinement(user_input, user_profile, conv_context)
                elif action == "general_chat":
                    return self.handle_general_conversation(user_input, user_profile)
                # else: action == "new_search", fall through to normal classification
        
        # Standard intent classification for new queries
        intent = self.intent_classifier.classify(user_input, has_image=False)
        
        if intent == "general_conversation":
            return self.handle_general_conversation(user_input, user_profile)
        elif intent == "scenario_shopping":
            return self.handle_scenario_shopping(user_input, user_profile)
        else:
            return self.handle_text_search(user_input, user_profile)
    
    def _is_scenario_refinement(self, query: str, conv_context: Dict) -> bool:
        """Check if query is a refinement request for active scenario"""
        refinement_indicators = [
            'instead', 'replace', 'change', 'different', 'swap', 'another',
            'don\'t like', 'not', 'prefer', 'cheaper', 'expensive', 'better',
            'first', 'second', 'third', 'fourth', 'fifth',
            '#1', '#2', '#3', '#4', '#5'
        ]
        query_lower = query.lower()
        # Check for direct item references or refinement keywords
        if any(ind in query_lower for ind in refinement_indicators):
            return True
        # Check if query mentions any of the current categories
        for item in conv_context.get("scenario_items", []):
            if item.get("category", "").lower() in query_lower:
                return True
        return False
    
    def handle_general_conversation(self, query: str, 
                                    user_profile: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle general questions about the agent"""
        context = self.conversation_manager.get_context()
        user_context = self._format_user_context(user_profile)
        
        full_context = f"{user_context}\n\n{context}" if user_context else context
        response = self.response_generator.generate_general_response(query, full_context)
        
        self.conversation_manager.add_turn(query, response)
        
        return AgentResponse(
            intent="general_conversation",
            response=response,
            products=[]
        )
    
    def handle_text_search(self, query: str,
                          user_profile: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle text-based product recommendations with personalization"""
        entities = self.query_processor.extract_entities(query)
        
        # Apply user profile to entities for proper filtering (e.g., gender)
        entities = self._apply_profile_to_entities(entities, user_profile, query)
        
        # Enhance query with user profile for better search results
        enhanced_query = self._enhance_query_with_profile(query, user_profile)
        
        products = self.search_engine.text_search(enhanced_query, filters=entities, top_k=5)
        
        # Build context with user profile for personalized response
        context = self.conversation_manager.get_context()
        user_context = self._format_user_context(user_profile)
        full_context = f"{user_context}\n\n{context}" if user_context else context
        
        response = self.response_generator.generate_product_response(query, products, full_context)
        
        # Store search type for follow-up handling
        self.conversation_manager.add_turn(
            query, response, products, 
            search_query=query, 
            entities=entities,
            search_type="text"
        )
        
        return AgentResponse(
            intent="product_search",
            response=response,
            products=products
        )
    
    def handle_search_refinement(self, query: str, 
                                 user_profile: Optional[Dict[str, Any]] = None,
                                 conv_context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle refinement of previous text search with additional constraints"""
        # Get base search parameters
        base_query = conv_context.get("last_search_query", query)
        base_entities = conv_context.get("last_search_entities") or {}
        
        # Refine entities with new constraints
        refined_entities = self.query_processor.refine_entities(query, base_entities, base_query)
        
        # Build combined query for search
        combined_query = f"{base_query} {query}"
        
        # Apply user profile to entities for proper filtering (e.g., gender)
        refined_entities = self._apply_profile_to_entities(refined_entities, user_profile, combined_query)
        
        enhanced_query = self._enhance_query_with_profile(combined_query, user_profile)
        
        # Perform refined search
        products = self.search_engine.text_search(enhanced_query, filters=refined_entities, top_k=5)
        
        # Build context
        context = self.conversation_manager.get_context()
        user_context = self._format_user_context(user_profile)
        full_context = f"{user_context}\n\n{context}" if user_context else context
        
        # Generate response acknowledging refinement
        response = self.response_generator.generate_refinement_response(
            original_query=base_query,
            refinement=query,
            products=products,
            context=full_context
        )
        
        # Preserve text search type
        self.conversation_manager.add_turn(
            query, response, products, 
            search_query=combined_query, 
            entities=refined_entities,
            search_type="text"
        )
        
        return AgentResponse(
            intent="product_search_refinement",
            response=response,
            products=products
        )
    
    def handle_product_discussion(self, query: str,
                                  user_profile: Optional[Dict[str, Any]] = None,
                                  conv_context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle questions/discussion about previously shown products"""
        # Get previously shown products
        last_products = []
        for turn in reversed(self.conversation_manager.history):
            if turn.products and len(turn.products) > 0:
                last_products = turn.products
                break
        
        if not last_products:
            # Fallback to general conversation
            return self.handle_general_conversation(query, user_profile)
        
        # Preserve existing search context for future refinements
        existing_entities = conv_context.get("last_search_entities") if conv_context else None
        existing_query = conv_context.get("last_search_query") if conv_context else None
        existing_search_type = conv_context.get("last_search_type") if conv_context else None
        existing_image_description = conv_context.get("last_image_description") if conv_context else None
        
        # Build context
        context = self.conversation_manager.get_context()
        user_context = self._format_user_context(user_profile)
        full_context = f"{user_context}\n\n{context}" if user_context else context
        
        # Generate discussion response
        response = self.response_generator.generate_product_discussion_response(
            query=query,
            products=last_products,
            context=full_context
        )
        
        # Preserve all search context for future refinements
        self.conversation_manager.add_turn(
            query, response, products=last_products,
            search_query=existing_query, 
            entities=existing_entities,
            search_type=existing_search_type,
            image_description=existing_image_description
        )
        
        return AgentResponse(
            intent="product_discussion",
            response=response,
            products=last_products
        )
    
    def handle_image_search_followup(self, query: str,
                                     user_profile: Optional[Dict[str, Any]] = None,
                                     conv_context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Handle follow-up queries after an image search.
        
        Uses the stored image description to maintain product type consistency.
        This ensures follow-ups like "show me in black" or "cheaper options" 
        still return the same type of product as the original image.
        """
        # Get stored image description from conversation context
        image_description = conv_context.get("last_image_description", "")
        
        if not image_description:
            # Fallback to text search if no image description stored
            return self.handle_text_search(query, user_profile)
        
        # Build profile filter context for search operations
        profile_context = self._build_profile_filter_context(user_profile)
        
        # Extract entities from text query if provided
        entities = self.query_processor.extract_entities(query) if query else {}
        
        # Apply user profile to entities
        entities = self._apply_profile_to_entities(entities, user_profile, query or "")
        
        # Use image_search_followup to search using stored image description
        products = self.search_engine.image_search_followup(
            query or "", image_description, top_k=5, profile_context=profile_context
        )
        
        context = self.conversation_manager.get_context()
        user_context = self._format_user_context(user_profile)
        full_context = f"{user_context}\n\n{context}" if user_context else context
        
        # Generate response - use refinement response to acknowledge the follow-up
        response = self.response_generator.generate_refinement_response(
            original_query="[Image search]",
            refinement=query,
            products=products,
            context=full_context
        )
        
        # Keep the image search context for further follow-ups
        self.conversation_manager.add_turn(
            query, response, products,
            search_query=query,
            entities=entities,
            search_type="image",  # Preserve image search type
            image_description=image_description  # Preserve image description
        )
        
        return AgentResponse(
            intent="image_search_followup",
            response=response,
            products=products
        )
    
    def handle_image_search(self, query: str, image: Image.Image,
                           user_profile: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Handle image-based product search with personalization.
        
        Uses hybrid_search which:
        1. Analyzes the image to understand the product
        2. Parses user's text to understand their intent (similar, variation, cheaper, etc.)
        3. Combines image understanding + user intent for optimal search
        4. Applies user's specific filters (color, price, style) to results
        """
        # Build profile filter context for search operations
        profile_context = self._build_profile_filter_context(user_profile)
        
        # Extract entities from text query if provided
        entities = self.query_processor.extract_entities(query) if query else {}
        
        # Apply user profile to entities for proper filtering (e.g., gender)
        entities = self._apply_profile_to_entities(entities, user_profile, query or "")
        
        # Use output_metadata to capture the image description for follow-ups
        output_metadata = {}
        
        # Always use hybrid_search - it handles all cases:
        # - "I want this" → finds similar products to the image
        # - "I want this in black" → finds similar but filters for black
        # - "show me cheaper options" → finds similar but sorts by price
        products = self.search_engine.hybrid_search(
            query or "", image, top_k=5, profile_context=profile_context,
            output_metadata=output_metadata
        )
        
        # Get the image description for storing in conversation context
        image_description = output_metadata.get('image_description', '')
        
        context = self.conversation_manager.get_context()
        user_context = self._format_user_context(user_profile)
        full_context = f"{user_context}\n\n{context}" if user_context else context
        
        response = self.response_generator.generate_image_search_response(query, products, full_context)
        
        input_text = f"[Image uploaded] {query}" if query else "[Image uploaded]"
        # Store search type and image description for follow-up handling
        self.conversation_manager.add_turn(
            input_text, response, products, 
            search_query=query or "image_search", 
            entities=entities,
            search_type="image",
            image_description=image_description
        )
        
        return AgentResponse(
            intent="image_search",
            response=response,
            products=products
        )
    
    def handle_scenario_shopping(self, query: str,
                                 user_profile: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle scenario-based shopping (e.g., 'going camping', 'wedding preparation')"""
        # Clear any previous scenario
        self.conversation_manager.clear_scenario()
        
        # Extract entities from query for refinement support
        entities = self.query_processor.extract_entities(query)
        
        # Apply user profile to entities for proper filtering (e.g., gender)
        entities = self._apply_profile_to_entities(entities, user_profile, query)
        
        # Analyze scenario to get product categories
        scenario_analysis = self.scenario_processor.analyze_scenario(query, user_profile)
        scenario_name = scenario_analysis.get("scenario_name", "Shopping")
        categories = scenario_analysis.get("categories", [])
        
        if not categories:
            return self.handle_text_search(query, user_profile)
        
        # Find one best product for each category
        scenario_items = []
        all_products = []
        
        for category in categories:
            # Enhance category search with user profile
            search_query = self._enhance_query_with_profile(category, user_profile)
            products = self.search_engine.text_search(search_query, filters=entities, top_k=1)
            
            if products:
                product = products[0]
                scenario_items.append({
                    "category": category,
                    "product": product,
                    "product_title": product.title,
                    "product_id": product.id
                })
                all_products.append(product)
        
        # Store scenario state
        self.conversation_manager.set_scenario(scenario_name, categories, scenario_items)
        
        # Build context
        context = self.conversation_manager.get_context()
        user_context = self._format_user_context(user_profile)
        full_context = f"{user_context}\n\n{context}" if user_context else context
        
        # Generate response
        response = self.response_generator.generate_scenario_response(
            scenario_name=scenario_name,
            scenario_items=scenario_items,
            context=full_context
        )
        
        self.conversation_manager.add_turn(
            query, response, all_products, 
            search_query=query, 
            entities=entities,
            search_type="scenario"
        )
        
        return AgentResponse(
            intent="scenario_shopping",
            response=response,
            products=all_products
        )
    
    def handle_scenario_refinement(self, query: str,
                                   user_profile: Optional[Dict[str, Any]] = None,
                                   conv_context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle refinement requests for scenario shopping (replace specific items)"""
        current_items = conv_context.get("scenario_items", [])
        scenario_name = conv_context.get("scenario_name", "Shopping")
        
        # Get base entities and refine with new query constraints
        base_entities = conv_context.get("last_search_entities") or {}
        base_query = conv_context.get("last_search_query", query)
        refined_entities = self.query_processor.refine_entities(query, base_entities, base_query)
        
        # Apply user profile to entities for proper filtering (e.g., gender)
        refined_entities = self._apply_profile_to_entities(refined_entities, user_profile, query)
        
        if not current_items:
            return self.handle_text_search(query, user_profile)
        
        # Parse which items need replacement
        refinement = self.scenario_processor.parse_refinement_request(query, current_items)
        items_to_replace = refinement.get("items_to_replace", [])
        new_requirements = refinement.get("new_requirements", {})
        
        if not items_to_replace:
            return self.handle_text_search(query, user_profile)
        
        # Create updated items list (keep unchanged items, replace specified ones)
        updated_items = list(current_items)
        
        for item_num in items_to_replace:
            idx = item_num - 1  # Convert to 0-based index
            if 0 <= idx < len(updated_items):
                old_item = updated_items[idx]
                category = old_item["category"]
                
                # Build new search query with refinement requirements
                requirement = new_requirements.get(str(item_num), query)
                search_query = f"{category} {requirement}"
                search_query = self._enhance_query_with_profile(search_query, user_profile)
                
                # Search for replacement with profile-aware filters
                products = self.search_engine.text_search(search_query, filters=refined_entities, top_k=1)
                
                if products:
                    new_product = products[0]
                    updated_items[idx] = {
                        "category": category,
                        "product": new_product,
                        "product_title": new_product.title,
                        "product_id": new_product.id
                    }
                    self.conversation_manager.update_scenario_item(idx, updated_items[idx])
        
        # Update scenario items in conversation manager
        self.conversation_manager.scenario_items = updated_items
        
        # Collect all products
        all_products = [item["product"] for item in updated_items if item.get("product")]
        
        # Build context
        context = self.conversation_manager.get_context()
        user_context = self._format_user_context(user_profile)
        full_context = f"{user_context}\n\n{context}" if user_context else context
        
        # Generate response highlighting changes
        response = self.response_generator.generate_scenario_refinement_response(
            scenario_name=scenario_name,
            scenario_items=updated_items,
            replaced_indices=items_to_replace,
            refinement_request=query,
            context=full_context
        )
        
        self.conversation_manager.add_turn(
            query, response, all_products, 
            search_query=query, 
            entities=refined_entities,
            search_type="scenario"
        )
        
        return AgentResponse(
            intent="scenario_shopping",
            response=response,
            products=all_products
        )
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_manager.clear()
