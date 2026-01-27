# app.py
# Business Intelligence Tool for Terry Wollam
# FIXED: Targets Layer 2 (Taxlots) instead of Layer 0 (Group)

from flask import Flask, request, jsonify, render_template
import requests
import json

app = Flask(__name__, static_folder="static", static_url_path="/static")

# ==========================================
# 1. ROBUST CONFIGURATION
# ==========================================

GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"

# CRITICAL FIX: Changed from /0/query to /2/query (Taxlots Layer)
CLARK_GIS_TAXLOTS = "https://gis.clark.wa.gov/arcgisfed2/rest/services/MapsOnline/LandRecords/MapServer/2/query"

DATA_COMMONS_API = "https://api.datacommons.org/stat/series"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def get_demographics(zip_code):
    """Fetches income/age data (Mocked if API fails)."""
    try:
        dc_geo = f"zip/{zip_code}"
        payload = {
            "places": [dc_geo],
            "stat_vars": ["Median_Income_Person", "Median_Age_Person"]
        }
        resp = requests.post(DATA_COMMONS_API, json=payload, timeout=3)
        data = resp.json()
        
        income = data['data'][dc_geo]['Median_Income_Person']['val'] if 'Median_Income_Person' in data['data'][dc_geo] else 75000
        age = data['data'][dc_geo]['Median_Age_Person']['val'] if 'Median_Age_Person' in data['data'][dc_geo] else 38
        
        return {
            "median_income": income,
            "median_age": age,
            "affordability_index": round(income / 2820 * 100, 2)
        }
    except:
        return {"median_income": 72000, "median_age": 39, "affordability_index": 115.5}

def format_currency(value):
    return f"${value:,.0f}" if value else "N/A"

# ==========================================
# 3. CORE LOGIC
# ==========================================

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/report")
def view_report():
    parcel = request.args.get("parcel")
    return render_template("report.html", parcel=parcel)

@app.route("/api/geocode")
def geocode():
    address = request.args.get("q", "").strip()
    if not address: return jsonify({"error": "address required"}), 400
    
    params = {"SingleLine": address, "f": "json", "outFields": "Match_addr,Addr_type", "maxLocations": 1}
    try:
        r = requests.get(GEOCODE_URL, params=params, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/find_parcel")
def find_parcel():
    """
    Robust Parcel Search targeting Layer 2 (Taxlots).
    """
    parcel_input = request.args.get("parcel")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    # --- SCENARIO A: Search by ID ---
    if parcel_input:
        # Clark County Taxlots (Layer 2) usually use 'SERIAL_NUM'
        # We try both Number and String formats to be safe.
        queries = [
            f"SERIAL_NUM = {parcel_input}",      # Number
            f"SERIAL_NUM = '{parcel_input}'",    # String
            f"PropertyID = {parcel_input}",      # Backup Field
            f"PARCELID = '{parcel_input}'"       # Backup Field
        ]

        for where_clause in queries:
            print(f"Trying Query on Layer 2: {where_clause}")
            params = {
                "where": where_clause,
                "outFields": "*",
                "f": "json",
                "returnGeometry": "true"
            }
            try:
                resp = requests.get(CLARK_GIS_TAXLOTS, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("features"):
                        print(f"✅ SUCCESS with: {where_clause}")
                        return jsonify({"result": data})
            except:
                continue
        
        return jsonify({"error": "Parcel not found in Taxlots (Layer 2)."}), 404

    # --- SCENARIO B: Search by Lat/Lon ---
    if lat and lon:
        print(f"Searching Layer 2 at Lat/Lon: {lat}, {lon}")
        geometry_string = f"{lon},{lat}"
        
        params = {
            "geometry": geometry_string,
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "f": "json",
            "returnGeometry": "true"
        }
        
        resp = requests.get(CLARK_GIS_TAXLOTS, params=params, timeout=10)
        data = resp.json()

        if data.get("features"):
            # Normalize the ID for the frontend
            feat = data['features'][0]
            # Ensure we return a clean ID even if the field name varies
            found_id = feat['attributes'].get('SERIAL_NUM') or feat['attributes'].get('PropertyID')
            if found_id:
                feat['attributes']['SERIAL_NUM'] = found_id # Standardize for frontend
            
            return jsonify({"result": data})
        else:
            return jsonify({"error": "No parcel found at this location"}), 404

    return jsonify({"error": "Provide parcel OR lat/lon"}), 400

@app.route("/api/links")
def links():
    pan = request.args.get("parcel")
    out = {}
    if pan:
        out["Property Information Center (PIC)"] = f"https://property.clark.wa.gov/?parcel={pan}"
        out["MapsOnline"] = f"https://gis.clark.wa.gov/mapsonline/?parcel={pan}"
        out["Recorded Documents (Auditor)"] = f"https://e-docs.clark.wa.gov/LandmarkWeb/?query={pan}"
        out["Generate Zonda Report"] = f"/report?parcel={pan}" 
    return jsonify(out)

@app.route("/api/generate_report_data")
def generate_report_data():
    parcel_id = request.args.get("parcel")
    
    # Direct Query on Layer 2
    params = {"where": f"SERIAL_NUM = {parcel_id}", "outFields": "*", "f": "json"}
    resp = requests.get(CLARK_GIS_TAXLOTS, params=params)
    data = resp.json()
    
    if not data.get("features"):
         return jsonify({"error": "Data not found"}), 404

    attrs = data['features'][0]['attributes']
    zip_code = str(attrs.get('ZipCode', '98607')).split('-')[0]
    
    report = {
        "project": {
            "name": attrs.get('SiteAddress') or attrs.get('SitusAddress', 'Unknown'),
            "city": attrs.get('City', 'Vancouver'),
            "zip": zip_code,
            "builder": "Wollam Custom (Mock)",
            "status": "Active"
        },
        "metrics": {
            "price": format_currency(attrs.get('SalePrice')),
            "sqft": f"{attrs.get('BldgSqFt', 0):,.0f}",
            "price_sqft": round(attrs.get('SalePrice', 0) / attrs.get('BldgSqFt', 1)) if attrs.get('BldgSqFt') else 0,
            "lot_size": f"{attrs.get('LandAcres', 0)} acres",
            "year_built": attrs.get('YearBuilt', 'N/A')
        },
        "demographics": get_demographics(zip_code),
        "location": {
            "lat": 45.63, "lon": -122.65 
        }
    }
    # Add geometry if available
    if 'geometry' in data['features'][0]:
        report['location']['lat'] = data['features'][0]['geometry'].get('y', 45.63)
        report['location']['lon'] = data['features'][0]['geometry'].get('x', -122.65)

    return jsonify(report)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)