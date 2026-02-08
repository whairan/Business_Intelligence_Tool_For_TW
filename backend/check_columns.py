import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Get password from .env (handle both naming conventions)
password = os.getenv("POSTGRES_PASSWORD") 
user = os.getenv("POSTGRES_USER", "admin")
db_name = os.getenv("POSTGRES_DB", "clark_county_db")

# Connect
DATABASE_URL = f"postgresql://{user}:{password}@localhost:5432/{db_name}"
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        # Get all column names from the 'parcels' table
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'parcels';
        """))
        
        print("\n✅ ACTUAL COLUMNS IN DATABASE:")
        print("-----------------------------")
        found_any = False
        for row in result:
            print(f" - {row[0]}")
            found_any = True
            
        if not found_any:
            print("❌ No columns found! Does the 'parcels' table exist?")

except Exception as e:
    print(f"❌ Connection failed: {e}")