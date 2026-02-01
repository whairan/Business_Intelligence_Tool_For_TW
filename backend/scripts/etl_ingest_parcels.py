import os
import requests
import zipfile
import shutil
from io import BytesIO
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm

# --- CONFIGURATION ---
# Clark County GIS Open Data (Taxlots / Parcels)
# Note: This URL is the direct bulk download. If it changes, check: https://hub-clarkcountywa.opendata.arcgis.com/
DATA_URL = "https://gis.clark.wa.gov/gishome/dataset/download/Taxlots.zip"
DOWNLOAD_DIR = "./temp_data"
SHAPEFILE_NAME = "Taxlots.shp"  # The file inside the zip

# Database Connection (Matches your docker-compose & .env)
# If running outside docker, use localhost. If inside, use 'db'.
DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "password123")
DB_HOST = "localhost" 
DB_PORT = "5432"
DB_NAME = os.getenv("POSTGRES_DB", "clark_county_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Column Mapping (Shapefile Column -> Database Column)
COLUMN_MAPPING = {
    "SERIAL_NUM": "parcel_id",    # The APN
    "SITEADDR": "site_address",
    "OWNER": "owner_name",
    "LANDVAL": "land_value",
    "BLDGVAL": "building_value",
    "YRBUILT": "year_built",
    "ACRES": "acres",
    "ZONING": "zoning_code"
    # "geometry" is handled automatically by GeoPandas
}

def download_and_extract():
    """Downloads the zip file and extracts the shapefile."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    print(f"⬇️  Downloading data from {DATA_URL}...")
    response = requests.get(DATA_URL, stream=True)
    
    if response.status_code != 200:
        raise Exception(f"Failed to download: {response.status_code}")

    # Unzip
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        print("📂 Extracting files...")
        z.extractall(DOWNLOAD_DIR)
    
    print("✅ Download complete.")

def process_and_load():
    """Reads shapefile, transforms CRS, and loads to DB."""
    shp_path = os.path.join(DOWNLOAD_DIR, SHAPEFILE_NAME)
    
    if not os.path.exists(shp_path):
        # Fallback: sometimes the zip structure varies, find the first .shp
        for root, dirs, files in os.walk(DOWNLOAD_DIR):
            for file in files:
                if file.endswith(".shp"):
                    shp_path = os.path.join(root, file)
                    break
    
    print(f"📖 Reading Shapefile: {shp_path}...")
    gdf = gpd.read_file(shp_path)
    
    # 1. Coordinate Transformation (CRITICAL)
    # Clark County data is usually EPSG:2927 (NAD83 / WA South).
    # We MUST convert to EPSG:4326 (Lat/Lon) for Mapbox/PostGIS default.
    if gdf.crs.to_string() != "EPSG:4326":
        print("🔄 Reprojecting to WGS84 (Lat/Lon)...")
        gdf = gdf.to_crs(epsg=4326)

    # 2. Rename Columns
    print("🧹 Cleaning data...")
    # Keep only columns we mapped + geometry
    keep_cols = list(COLUMN_MAPPING.keys()) + ['geometry']
    # Filter only existing columns (avoid crash if schema changed)
    existing_cols = [c for c in keep_cols if c in gdf.columns]
    gdf = gdf[existing_cols]
    
    # Rename to match our DB schema
    gdf = gdf.rename(columns=COLUMN_MAPPING)
    
    # 3. Data Type Cleaning
    # Convert 'nan' owner names to None (NULL in SQL)
    gdf = gdf.where(pd.notnull(gdf), None)

    # 4. Connect to DB
    engine = create_engine(DATABASE_URL)
    
    print(f"🚀 Loading {len(gdf)} parcels into PostGIS...")
    
    # We use 'append' but chunks are recommended for 100k+ rows
    # GeoPandas to_postgis is slower but easiest to implement.
    gdf.to_postgis(
        "parcels", 
        engine, 
        if_exists="replace", # WARNING: This wipes existing data. Use 'append' for updates.
        index=False,
        dtype={'geometry': 'Geometry("MULTIPOLYGON", srid=4326)'},
        chunksize=1000  # Process in batches
    )
    
    # 5. Restore Indexes (replace drops them)
    with engine.connect() as conn:
        print("⚡ Re-creating Spatial Index...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parcels_geom ON parcels USING GIST (geometry);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parcels_parcel_id ON parcels(parcel_id);"))
        conn.commit()

    print("✅ Success! Database populated.")
    
    # Cleanup
    shutil.rmtree(DOWNLOAD_DIR)

if __name__ == "__main__":
    download_and_extract()
    process_and_load()