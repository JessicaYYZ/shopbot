"""
Multi-modal search engine - Optimized for Flipkart catalog
"""

from typing import List, Dict, Optional
from PIL import Image
from ..models.openai_client import OpenAIClient
from ..models.vector_store import VectorStore
from ..data.database import Database
from ..data.schemas import Product
import logging

logging.basicConfig(level=logging.INFO)

class SearchEngine:
    """Handles text and image-based product search - optimized for performance"""

    def __init__(self, openai_client: OpenAIClient, vector_store: VectorStore,
                 database: Database):
        self.openai = openai_client
        self.vector_store = vector_store
        self.database = database
        self._embedding_cache = {}  # Cache for common query embeddings

    def text_search(self,
                    query: str,
                    filters: Dict = None,
                    top_k: int = 5) -> List[Product]:
        """Search products using text query with caching"""
        # Check cache for embedding
        cache_key = query.lower().strip()
        if cache_key in self._embedding_cache:
            query_embedding = self._embedding_cache[cache_key]
        else:
            query_embedding = self.openai.generate_embedding(query)
            if query_embedding:
                # Cache up to 100 embeddings
                if len(self._embedding_cache) < 100:
                    self._embedding_cache[cache_key] = query_embedding

        if not query_embedding:
            return []

        # Build metadata filters
        where_filter = self._build_filters(filters) if filters else None

        # Search vector store - fetch more results for better filtering
        search_k = top_k * 3 if filters else top_k
        results = self.vector_store.search_text(query_embedding,
                                                top_k=search_k,
                                                where_filter=where_filter)

        # Extract product IDs
        if not results['ids'] or not results['ids'][0]:
            return []

        product_ids = [int(pid) for pid in results['ids'][0]]

        # Fetch full product details from database
        products = self.database.get_products_by_ids(product_ids)

        logging.info("Products:")
        logging.info(products)

        # Apply additional filtering and ranking
        if filters:
            products = self._apply_filters(products, filters)

        return products[:top_k]

    def image_search(self,
                     image: Image.Image,
                     top_k: int = 5,
                     profile_context: Optional[Dict] = None) -> List[Product]:
        """Search products using image with enhanced analysis"""
        # Build detailed image analysis prompt for better embedding search
        image_analysis_prompt = self._build_image_analysis_prompt(profile_context)
        
        # Analyze image with enhanced prompt to capture type and features
        description = self.openai.analyze_image(image=image, prompt=image_analysis_prompt)

        if not description or description == "Could not analyze image":
            return []
        
        logging.info(f"Image analysis result: {description[:200]}...")

        # Convert description to embedding
        embedding = self.openai.generate_embedding(description)

        if not embedding:
            return []

        # Search vector store with more results for filtering
        search_k = top_k * 2 if profile_context else top_k
        results = self.vector_store.search_text(embedding, top_k=search_k)

        # Extract product IDs
        if not results['ids'] or not results['ids'][0]:
            return []

        product_ids = [int(pid) for pid in results['ids'][0]]

        # Fetch products
        products = self.database.get_products_by_ids(product_ids)
        
        # Apply profile-based filtering if provided
        if profile_context:
            products = self._apply_profile_filter(products, profile_context)

        return products[:top_k]
    
    def _build_image_analysis_prompt(self, profile_context: Optional[Dict] = None) -> str:
        """Build a detailed prompt for image analysis to improve embedding search."""
        base_prompt = """Analyze this product image in detail for e-commerce search matching.

Provide a structured description covering:

1. PRODUCT TYPE: Exact product category (e.g., "casual cotton t-shirt", "leather formal shoes", "gold pendant necklace")

2. TARGET DEMOGRAPHIC: Who is this product for?
   - Gender: men's/women's/unisex/boys'/girls'/kids'
   - Age group: adult/teen/child/baby
   - Occasion: casual/formal/party/sports/ethnic/wedding

3. VISUAL FEATURES:
   - Primary color(s) and patterns (solid, striped, printed, floral, geometric)
   - Material texture (cotton, silk, leather, denim, wool, synthetic, metal, gemstone)
   - Style elements (slim fit, oversized, vintage, modern, minimalist, ornate)
   
4. DISTINCTIVE DETAILS:
   - Design elements (embroidery, studs, cutwork, pleats, ruffles)
   - Brand logos or text (if visible)
   - Hardware or embellishments (buttons, zippers, clasps, stones)

5. SEARCH KEYWORDS: List 5-8 specific keywords that would help find similar products.

Be specific and use e-commerce terminology. Focus on searchable attributes."""

        # Add profile context hints if available
        if profile_context:
            gender_include = profile_context.get('gender_include', [])
            if gender_include:
                base_prompt += f"\n\nNote: The user is looking for products suitable for {', '.join(gender_include[:2])}. Emphasize features relevant to this demographic."
        
        return base_prompt
    
    def _apply_profile_filter(self, products: List[Product], profile_context: Dict) -> List[Product]:
        """Filter products based on user profile context."""
        if not profile_context:
            return products
        
        gender_include = profile_context.get('gender_include', [])
        gender_exclude = profile_context.get('gender_exclude', [])
        
        if not gender_include and not gender_exclude:
            return products
        
        filtered = []
        for p in products:
            # Build searchable text from product
            product_text = f"{p.title} {p.category} {p.specifications.get('Ideal For', '')} {p.specifications.get('Gender', '')}".lower()
            
            # Check for exclusion terms
            has_exclude = any(term.lower() in product_text for term in gender_exclude)
            
            # Check for inclusion terms
            has_include = any(term.lower() in product_text for term in gender_include)
            
            # Include if it matches include terms OR doesn't have exclude terms (for unisex products)
            if has_include or (not has_exclude and not has_include):
                filtered.append(p)
        
        # Return filtered if we have results, otherwise return original to avoid empty results
        return filtered if filtered else products

    def _extract_user_modifications(self, query: str) -> Dict:
        """
        Extract filter modifications from user's text query.
        
        Only extracts attributes like color, price preference, style - 
        NEVER changes the product type (that comes from the image).
        """
        if not query or not query.strip():
            return {}
        
        import json
        
        prompt = f"""Extract any product attribute modifications from the user's request.
The user is looking at a product image and wants similar items. Extract ONLY the modifications they want.

USER SAID: "{query}"

Return a JSON object with ONLY the attributes the user explicitly mentioned:
{{
    "color": "color if user specified one, else null",
    "price_preference": "cheaper" or "expensive" if mentioned, else null,
    "style": "casual/formal/sporty/etc" if mentioned, else null,
    "material": "material if mentioned, else null",
    "brand": "brand if mentioned, else null",
    "occasion": "occasion if mentioned, else null"
}}

RULES:
1. Only include attributes the user EXPLICITLY mentioned
2. If user says "I want this", "find similar", "show me" - return empty modifications {{}}
3. If user says "but in black" - return {{"color": "black"}}
4. If user says "cheaper options" - return {{"price_preference": "cheaper"}}
5. Return null for any attribute not mentioned

Return ONLY the JSON object."""

        messages = [
            {"role": "system", "content": "Extract product attribute modifications. Return only valid JSON with null for unmentioned attributes."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.openai.generate_text(messages, max_tokens=150, temperature=0.0)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()
            
            modifications = json.loads(response)
            # Remove null values
            modifications = {k: v for k, v in modifications.items() if v is not None}
            logging.info(f"Extracted modifications: {modifications}")
            return modifications
        except Exception as e:
            logging.warning(f"Failed to parse modifications: {e}")
            return {}
    
    def _apply_modifications(self, products: List[Product], modifications: Dict) -> List[Product]:
        """Apply user's modifications to filter/rerank products."""
        if not modifications:
            return products
        
        filtered = list(products)  # Make a copy
        
        # Filter by color
        color = modifications.get("color")
        if color:
            color_lower = color.lower()
            color_filtered = [
                p for p in filtered 
                if color_lower in p.title.lower() 
                or color_lower in str(p.specifications.get('Color', '')).lower()
            ]
            if color_filtered:
                filtered = color_filtered
                logging.info(f"Color filter '{color}': {len(color_filtered)} products")
        
        # Filter by material
        material = modifications.get("material")
        if material:
            material_lower = material.lower()
            material_filtered = [
                p for p in filtered
                if material_lower in p.title.lower()
                or material_lower in str(p.specifications.get('Material', '')).lower()
                or material_lower in str(p.specifications.get('Fabric', '')).lower()
            ]
            if material_filtered:
                filtered = material_filtered
        
        # Filter by style/occasion
        style = modifications.get("style") or modifications.get("occasion")
        if style:
            style_lower = style.lower()
            style_filtered = [
                p for p in filtered
                if style_lower in p.title.lower()
                or style_lower in p.category.lower()
                or style_lower in str(p.specifications.get('Occasion', '')).lower()
                or style_lower in str(p.specifications.get('Type', '')).lower()
            ]
            if style_filtered:
                filtered = style_filtered
        
        # Sort by price preference
        price_pref = modifications.get("price_preference")
        if price_pref and filtered:
            if price_pref in ["cheaper", "budget", "affordable", "low"]:
                filtered = sorted(filtered, key=lambda p: p.price)
            elif price_pref in ["expensive", "premium", "luxury", "high"]:
                filtered = sorted(filtered, key=lambda p: p.price, reverse=True)
        
        return filtered if filtered else products
    
    def hybrid_search(self,
                      query: str,
                      image: Image.Image,
                      top_k: int = 5,
                      profile_context: Optional[Dict] = None,
                      output_metadata: Optional[Dict] = None) -> List[Product]:
        """
        Image-first search with text-based filtering.
        
        Strategy:
        1. Analyze image → get product description (determines PRODUCT TYPE)
        2. Search using image description embedding (finds same type of products)
        3. Extract modifications from user text (color, price, style only)
        4. Apply modifications as filters on search results
        
        The product TYPE always comes from the image - user text only filters/refines.
        
        Args:
            output_metadata: Optional dict to store metadata like image_description for caller
        """
        logging.info(f"Hybrid search - query: '{query}'")
        
        # Step 1: Analyze image to understand what product it is
        image_analysis_prompt = self._build_image_analysis_prompt(profile_context)
        image_description = self.openai.analyze_image(image=image, prompt=image_analysis_prompt)
        
        if not image_description or image_description == "Could not analyze image":
            logging.warning("Could not analyze image, falling back to text search")
            return self.text_search(query, top_k=top_k) if query else []
        
        logging.info(f"Image analysis: {image_description[:200]}...")
        
        # Store image description in output metadata for conversation context
        if output_metadata is not None:
            output_metadata['image_description'] = image_description
        
        # Step 2: Search using the IMAGE DESCRIPTION (this ensures product type match)
        # The image description determines what type of product we're looking for
        embedding = self.openai.generate_embedding(image_description)
        if not embedding:
            return []
        
        # Get more results for filtering
        search_k = top_k * 4
        results = self.vector_store.search_text(embedding, top_k=search_k)
        
        if not results['ids'] or not results['ids'][0]:
            return []
        
        # Get products in the order returned by vector search (most similar first)
        product_ids = [int(pid) for pid in results['ids'][0]]
        products_map = {p.id: p for p in self.database.get_products_by_ids(product_ids)}
        
        # Preserve order from vector search
        products = [products_map[pid] for pid in product_ids if pid in products_map]
        
        logging.info(f"Found {len(products)} products from image search")
        
        # Step 3: Extract modifications from user's text (color, price, etc.)
        modifications = self._extract_user_modifications(query)
        
        # Step 4: Apply modifications as filters
        if modifications:
            products = self._apply_modifications(products, modifications)
            logging.info(f"After applying modifications: {len(products)} products")
        
        # Step 5: Apply profile-based filtering if provided
        if profile_context:
            products = self._apply_profile_filter(products, profile_context)
        
        return products[:top_k]
    
    def image_search_followup(self,
                              query: str,
                              image_description: str,
                              top_k: int = 5,
                              profile_context: Optional[Dict] = None) -> List[Product]:
        """
        Follow-up search after an image search, using stored image description.
        
        This allows refining image search results without needing the original image.
        The product type is preserved from the original image description.
        
        Args:
            query: User's follow-up query (e.g., "show me in black", "cheaper options")
            image_description: Stored description from original image analysis
            top_k: Number of results to return
            profile_context: Optional profile-based filters
        """
        logging.info(f"Image search followup - query: '{query}'")
        logging.info(f"Using stored image description: {image_description[:100]}...")
        
        # Step 1: Search using the stored IMAGE DESCRIPTION (preserves product type)
        embedding = self.openai.generate_embedding(image_description)
        if not embedding:
            return []
        
        # Get more results for filtering
        search_k = top_k * 4
        results = self.vector_store.search_text(embedding, top_k=search_k)
        
        if not results['ids'] or not results['ids'][0]:
            return []
        
        # Get products in the order returned by vector search (most similar first)
        product_ids = [int(pid) for pid in results['ids'][0]]
        products_map = {p.id: p for p in self.database.get_products_by_ids(product_ids)}
        
        # Preserve order from vector search
        products = [products_map[pid] for pid in product_ids if pid in products_map]
        
        logging.info(f"Found {len(products)} products from image description search")
        
        # Step 2: Extract modifications from user's follow-up text
        modifications = self._extract_user_modifications(query)
        
        # Step 3: Apply modifications as filters
        if modifications:
            products = self._apply_modifications(products, modifications)
            logging.info(f"After applying modifications: {len(products)} products")
        
        # Step 4: Apply profile-based filtering if provided
        if profile_context:
            products = self._apply_profile_filter(products, profile_context)
        
        return products[:top_k]

    def _apply_filters(self, products: List[Product],
                       filters: Dict) -> List[Product]:
        """Apply post-retrieval filtering for better accuracy"""
        filtered = products

        # Filter by price
        if filters.get('price_max'):
            filtered = [p for p in filtered if p.price <= filters['price_max']]
        if filters.get('price_min'):
            filtered = [p for p in filtered if p.price >= filters['price_min']]

        # Filter by gender (check in category, title, or specifications)
        if filters.get('gender'):
            gender = filters['gender'].lower()
            gender_keywords = {
                'women': ["women's", "women", "ladies", "female", "girl"],
                'men': ["men's", "men", "male", "boy", "gents"],
                'kids': ["kids", "children", "baby", "infant"]
            }
            keywords = gender_keywords.get(gender, [])
            if keywords:
                gender_filtered = []
                for p in filtered:
                    text = f"{p.title} {p.category} {p.specifications.get('Ideal For', '')}".lower(
                    )
                    if any(kw in text for kw in keywords):
                        gender_filtered.append(p)
                if gender_filtered:
                    filtered = gender_filtered

        # Filter by color
        if filters.get('color'):
            color = filters['color'].lower()
            color_filtered = [
                p for p in filtered if color in p.title.lower()
                or color in str(p.specifications.get('Color', '')).lower()
            ]
            if color_filtered:
                filtered = color_filtered

        return filtered

    def _build_filters(self, entities: Dict) -> Optional[Dict]:
        """Convert entities to ChromaDB filter format"""
        filters = {}

        # Price filter
        if entities.get('price_max'):
            filters['price'] = {'$lte': entities['price_max']}

        # Brand filter - exact match (ChromaDB doesn't support $contains)
        if entities.get('brand'):
            filters['brand'] = {'$eq': entities['brand']}

        # Note: Category filtering is done post-retrieval in _apply_filters
        # because ChromaDB doesn't support partial string matching

        return filters if filters else None

    def clear_cache(self):
        """Clear the embedding cache"""
        self._embedding_cache = {}
