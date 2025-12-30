"""
Generate embeddings for all products
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import Database
from src.models.openai_client import OpenAIClient
from src.models.vector_store import VectorStore
from dotenv import load_dotenv

load_dotenv()

def main():
    """Generate embeddings for all products using batch processing"""
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        return
    
    # Initialize components - Default to Flipkart database
    db_path = os.getenv("DATABASE_PATH", "data/flipkart_products.db")
    vector_store_path = os.getenv("VECTOR_STORE_PATH", "vector_store_flipkart/")
    
    if not os.path.exists(db_path):
        print("❌ Database not found. Please run setup_db.py first.")
        return
    
    database = Database(db_path)
    
    if database.count_products() == 0:
        print("❌ No products in database. Please run create_sample_data.py first.")
        return
    
    # Create vector store directory
    os.makedirs(vector_store_path, exist_ok=True)
    
    openai_client = OpenAIClient()
    vector_store = VectorStore(vector_store_path)
    
    print(f"📊 Found {database.count_products()} products")
    print(f"🔄 Generating embeddings using batch processing...")
    
    # Clear existing embeddings
    if vector_store.get_embedding_count() > 0:
        print(f"⚠️ Clearing {vector_store.get_embedding_count()} existing embeddings")
        vector_store.clear_collection()
    
    # Get all products
    products = database.get_all_products()
    
    success_count = 0
    error_count = 0
    start_time = time.time()
    
    # Process in batches for much better performance
    batch_size = 100  # Process 100 products at a time
    total_batches = (len(products) + batch_size - 1) // batch_size
    
    for batch_idx in range(0, len(products), batch_size):
        batch_products = products[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1
        
        try:
            # Prepare texts for batch
            texts = []
            for product in batch_products:
                text = f"{product.title}. {product.description}. Category: {product.category}. Brand: {product.brand}"
                if product.tags:
                    text += f". Tags: {', '.join(product.tags)}"
                
                # Include review comments for richer context
                if product.reviews and len(product.reviews) > 0:
                    review_texts = []
                    for review in product.reviews[:3]:
                        if isinstance(review, dict) and 'comment' in review:
                            review_texts.append(review['comment'])
                        elif hasattr(review, 'comment'):
                            review_texts.append(review.comment)
                    
                    if review_texts:
                        text += f". Customer reviews: {' '.join(review_texts)}"
                
                texts.append(text)
            
            # Generate embeddings for entire batch
            print(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch_products)} products)...")
            embeddings = openai_client.generate_embeddings_batch(texts)
            
            if not embeddings or len(embeddings) != len(batch_products):
                print(f"❌ Failed to generate embeddings for batch {batch_num}")
                error_count += len(batch_products)
                continue
            
            # Store embeddings
            for product, embedding, text in zip(batch_products, embeddings, texts):
                if not embedding:
                    print(f"  ❌ Empty embedding for: {product.title[:80]}")
                    error_count += 1
                    continue
                
                try:
                    metadata = {
                        "product_id": product.id,
                        "title": product.title,
                        "category": product.category,
                        "price": product.price,
                        "brand": product.brand,
                        "review_count": len(product.reviews) if product.reviews else 0
                    }
                    
                    vector_store.add_text_embedding(
                        product_id=product.id,
                        embedding=embedding,
                        metadata=metadata,
                        document=text
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"  ❌ Error storing embedding for {product.title[:80]}: {e}")
                    error_count += 1
            
            # Progress update
            elapsed = time.time() - start_time
            rate = success_count / elapsed if elapsed > 0 else 0
            estimated_remaining = (len(products) - success_count) / rate if rate > 0 else 0
            
            print(f"✅ Batch {batch_num}/{total_batches} complete!")
            print(f"📊 Progress: {success_count}/{len(products)} succeeded, {error_count} failed, {rate:.1f} products/sec, ~{estimated_remaining/60:.1f} min remaining\n")
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted by user at batch {batch_num}")
            print(f"📊 Processed {success_count} products successfully before interruption")
            raise
        except Exception as e:
            print(f"❌ Error processing batch {batch_num}: {e}")
            error_count += len(batch_products)
    
    elapsed_time = time.time() - start_time
    print(f"\n✅ Successfully generated {success_count} embeddings!")
    print(f"❌ Failed: {error_count}")
    print(f"⏱️  Total time: {elapsed_time/60:.1f} minutes")
    print(f"📊 Total embeddings in vector store: {vector_store.get_embedding_count()}")
    print("\n🎉 Embeddings generated successfully!")
    print("Next step: Run './run.sh' to start the application")
    print("Then visit: http://localhost:3000")

if __name__ == "__main__":
    main()

