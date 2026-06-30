#!/usr/bin/env python3
"""
Script to clear MySQL foods table and import new dataset
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import pandas as pd

def main():
    csv_path = Path(__file__).parent / "data" / "food_dataset_fixed.csv"
    
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found at {csv_path}")
        return 1
    
    # Import after path is set
    from app.core.database import Base, SessionLocal, engine, wait_for_database
    from app.models.entities import Food
    from app.scripts.import_foods_csv import normalize_dataframe, import_foods
    from sqlalchemy import delete
    
    try:
        # Wait for database
        print("⏳ Waiting for database connection...")
        wait_for_database()
        print("✓ Database connected")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created")
        
        # Read and validate CSV
        print(f"📖 Reading CSV: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"✓ CSV loaded: {len(df)} rows")
        
        # Normalize
        print("🔄 Normalizing data...")
        normalized_df = normalize_dataframe(df)
        print(f"✓ Data normalized: {len(normalized_df)} rows")
        
        # Clear old data
        db = SessionLocal()
        try:
            print("🗑️  Clearing old foods table...")
            deleted = db.execute(delete(Food)).rowcount
            db.commit()
            print(f"✓ Deleted {deleted} rows from foods table")
        finally:
            db.close()
        
        # Import new data
        print("📥 Importing new data...")
        count = import_foods(csv_path, truncate=False, dry_run=False)
        print(f"✓ Imported {count} food items")
        
        # Verify
        db = SessionLocal()
        try:
            food_count = db.query(Food).count()
            print(f"\n✅ SUCCESS: {food_count} foods in database")
        finally:
            db.close()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
