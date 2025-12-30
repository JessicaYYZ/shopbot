"""
OpenAI API Client Wrapper
"""

import os
import base64
import time
from typing import List, Dict
from openai import OpenAI
from PIL import Image
import io


class OpenAIClient:
    """Wrapper for OpenAI API calls"""
    
    def __init__(self):
        # Add timeout to prevent hanging
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0,  # 30 second timeout
            max_retries=2   # Retry up to 2 times
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    def generate_text(self, messages: List[Dict[str, str]], max_tokens: int = 300, 
                     temperature: float = 0.7) -> str:
        """Generate text using GPT-4o"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating text: {e}")
            return "I apologize, but I encountered an error. Please try again."
    
    def generate_embedding(self, text: str, retry_count: int = 3) -> List[float]:
        """Generate embedding vector for text with retry logic"""
        # Truncate text if too long (max ~8000 tokens for embedding model)
        max_chars = 30000  # Conservative estimate
        if len(text) > max_chars:
            text = text[:max_chars]
        
        for attempt in range(retry_count):
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2, 4, 6 seconds
                    print(f"⚠️  Error generating embedding (attempt {attempt + 1}/{retry_count}): {e}")
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Error generating embedding after {retry_count} attempts: {e}")
                    return []
        return []
    
    def generate_embeddings_batch(self, texts: List[str], retry_count: int = 3) -> List[List[float]]:
        """Generate embeddings for multiple texts in a single API call (faster and more efficient)"""
        # Truncate texts if too long
        max_chars = 30000
        truncated_texts = [text[:max_chars] if len(text) > max_chars else text for text in texts]
        
        for attempt in range(retry_count):
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=truncated_texts
                )
                # Return embeddings in the same order as input
                return [item.embedding for item in response.data]
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"⚠️  Error generating batch embeddings (attempt {attempt + 1}/{retry_count}): {e}")
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Error generating batch embeddings after {retry_count} attempts: {e}")
                    return [[] for _ in texts]  # Return empty embeddings for all
        return [[] for _ in texts]
    
    def analyze_image(self, image_path: str = None, image: Image.Image = None, 
                     prompt: str = None) -> str:
        """Analyze image using GPT-4o Vision"""
        try:
            # Convert image to base64
            if image:
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                image_data = base64.b64encode(buffered.getvalue()).decode('utf-8')
            elif image_path:
                with open(image_path, 'rb') as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
            else:
                return "No image provided"
            
            # Default prompt for product analysis
            if not prompt:
                prompt = """Analyze this product image and describe it for search purposes.
Include:
- Product type/category
- Colors
- Style features
- Brand (if visible)
- Key characteristics

Be concise and specific."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return "Could not analyze image"
    
    def image_to_embedding(self, image_path: str = None, image: Image.Image = None) -> List[float]:
        """Convert image to embedding via Vision API + Embeddings"""
        # Analyze image to get description
        description = self.analyze_image(image_path=image_path, image=image)
        # Convert description to embedding
        return self.generate_embedding(description)

