import os
import zipfile
import shutil
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv 

# 1. Load Environment Variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

# --- CONFIGURATION ---
DOWNLOAD_DIR = "./temp_data"
ZIP_FILE_NAME = "Taxlots.zip" 
ZIP_PATH = os.path.join(DOWNLOAD_DIR, ZIP_FILE_NAME)

# Database Connection
DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "password123")
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = os.getenv("POSTGRES_DB", "clark_county_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- CRITICAL UPDATE: NEW COLUMN MAPPING ---
# Maps "Shapefile Column Name" -> "Your Database Column Name"
COLUMN_MAPPING = {
    "prop_id": "parcel_id",       # The Unique ID
    "SitusAddrs": "site_address", # Full Address
    "MainOwnerI": "owner_name",   # Owner Name
    "MktLandVal": "land_value",   # Market Land Value
    "MktBldgVal": "building_value", # Market Building Value
    "BldgYrBlt": "year_built",    # Year Built
    "GISAc": "acres",             # GIS Calculated Acres
    "Zone1": "zoning_code"        # Zoning Code
}

def process_and_load():
    if not os.path.exists(ZIP_PATH):
        print(f"❌ Error: Could not find {ZIP_PATH}")
        return

    print(f"📂 Found manual file: {ZIP_PATH}")
    
    with zipfile.ZipFile(ZIP_PATH, 'r') as z:
        z.extractall(DOWNLOAD_DIR)

    # 2. Find the Shapefile
    shp_path = None
    for root, dirs, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if "taxlot" in file.lower() and file.endswith(".shp"):
                shp_path = os.path.join(root, file)
                print(f"✅ Found Correct Shapefile: {file}")
                break
    
    if not shp_path:
        print("❌ Error: No 'Taxlots' shapefile found.")
        return

    print(f"📖 Reading Shapefile (this takes time)...")
    gdf = gpd.read_file(shp_path)
    
    # 3. Coordinate Transformation
    if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
        print(f"🔄 Reprojecting to WGS84...")
        gdf = gdf.to_crs(epsg=4326)

    # 4. Clean & Rename
    print("🧹 Cleaning data...")
    
    # Identify which columns from our mapping actually exist in the file
    existing_source_cols = [c for c in COLUMN_MAPPING.keys() if c in gdf.columns]
    
    if not existing_source_cols:
        print(f"❌ CRITICAL ERROR: No matching columns found. Expected: {list(COLUMN_MAPPING.keys())}")
        print(f"   Found in file: {gdf.columns.tolist()[:10]}...")
        return

    # Filter to keep only the columns we want + geometry
    gdf = gdf[existing_source_cols + ['geometry']]
    
    # Rename them to match the database schema
    gdf = gdf.rename(columns=COLUMN_MAPPING)
    
    # Convert 'nan' to SQL NULL
    gdf = gdf.where(pd.notnull(gdf), None)

    # 5. Load to DB
    engine = create_engine(DATABASE_URL)
    print(f"🚀 Loading {len(gdf)} parcels into PostGIS...")
    
    # We use chunksize to prevent memory crashes on 190k rows
    gdf.to_postgis(
        "parcels", 
        engine, 
        if_exists="replace", 
        index=False,
        dtype={'geometry': 'Geometry("MULTIPOLYGON", srid=4326)'},
        chunksize=1000
    )
    
    # 6. Restore Index
    with engine.connect() as conn:
        print("⚡ Re-creating Spatial Index...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parcels_geom ON parcels USING GIST (geometry);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parcels_parcel_id ON parcels(parcel_id);"))
        conn.commit()

    print("✅ Success! Database populated.")

if __name__ == "__main__":
    process_and_load()