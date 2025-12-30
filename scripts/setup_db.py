"""
Initialize database schema
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import Database
from dotenv import load_dotenv

load_dotenv()

def main():
    """Initialize database"""
    # Get database path - Default to Flipkart database
    db_path = os.getenv("DATABASE_PATH", "data/flipkart_products.db")
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print(f"Initializing database at: {db_path}")
    
    # Initialize database
    db = Database(db_path)
    
    print("✅ Database schema created successfully!")
    print(f"📊 Current products count: {db.count_products()}")

if __name__ == "__main__":
    main()

