"""
Import all CSV files from amazon_products_dataset folder
"""

import sys
import os
import csv
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import Database

def clean_price(price_str):
    """Convert Indian Rupee price string to float"""
    try:
        if isinstance(price_str, (int, float)):
            return float(price_str)
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
    """Convert count string to int"""
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
        parts = name.split()
        if len(parts) > 0:
            brand = parts[0].replace('(', '').replace(')', '').strip()
            return brand if len(brand) > 1 else category
        return category
    except:
        return category

def generate_tags(name, main_category, sub_category):
    """Generate search tags from product attributes"""
    tags = []
    if main_category and main_category.lower() != 'nan':
        tags.append(main_category.lower())
    if sub_category and sub_category.lower() != 'nan':
        tags.append(sub_category.lower())
    
    name_lower = name.lower()
    keywords = ['party', 'formal', 'casual', 'dress', 'shoes', 'jewellery', 'watch', 
                'bag', 'wallet', 'makeup', 'beauty', 'fashion', 'wear', 'accessories',
                'sandals', 'shirt', 'jeans', 'sunglasses', 'designer', 'luxury']
    
    for keyword in keywords:
        if keyword in name_lower and keyword not in tags:
            tags.append(keyword)
    
    return tags[:15]

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

def import_csv_file(csv_file_path: str, db: Database, global_seen_names: set = None):
    """Import all products from a single CSV file"""
    if global_seen_names is None:
        global_seen_names = set()
    
    products_added = 0
    products_skipped = 0
    seen_names = set()  # Track within this file for reporting
    
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader, 1):
            if not row.get('name') or not row.get('image'):
                products_skipped += 1
                continue
            
            name = row['name'].strip()
            name_lower = name.lower()
            
            # Check both within-file and cross-file duplicates
            if name_lower in global_seen_names or name_lower in seen_names:
                products_skipped += 1
                continue
            
            seen_names.add(name_lower)
            global_seen_names.add(name_lower)
            
            try:
                main_category = row.get('main_category', '').strip()
                sub_category = row.get('sub_category', '').strip()
                image_url = row.get('image', '').strip()
                product_link = row.get('link', '').strip()
                
                discount_price = clean_price(row.get('discount_price', 0))
                actual_price = clean_price(row.get('actual_price', 0))
                price = discount_price if discount_price > 0 else actual_price
                
                rating = clean_rating(row.get('ratings', 0))
                review_count = clean_count(row.get('no_of_ratings', 0))
                
                brand = extract_brand(name, main_category)
                tags = generate_tags(name, main_category, sub_category)
                description = create_description(name, main_category, sub_category, rating, review_count)
                
                specifications = {}
                specifications['Main Category'] = main_category
                specifications['Sub Category'] = sub_category
                if actual_price != discount_price and actual_price > 0:
                    specifications['MRP'] = f"₹{actual_price:,.0f}"
                    specifications['Discount'] = f"{((actual_price - discount_price) / actual_price * 100):.0f}%"
                if product_link:
                    specifications['Amazon Link'] = product_link
                
                product_dict = {
                    'title': name[:500],
                    'description': description[:1000],
                    'category': sub_category if sub_category else main_category,
                    'price': price,
                    'brand': brand,
                    'specifications': specifications,
                    'image_path': image_url,
                    'rating': rating,
                    'review_count': review_count,
                    'reviews': [],
                    'tags': tags,
                    'created_at': datetime.now().isoformat()
                }
                
                db.insert_product(product_dict)
                products_added += 1
                
                if products_added % 1000 == 0:
                    print(f"   ✓ Imported {products_added:,} products...")
            
            except Exception as e:
                products_skipped += 1
                continue
    
    print(f"   📊 Total valid products in file: {len(seen_names) + products_skipped}")
    return products_added, products_skipped

def main():
    """Import all CSV files from amazon_products_dataset"""
    dataset_folder = Path(__file__).parent.parent / 'amazon_products_dataset'
    
    if not dataset_folder.exists():
        print(f"❌ Dataset folder not found: {dataset_folder}")
        return
    
    csv_files = sorted(list(dataset_folder.glob('*.csv')))
    
    if not csv_files:
        print(f"❌ No CSV files found in {dataset_folder}")
        return
    
    db_path = Path(__file__).parent.parent / 'data' / 'products.db'
    db = Database(str(db_path))
    
    # Get existing product titles to avoid cross-file duplicates
    print("🔍 Checking existing products in database...")
    existing_products = set()
    try:
        existing = db.get_all_products()
        existing_products = {p.title.strip().lower() for p in existing}
        print(f"   Found {len(existing_products):,} existing products")
    except:
        pass
    
    print(f"\n📂 Found {len(csv_files)} CSV files to import")
    print(f"📁 Database: {db_path}")
    print(f"📦 Importing ALL products from each file")
    print(f"🛡️  Preventing duplicates across all files")
    print("=" * 60)
    print()
    
    total_imported = 0
    total_skipped = 0
    global_seen_names = existing_products.copy()  # Track across all files
    
    for i, csv_file in enumerate(csv_files, 1):
        print(f"\n{'='*60}")
        print(f"📦 Importing file {i}/{len(csv_files)}: {csv_file.name}")
        print(f"{'='*60}\n")
        
        try:
            added, skipped = import_csv_file(str(csv_file), db, global_seen_names)
            total_imported += added
            total_skipped += skipped
            print(f"\n✅ Completed: {csv_file.name}")
            print(f"   📦 Added: {added:,} | ⏭️  Skipped: {skipped:,}\n")
        except Exception as e:
            print(f"❌ Error importing {csv_file.name}: {e}\n")
            continue
    
    print(f"\n{'='*60}")
    print("🎉 All imports completed!")
    print(f"   📦 Total products added: {total_imported:,}")
    print(f"   ⏭️  Total products skipped: {total_skipped:,}")
    print(f"   📊 Total in database: {db.count_products():,}")
    print(f"{'='*60}\n")
    print("🎯 Next step: Generate embeddings")
    print("   python scripts/generate_embeddings.py")

if __name__ == "__main__":
    main()

