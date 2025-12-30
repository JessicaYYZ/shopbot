"""
Import Amazon Products from Sales Dataset
~551K products from comprehensive Amazon catalog
"""

import sys
import os
import csv
import json
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import Database
from datetime import datetime

def clean_price(price_str):
    """Convert Indian Rupee price string to float"""
    try:
        if isinstance(price_str, (int, float)):
            return float(price_str)
        # Remove ₹, commas, and convert to float
        price_str = str(price_str).replace('₹', '').replace(',', '').strip()
        return float(price_str)
    except:
        return 0.0

def clean_rating(rating_str):
    """Convert rating string to float"""
    try:
        if isinstance(rating_str, (int, float)):
            return float(rating_str)
        rating_str = str(rating_str).strip()
        return float(rating_str) if rating_str else 0.0
    except:
        return 0.0

def clean_count(count_str):
    """Convert count string (e.g., '2,255') to int"""
    try:
        if isinstance(count_str, int):
            return count_str
        count_str = str(count_str).replace(',', '').strip()
        return int(count_str) if count_str else 0
    except:
        return 0

def extract_brand(name, category):
    """Extract brand from product name"""
    try:
        # Common patterns
        parts = name.split()
        if len(parts) > 0:
            # First word is often the brand
            brand = parts[0]
            # Clean up brand name
            brand = brand.replace('(', '').replace(')', '').strip()
            return brand if len(brand) > 1 else category
        return category
    except:
        return category

def generate_tags(name, main_category, sub_category):
    """Generate search tags from product attributes"""
    tags = []
    
    # Add categories as tags
    if main_category and main_category.lower() != 'nan':
        tags.append(main_category.lower())
    if sub_category and sub_category.lower() != 'nan':
        tags.append(sub_category.lower())
    
    # Extract keywords from name
    name_lower = name.lower()
    keywords = ['ac', 'inverter', 'split', 'window', 'portable', 'star', 'ton',
                'smart', 'led', 'wifi', 'wireless', 'bluetooth', 'usb', 'type-c',
                'cable', 'charger', 'fast', 'quick', 'power', 'bank', 'battery',
                'watch', 'fitness', 'tracker', 'band', 'earbuds', 'headphones',
                'speaker', 'soundbar', 'tv', 'television', 'laptop', 'tablet',
                'phone', 'mobile', 'case', 'cover', 'screen', 'protector',
                'camera', 'lens', 'tripod', 'bag', 'backpack', 'wallet',
                'shoes', 'sneakers', 'sandals', 'boots', 'clothing', 'shirt',
                'jeans', 'dress', 'jacket', 'coat', 'watch', 'jewellery']
    
    for keyword in keywords:
        if keyword in name_lower and keyword not in tags:
            tags.append(keyword)
    
    return tags[:15]  # Limit to 15 tags

def create_description(name, main_category, sub_category, rating, review_count):
    """Create a description from available data"""
    desc_parts = [name]
    
    if main_category and main_category != 'nan':
        desc_parts.append(f"Category: {main_category}")
    if sub_category and sub_category != 'nan':
        desc_parts.append(f"Type: {sub_category}")
    if rating > 0:
        desc_parts.append(f"Rating: {rating}⭐ ({review_count} reviews)")
    
    return ". ".join(desc_parts)

def import_amazon_products(csv_file_path: str, max_products: int = 100000):
    """Import Amazon products from CSV file"""
    
    print("🛍️ Amazon Products Importer (551K Dataset)")
    print("=" * 60)
    print()
    
    # Initialize database
    db_path = Path(__file__).parent.parent / 'data' / 'products.db'
    print(f"📁 Database: {db_path}")
    
    # Setup database schema
    print("🔧 Setting up database schema...")
    os.system(f"python {Path(__file__).parent / 'setup_db.py'}")
    
    db = Database(str(db_path))
    
    # Read CSV file
    print(f"\n📂 Reading CSV: {csv_file_path}")
    print(f"⏱️  This may take a while (551K products)...")
    print(f"📊 Limiting to: {max_products} products")
    print()
    
    products_added = 0
    products_skipped = 0
    seen_names = set()  # Track unique products by name
    
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader, 1):
            if products_added >= max_products:
                print(f"\n✅ Reached max products limit: {max_products}")
                break
            
            # Skip rows with missing essential data
            if not row.get('name') or not row.get('image'):
                products_skipped += 1
                continue
            
            # Skip duplicate names
            name = row['name'].strip()
            if name in seen_names:
                products_skipped += 1
                continue
            
            seen_names.add(name)
            
            try:
                # Parse product data
                main_category = row.get('main_category', '').strip()
                sub_category = row.get('sub_category', '').strip()
                image_url = row.get('image', '').strip()
                product_link = row.get('link', '').strip()
                
                # Parse pricing
                discount_price = clean_price(row.get('discount_price', 0))
                actual_price = clean_price(row.get('actual_price', 0))
                price = discount_price if discount_price > 0 else actual_price
                
                # Parse ratings
                rating = clean_rating(row.get('ratings', 0))
                review_count = clean_count(row.get('no_of_ratings', 0))
                
                # Extract brand
                brand = extract_brand(name, main_category)
                
                # Generate tags
                tags = generate_tags(name, main_category, sub_category)
                
                # Create description
                description = create_description(name, main_category, sub_category, rating, review_count)
                
                # Create specifications dict
                specifications = {}
                specifications['Main Category'] = main_category
                specifications['Sub Category'] = sub_category
                if actual_price != discount_price:
                    specifications['MRP'] = f"₹{actual_price:,.0f}"
                    specifications['Discount'] = f"{((actual_price - discount_price) / actual_price * 100):.0f}%"
                if product_link:
                    specifications['Amazon Link'] = product_link
                
                # Create product dict
                product_dict = {
                    'title': name[:500],  # Limit title length
                    'description': description[:1000],  # Limit description
                    'category': sub_category if sub_category else main_category,
                    'price': price,
                    'brand': brand,
                    'specifications': specifications,
                    'image_path': image_url,
                    'rating': rating,
                    'review_count': review_count,
                    'reviews': [],  # No review text in this dataset
                    'tags': tags,
                    'created_at': datetime.now().isoformat()
                }
                
                # Insert into database
                db.insert_product(product_dict)
                products_added += 1
                
                # Progress indicator
                if products_added % 1000 == 0:
                    print(f"   ✓ Imported {products_added:,} products...")
            
            except Exception as e:
                print(f"   ⚠️  Error importing row {i}: {e}")
                products_skipped += 1
                continue
    
    print(f"\n{'='*60}")
    print(f"✅ Import complete!")
    print(f"   📦 Products added: {products_added:,}")
    print(f"   ⏭️  Products skipped: {products_skipped:,}")
    
    # Display sample products
    print(f"\n📋 Sample products:")
    sample_products = db.get_all_products()
    for i, product in enumerate(sample_products[:5], 1):
        print(f"\n{i}. {product.title[:80]}")
        print(f"   💰 ₹{product.price:,.0f}")
        print(f"   ⭐ {product.rating}/5 ({product.review_count:,} reviews)")
        print(f"   🏷️  {product.brand} | {product.category}")
        print(f"   🎨 Tags: {', '.join(product.tags[:5])}")
    
    print(f"\n{'='*60}")
    print(f"📊 Total products in database: {db.count_products():,}")
    print()
    print("🎯 Next steps:")
    print("   1. Generate embeddings: python scripts/generate_embeddings.py")
    print("   2. Start the app: ./run.sh")
    print()
    print(f"⚠️  Note: Generating embeddings for {products_added:,} products will take ~3-5 hours")
    print()

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "Amazon_Products_Sales_Dataset/Amazon-Products.csv"
    max_products = int(sys.argv[2]) if len(sys.argv) > 2 else 600000  # Default to all products
    import_amazon_products(csv_file, max_products=max_products)

