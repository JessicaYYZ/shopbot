"""
Remove duplicate products from database
Keeps only the first occurrence of each product title
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import Database

def remove_duplicates():
    """Remove duplicate products, keeping only first occurrence"""
    
    print("🧹 Removing Duplicate Products")
    print("=" * 50)
    
    db_path = Path(__file__).parent.parent / 'data' / 'products.db'
    db = Database(str(db_path))
    
    # Get initial count
    with db.get_connection() as conn:
        initial_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        print(f"📊 Initial product count: {initial_count:,}")
        
        # Find duplicates
        print("\n🔍 Finding duplicates...")
        duplicates = conn.execute("""
            SELECT title, COUNT(*) as cnt 
            FROM products 
            GROUP BY title 
            HAVING cnt > 1
        """).fetchall()
        
        print(f"   Found {len(duplicates):,} unique titles with duplicates")
        total_dups = sum(count - 1 for _, count in duplicates)
        print(f"   Total duplicate entries to remove: {total_dups:,}")
        
        if total_dups == 0:
            print("\n✅ No duplicates found! Database is clean.")
            return
        
        # Remove duplicates - keep lowest ID (first occurrence)
        print("\n🗑️  Removing duplicates...")
        conn.execute("""
            DELETE FROM products 
            WHERE rowid NOT IN (
                SELECT MIN(rowid) 
                FROM products 
                GROUP BY title
            )
        """)
        conn.commit()
        
        # Get final count
        final_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        removed = initial_count - final_count
        
        print(f"\n{'='*50}")
        print(f"✅ Cleanup complete!")
        print(f"   Before: {initial_count:,} products")
        print(f"   After:  {final_count:,} products")
        print(f"   Removed: {removed:,} duplicates")
        print(f"\n📊 Database now has {final_count:,} unique products")

if __name__ == "__main__":
    remove_duplicates()

