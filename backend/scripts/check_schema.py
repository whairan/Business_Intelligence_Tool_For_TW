import os
import geopandas as gpd

# Path to the unzipped file (from your logs)
SHP_PATH = "./temp_data/TaxlotsPublic.shp"

if not os.path.exists(SHP_PATH):
    # Fallback to search if specific name varies
    for root, dirs, files in os.walk("./temp_data"):
        for file in files:
            if file.endswith(".shp") and "taxlot" in file.lower():
                SHP_PATH = os.path.join(root, file)
                break

print(f"🕵️‍♀️ Inspecting: {SHP_PATH}")
try:
    # Read just the first row to get columns fast
    gdf = gpd.read_file(SHP_PATH, rows=1)
    print("\n👇 EXISTING COLUMNS 👇")
    print(gdf.columns.tolist())
    print("\n")
except Exception as e:
    print(f"Error: {e}")