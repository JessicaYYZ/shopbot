"""
Response generation using LLM - Optimized for Flipkart catalog
"""

from typing import List
from ..models.openai_client import OpenAIClient
from ..data.schemas import Product
import logging


class ResponseGenerator:
    """Generates natural language responses with personalization"""

    def __init__(self, openai_client: OpenAIClient):
        self.openai = openai_client

    def _validate_response(self, response: str,
                           products: List[Product]) -> str:
        """Validate that response only mentions products from the provided list"""
        if not products:
            return response

        # Extract product titles for validation
        product_titles = [p.title for p in products]

        # Check if response contains any of the actual product titles
        found_valid_product = False
        for title in product_titles:
            # Check for at least first 20 chars of the product title
            title_start = title[:20].lower()
            if title_start in response.lower():
                found_valid_product = True
                break

        # If no valid products mentioned, add a warning
        if not found_valid_product and len(products) > 0:
            warning = (
                "\n\n⚠️ Note: The recommendations above may not exactly match our current inventory. "
                "Here are the actual products available:\n\n")
            for i, p in enumerate(products[:3], 1):
                warning += f"{i}. {p.title[:80]} - ₹{p.price:,.0f}\n"

            return response + warning

        return response

    def _extract_user_profile_prompt(self, context: str) -> str:
        """Extract user profile section from context for prompts"""
        if "User Profile:" in context:
            return context
        return ""

    def generate_general_response(self, query: str, context: str = "") -> str:
        """Handle general conversation about the agent"""
        user_profile_context = self._extract_user_profile_prompt(context)

        system_prompt = f"""You are ShopBot, a helpful AI shopping assistant for an Indian e-commerce platform.

Your catalog includes:
- Clothing (Men's, Women's, Kids')
- Jewellery (Necklaces, Rings, Bangles, Earrings)
- Footwear (Shoes, Sandals, Heels, Sneakers)
- Watches (Wrist Watches, Smartwatches)
- Electronics (Laptops, Mobiles, Accessories)
- Beauty & Personal Care (Fragrances, Skincare, Makeup)
- Home & Kitchen (Furniture, Decor, Appliances)
- Sports & Fitness
- Bags, Wallets & Belts

{user_profile_context}

Be friendly, concise, and helpful. Use Indian Rupees (₹) for prices. Address users by name when available."""

        messages = [{
            "role": "system",
            "content": system_prompt
        }, {
            "role": "user",
            "content": query
        }]

        return self.openai.generate_text(messages, max_tokens=200)

    def generate_product_response(self,
                                  query: str,
                                  products: List[Product],
                                  context: str = "") -> str:
        """Generate response for text-based product search with personalization"""
        if not products:
            return "I couldn't find any products matching your criteria. Could you try rephrasing or adjusting your requirements?"

        product_context = self._format_products(products)
        logging.info(product_context)
        user_profile_context = self._extract_user_profile_prompt(context)

        personalization_instructions = ""
        if user_profile_context:
            personalization_instructions = f"""
IMPORTANT - USER PROFILE FOR PERSONALIZATION:
{user_profile_context}

PERSONALIZATION RULES:
- Tailor your recommendations to match the user's gender, interests, and style preferences
- For FEMALE users asking about fashion/party attire: prioritize dresses, skirts, handbags, jewelry, high-heel shoes, makeup, elegant accessories
- For MALE users asking about fashion/party attire: prioritize suits, formal shirts, leather shoes, watches, ties, cufflinks, men's accessories
- Use the user's interests to highlight relevant product features
- Consider their budget preference when discussing prices
- Address them by name for a personal touch
- Match recommendations to their stated style (elegant, practical, tech-savvy, etc.)
"""

        messages = [{
            "role":
            "system",
            "content":
            f"""You are a helpful shopping assistant that provides personalized product recommendations.

{personalization_instructions}

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. ONLY recommend products from the list provided below - DO NOT invent or create product names
2. Use the EXACT product titles as provided - DO NOT modify or paraphrase them
3. Use the EXACT prices shown - DO NOT make up prices
4. Always consider the user's gender when suggesting fashion, accessories, or personal items
5. Prioritize products that match their interests and style preferences
6. Be enthusiastic and conversational
7. Use Indian Rupee (₹) for prices"""
        }, {
            "role":
            "user",
            "content":
            f"""The user asked: "{query}"

Here are relevant products from our catalog (ONLY recommend from this list):

{product_context}

Provide a personalized response that:
1. Acknowledges their request (use their name if known)
2. Recommends 2-3 products from the EXACT list above that BEST MATCH their profile and query
3. Use the EXACT product titles and prices shown above - DO NOT change them
4. Explain WHY each product is a good match for them specifically
5. Highlight features relevant to their interests

IMPORTANT: You must ONLY mention products from the list provided above. Do NOT invent or create new product names.

Be conversational and make them feel the recommendations are just for them!"""
        }]

        # Use lower temperature (0.3) to reduce hallucinations
        response = self.openai.generate_text(messages,
                                             max_tokens=500,
                                             temperature=0.3)

        # Validate response to catch hallucinations
        return self._validate_response(response, products)

    def generate_image_search_response(self,
                                       query: str,
                                       products: List[Product],
                                       context: str = "") -> str:
        """Generate response for image-based search with personalization"""
        if not products:
            return "I couldn't find similar products for the image you uploaded. Try uploading a different image or describe what you're looking for!"

        product_context = self._format_products(products)
        user_profile_context = self._extract_user_profile_prompt(context)

        personalization_instructions = ""
        if user_profile_context:
            personalization_instructions = f"""
USER PROFILE FOR PERSONALIZATION:
{user_profile_context}

Personalize your response based on the user's profile. Consider their gender, interests, and style preferences when highlighting products.
"""

        user_message = "The user uploaded an image"
        if query:
            user_message += f' and said: "{query}"'

        messages = [{
            "role":
            "system",
            "content":
            f"""You are a helpful shopping assistant that provides personalized recommendations.

{personalization_instructions}

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. ONLY recommend products from the list provided below - DO NOT invent or create product names
2. Use the EXACT product titles as provided - DO NOT modify or paraphrase them
3. Use the EXACT prices shown - DO NOT make up prices
4. Use Indian Rupee (₹) for prices"""
        }, {
            "role":
            "user",
            "content":
            f"""{user_message}

Here are similar products from our catalog (ONLY recommend from this list):

{product_context}

Provide a personalized response that:
1. Acknowledges their image upload
2. Describes the similar products found using their EXACT titles from the list above
3. Highlight products most suitable for their profile
4. Mention key features and prices in ₹

IMPORTANT: You must ONLY mention products from the list provided above. Do NOT invent or create new product names.

Be friendly and make recommendations personal!"""
        }]

        # Use lower temperature (0.3) to reduce hallucinations
        response = self.openai.generate_text(messages,
                                             max_tokens=400,
                                             temperature=0.3)

        # Validate response to catch hallucinations
        return self._validate_response(response, products)
    
    def generate_refinement_response(self,
                                    original_query: str,
                                    refinement: str,
                                    products: List[Product],
                                    context: str = "") -> str:
        """Generate response for refined search results"""
        if not products:
            return f"I couldn't find products matching '{original_query}' with your additional requirement '{refinement}'. Would you like to try different filters or see the original results?"
        
        product_context = self._format_products(products)
        user_profile_context = self._extract_user_profile_prompt(context)
        
        personalization_instructions = ""
        if user_profile_context:
            personalization_instructions = f"""
USER PROFILE FOR PERSONALIZATION:
{user_profile_context}

Consider their preferences when highlighting products.
"""
        
        messages = [{
            "role": "system",
            "content": f"""You are a helpful shopping assistant that provides personalized product recommendations.

{personalization_instructions}

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. ONLY recommend products from the list provided below - DO NOT invent or create product names
2. Use the EXACT product titles as provided - DO NOT modify or paraphrase them
3. Use the EXACT prices shown - DO NOT make up prices
4. Acknowledge that these are REFINED results based on their additional requirements
5. Use Indian Rupee (₹) for prices"""
        }, {
            "role": "user",
            "content": f"""The user originally searched for: "{original_query}"
Then they added: "{refinement}"

Here are the refined products from our catalog (ONLY recommend from this list):

{product_context}

Provide a response that:
1. Acknowledges their refinement request
2. Shows 2-3 best matching products from the EXACT list above
3. Use EXACT product titles and prices from the list
4. Explains how these match their refined requirements
5. If relevant, mention what changed from the original search

Be conversational and helpful!"""
        }]
        
        response = self.openai.generate_text(messages, max_tokens=500, temperature=0.3)
        return self._validate_response(response, products)
    
    def generate_product_discussion_response(self,
                                            query: str,
                                            products: List[Product],
                                            context: str = "") -> str:
        """Generate response for questions about previously shown products"""
        if not products:
            return "I don't have the product details available. Could you ask about a specific product search?"
        
        product_context = self._format_products(products)
        user_profile_context = self._extract_user_profile_prompt(context)
        
        messages = [{
            "role": "system",
            "content": f"""You are a helpful shopping assistant answering questions about products.

{user_profile_context if user_profile_context else ''}

CRITICAL RULES:
1. ONLY discuss products from the list provided below
2. Use EXACT product titles and prices
3. Answer the user's specific question
4. Be helpful and provide relevant details
5. Use Indian Rupee (₹) for prices"""
        }, {
            "role": "user",
            "content": f"""The user is asking about these products:

{product_context}

Their question: "{query}"

Answer their question using information from the products listed above. Be specific and helpful!"""
        }]
        
        response = self.openai.generate_text(messages, max_tokens=400, temperature=0.3)
        return self._validate_response(response, products)

    def generate_scenario_response(self,
                                   scenario_name: str,
                                   scenario_items: list,
                                   context: str = "") -> str:
        """Generate response for scenario-based shopping recommendations"""
        if not scenario_items:
            return "I couldn't find suitable products for this scenario. Could you provide more details?"
        
        user_profile_context = self._extract_user_profile_prompt(context)
        
        # Format scenario items
        items_list = []
        for i, item in enumerate(scenario_items, 1):
            product = item.get("product")
            if product:
                items_list.append(f"{i}. **{item['category']}**: {product.title[:70]} - ₹{product.price:,.0f}")
            else:
                items_list.append(f"{i}. **{item['category']}**: (No match found)")
        
        items_str = "\n".join(items_list)
        categories_str = ", ".join([item['category'] for item in scenario_items])
        
        messages = [{
            "role": "system",
            "content": f"""You are a helpful shopping assistant presenting a curated set of products for a specific scenario/occasion.

{user_profile_context if user_profile_context else ''}

RULES:
1. Present the scenario and why these products work together
2. List each category and its recommended product using EXACT titles/prices provided
3. Keep it concise but helpful
4. Mention the user can ask to swap any specific item
5. Use Indian Rupee (₹) for prices"""
        }, {
            "role": "user",
            "content": f"""Scenario: {scenario_name}

Product categories identified: {categories_str}

Recommendations:
{items_str}

Write a response that:
1. Acknowledges the scenario
2. Lists the categories and one recommended product per category (use EXACT titles)
3. Briefly explain why this combination works
4. Remind them they can ask to change any specific item"""
        }]
        
        return self.openai.generate_text(messages, max_tokens=600, temperature=0.3)
    
    def generate_scenario_refinement_response(self,
                                              scenario_name: str,
                                              scenario_items: list,
                                              replaced_indices: list,
                                              refinement_request: str,
                                              context: str = "") -> str:
        """Generate response for scenario item replacement"""
        user_profile_context = self._extract_user_profile_prompt(context)
        
        # Format all items, marking which were replaced
        items_list = []
        for i, item in enumerate(scenario_items, 1):
            product = item.get("product")
            marker = " ✓ (updated)" if i in replaced_indices else ""
            if product:
                items_list.append(f"{i}. **{item['category']}**: {product.title[:70]} - ₹{product.price:,.0f}{marker}")
            else:
                items_list.append(f"{i}. **{item['category']}**: (No match found)")
        
        items_str = "\n".join(items_list)
        
        messages = [{
            "role": "system",
            "content": f"""You are a helpful shopping assistant updating a scenario-based recommendation.

{user_profile_context if user_profile_context else ''}

RULES:
1. Acknowledge the user's change request
2. Show the updated list with EXACT product titles/prices
3. Highlight what changed
4. Keep other items the same
5. Use Indian Rupee (₹) for prices"""
        }, {
            "role": "user",
            "content": f"""Scenario: {scenario_name}
User requested: "{refinement_request}"
Items replaced: {replaced_indices}

Updated recommendations:
{items_str}

Write a concise response acknowledging the change and showing the updated list."""
        }]
        
        return self.openai.generate_text(messages, max_tokens=500, temperature=0.3)

    def _format_products(self, products: List[Product]) -> str:
        """Format products for LLM context - optimized for Flipkart data"""
        formatted = []
        formatted.append("=" * 80)
        formatted.append(
            "AVAILABLE PRODUCTS IN OUR DATABASE (Use EXACT titles below):")
        formatted.append("=" * 80)
        formatted.append("")

        for i, p in enumerate(products[:5], 1):
            # Get key specs
            specs = p.specifications
            key_specs = []

            # Extract most useful specs
            for key in [
                    'Ideal For', 'Type', 'Fabric', 'Material', 'Color',
                    'Occasion', 'Pattern'
            ]:
                if specs.get(key):
                    key_specs.append(f"{key}: {specs[key]}")

            specs_str = " | ".join(key_specs[:4]) if key_specs else ""

            # Get discount info
            discount_info = ""
            if specs.get('MRP') and specs.get('Discount'):
                discount_info = f" (MRP: {specs['MRP']}, {specs['Discount']} off)"

            # Short description
            desc = p.description[:120] + "..." if len(
                p.description) > 120 else p.description

            formatted.append(f"""Product #{i}:
EXACT TITLE: {p.title[:80]}
EXACT PRICE: ₹{p.price:,.0f}{discount_info}
Category: {p.category}
Brand: {p.brand}
Specifications: {specs_str}
Description: {desc}
""")

        formatted.append("=" * 80)
        formatted.append(
            "END OF AVAILABLE PRODUCTS - DO NOT recommend products not listed above"
        )
        formatted.append("=" * 80)

        return "\n".join(formatted)
