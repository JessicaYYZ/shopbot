"""
Import Flipkart e-commerce dataset
"""

import sys
import os
import csv
import json
import re
import ast
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import Database


def clean_price(price_str):
    """Convert price string to float"""
    try:
        if isinstance(price_str, (int, float)):
            return float(price_str)
        price_str = str(price_str).replace(',', '').strip()
        return float(price_str) if price_str else 0.0
    except:
        return 0.0


def parse_category_tree(category_tree_str):
    """
    Parse the product_category_tree field.
    
    Format: ["Clothing >> Women's Clothing >> Shorts >> Product Name"]
    
    Returns: (main_category, sub_category, full_path)
    """
    try:
        if not category_tree_str or category_tree_str == 'nan':
            return ('', '', '')
        
        # Parse JSON array - the string is already valid JSON with double quotes
        try:
            category_list = json.loads(category_tree_str)
        except:
            # Fallback: try to extract the path manually
            # Format is like ["path >> here"]
            import re
            match = re.search(r'\["(.+?)"\]', category_tree_str)
            if match:
                category_list = [match.group(1)]
            else:
                return ('', '', str(category_tree_str)[:200])
        
        if not category_list or len(category_list) == 0:
            return ('', '', '')
        
        # Get the path string (first element of the array)
        path_str = category_list[0] if isinstance(category_list, list) else str(category_list)
        
        # Split by ">>" separator
        categories = [c.strip() for c in path_str.split('>>')]
        
        # Extract main category (first level)
        main_category = categories[0] if len(categories) > 0 else ''
        
        # Extract sub-category (second level, or third if second is too generic)
        sub_category = ''
        if len(categories) > 1:
            sub_category = categories[1]
        if len(categories) > 2 and sub_category in ['Men', 'Women', "Men's", "Women's"]:
            sub_category = categories[2]
        
        return (main_category, sub_category, path_str)
    
    except Exception as e:
        return ('', '', str(category_tree_str)[:200])


def parse_specifications(spec_str):
    """
    Parse the product_specifications field.
    
    Format is Ruby hash: {"product_specification"=>[{"key"=>"Fabric", "value"=>"Cotton"}]}
    
    Returns: dict of specifications
    """
    specs = {}
    
    try:
        if not spec_str or spec_str == 'nan' or pd.isna(spec_str) if 'pd' in dir() else False:
            return specs
        
        # Convert Ruby hash syntax to JSON
        # Replace => with :
        json_str = spec_str.replace('=>', ':')
        
        # Handle nil values
        json_str = json_str.replace(':nil', ':null')
        
        # Try to parse as JSON
        try:
            data = json.loads(json_str)
        except:
            # Try alternative parsing with ast
            try:
                # Replace Ruby syntax for Python eval
                py_str = spec_str.replace('=>', ':').replace('nil', 'None')
                data = ast.literal_eval(py_str)
            except:
                return specs
        
        # Extract specifications from the nested structure
        spec_list = data.get('product_specification', [])
        
        if not isinstance(spec_list, list):
            return specs
        
        misc_count = 0
        for item in spec_list:
            if not isinstance(item, dict):
                continue
            
            key = item.get('key', '')
            value = item.get('value', '')
            
            if key and value:
                # Clean up key name
                key = key.strip()
                specs[key] = str(value).strip()[:500]  # Limit value length
            elif value and not key:
                # Items with only value (no key)
                misc_count += 1
                if misc_count <= 3:  # Only keep first 3 misc notes
                    specs[f'Note {misc_count}'] = str(value).strip()[:200]
        
        return specs
    
    except Exception as e:
        return specs


def parse_images(image_str):
    """Parse image URLs from JSON array string"""
    try:
        if not image_str or image_str == 'nan':
            return ''
        
        # Parse JSON array
        images = json.loads(image_str.replace("'", '"'))
        
        if isinstance(images, list) and len(images) > 0:
            return images[0]  # Return first image
        return str(images)
    except:
        return str(image_str)[:500] if image_str else ''


def generate_tags(product_name, main_category, sub_category, brand):
    """Generate search tags from product attributes"""
    tags = []
    
    # Add category tags
    if main_category and main_category.lower() != 'nan':
        tags.append(main_category.lower())
    if sub_category and sub_category.lower() != 'nan':
        tags.append(sub_category.lower())
    if brand and brand.lower() != 'nan':
        tags.append(brand.lower())
    
    # Extract keywords from product name
    name_lower = product_name.lower()
    keywords = [
        'men', 'women', 'kids', 'baby', 'casual', 'formal', 'sports', 'running',
        'cotton', 'leather', 'silk', 'polyester', 'wool', 'denim',
        'shirt', 'jeans', 'dress', 'shoes', 'watch', 'bag', 'wallet',
        'phone', 'laptop', 'camera', 'headphone', 'speaker', 'tv', 'refrigerator',
        'furniture', 'sofa', 'bed', 'table', 'chair', 'kitchen', 'home',
        'beauty', 'skincare', 'makeup', 'jewellery', 'accessories'
    ]
    
    for keyword in keywords:
        if keyword in name_lower and keyword not in tags:
            tags.append(keyword)
    
    return tags[:15]  # Limit to 15 tags


def import_flipkart_dataset(csv_path: str, db: Database):
    """Import Flipkart dataset into database"""
    
    products_added = 0
    products_skipped = 0
    seen_names = set()
    
    # Get max field size for CSV
    csv.field_size_limit(sys.maxsize)
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader, 1):
            try:
                product_name = row.get('product_name', '').strip()
                
                if not product_name:
                    products_skipped += 1
                    continue
                
                # Check for duplicates
                name_lower = product_name.lower()
                if name_lower in seen_names:
                    products_skipped += 1
                    continue
                seen_names.add(name_lower)
                
                # Parse category tree
                main_category, sub_category, full_path = parse_category_tree(
                    row.get('product_category_tree', '')
                )
                
                # Parse prices
                retail_price = clean_price(row.get('retail_price', 0))
                discounted_price = clean_price(row.get('discounted_price', 0))
                price = discounted_price if discounted_price > 0 else retail_price
                
                # Parse image
                image_url = parse_images(row.get('image', ''))
                
                # Parse specifications
                specifications = parse_specifications(row.get('product_specifications', ''))
                
                # Add category path to specifications
                if full_path:
                    specifications['Category Path'] = full_path
                if main_category:
                    specifications['Main Category'] = main_category
                if sub_category:
                    specifications['Sub Category'] = sub_category
                
                # Add price info
                if retail_price != discounted_price and retail_price > 0:
                    specifications['MRP'] = f"₹{retail_price:,.0f}"
                    discount_pct = ((retail_price - discounted_price) / retail_price * 100)
                    specifications['Discount'] = f"{discount_pct:.0f}%"
                
                # Add product URL
                product_url = row.get('product_url', '').strip()
                if product_url:
                    specifications['Flipkart Link'] = product_url
                
                # Get brand
                brand = row.get('brand', '').strip()
                if not brand or brand.lower() == 'nan':
                    brand = product_name.split()[0] if product_name else 'Unknown'
                
                # Get description
                description = row.get('description', '').strip()
                if not description or description.lower() == 'nan':
                    description = f"{product_name}. {sub_category} in {main_category}."
                
                # Generate tags
                tags = generate_tags(product_name, main_category, sub_category, brand)
                
                # Create product dict
                product_dict = {
                    'title': product_name[:500],
                    'description': description[:2000],
                    'category': sub_category if sub_category else main_category,
                    'price': price,
                    'brand': brand,
                    'specifications': specifications,
                    'image_path': image_url,
                    'rating': 0.0,  # Flipkart dataset doesn't have ratings
                    'review_count': 0,
                    'reviews': [],
                    'tags': tags,
                    'created_at': datetime.now().isoformat()
                }
                
                db.insert_product(product_dict)
                products_added += 1
                
                if products_added % 5000 == 0:
                    print(f"   ✓ Imported {products_added:,} products...")
            
            except Exception as e:
                products_skipped += 1
                if products_skipped <= 5:
                    print(f"   ⚠️ Error on row {i}: {str(e)[:100]}")
                continue
    
    return products_added, products_skipped


def main():
    """Import Flipkart dataset"""
    
    csv_path = Path(__file__).parent.parent / 'flipkart_com-ecommerce_sample.csv'
    
    if not csv_path.exists():
        print(f"❌ Dataset not found: {csv_path}")
        return
    
    # Use new database for Flipkart data
    db_path = Path(__file__).parent.parent / 'data' / 'flipkart_products.db'
    
    print(f"\n{'='*60}")
    print("🛒 Flipkart E-commerce Dataset Import")
    print(f"{'='*60}")
    print(f"📂 Source: {csv_path.name}")
    print(f"📁 Database: {db_path}")
    print(f"{'='*60}\n")
    
    # Create fresh database
    if db_path.exists():
        print("⚠️  Removing existing Flipkart database...")
        os.remove(db_path)
    
    db = Database(str(db_path))
    
    print("🔄 Importing products...")
    added, skipped = import_flipkart_dataset(str(csv_path), db)
    
    print(f"\n{'='*60}")
    print("✅ Import completed!")
    print(f"   📦 Products added: {added:,}")
    print(f"   ⏭️  Products skipped: {skipped:,}")
    print(f"   📊 Total in database: {db.count_products():,}")
    print(f"{'='*60}\n")
    
    print("🎯 Next steps:")
    print("   1. Update .env to use the new database:")
    print('      DATABASE_PATH=data/flipkart_products.db')
    print('      VECTOR_STORE_PATH=vector_store_flipkart/')
    print("   2. Generate embeddings:")
    print("      python scripts/generate_embeddings.py")


if __name__ == "__main__":
    main()

