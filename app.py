# app.py
# Business Intelligence Tool for Terry Wollam
# Version: Developer Metrics + Zoning + RMLS Bridge

from flask import Flask, request, jsonify, render_template
import requests
import json
import os

app = Flask(__name__, static_folder="static", static_url_path="/static")

# ==========================================
# 1. DATA SOURCES & CONFIG
# ==========================================

DATA_SOURCES_FILE = "sources.json"
GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"

# Clark County GIS Layers
# Layer 2 = Taxlots (Property Data)
CLARK_GIS_TAXLOTS = "https://gis.clark.wa.gov/arcgisfed2/rest/services/MapsOnline/LandRecords/MapServer/2/query"
# Layer 28 = Zoning (This might vary, checking standard layer index)
# We will use a spatial query on the Zoning layer if needed, or extract from Taxlots if available there.
# Note: Clark County Taxlots usually contain a 'Zoning' field directly! We will use that first.

DATA_COMMONS_API = "https://api.datacommons.org/stat/series"

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def load_sources():
    """Reads the JSON list of data sources."""
    if not os.path.exists(DATA_SOURCES_FILE): return []
    with open(DATA_SOURCES_FILE, 'r') as f: return json.load(f)

def save_sources(sources):
    with open(DATA_SOURCES_FILE, 'w') as f: json.dump(sources, f, indent=2)

def get_demographics(zip_code):
    """Fetches income/age data (Mocked fallback if API fails)."""
    try:
        dc_geo = f"zip/{zip_code}"
        payload = {"places": [dc_geo], "stat_vars": ["Median_Income_Person", "Median_Age_Person"]}
        resp = requests.post(DATA_COMMONS_API, json=payload, timeout=2)
        data = resp.json()
        
        income = data['data'][dc_geo]['Median_Income_Person']['val'] if 'Median_Income_Person' in data['data'][dc_geo] else 75000
        age = data['data'][dc_geo]['Median_Age_Person']['val'] if 'Median_Age_Person' in data['data'][dc_geo] else 38
        
        return {"median_income": income, "median_age": age, "affordability_index": round(income / 2820 * 100, 2)}
    except:
        return {"median_income": 72000, "median_age": 39, "affordability_index": 115.5}

def get_rmls_data(parcel_id):
    """
    BRIDGE: Connects to RMLS API.
    Currently mocked because we need a valid RETS/WebAPI Key.
    """
    # TODO: Implement RMLS WebAPI connection here with Terry's Credentials.
    # For now, we return a "Market Pulse" based on the property status.
    return {
        "status": "Active",
        "days_on_market": 14,
        "list_price": 0, # Will fill with Tax Assessed if 0
        "mls_id": "24105500", # Fake ID
        "absorption_rate": 1.2 # "Seller's Market"
    }

# ==========================================
# 3. ROUTES
# ==========================================

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/report")
def view_report():
    parcel = request.args.get("parcel")
    return render_template("report.html", parcel=parcel)

@app.route("/api/sources", methods=["GET"])
def get_sources(): return jsonify(load_sources())

@app.route("/api/sources", methods=["POST"])
def add_source():
    new_source = request.json
    sources = load_sources()
    new_source["id"] = str(len(sources) + 1)
    new_source["active"] = True
    sources.append(new_source)
    save_sources(sources)
    return jsonify({"success": True})

@app.route("/api/sources/<source_id>/toggle", methods=["POST"])
def toggle_source(source_id):
    sources = load_sources()
    for s in sources:
        if s["id"] == source_id: s["active"] = not s["active"]
    save_sources(sources)
    return jsonify({"success": True})

@app.route("/api/geocode")
def geocode():
    address = request.args.get("q", "").strip()
    if not address: return jsonify({"error": "address required"}), 400
    params = {"SingleLine": address, "f": "json", "outFields": "Match_addr,Addr_type", "maxLocations": 1}
    try:
        r = requests.get(GEOCODE_URL, params=params, timeout=5)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/find_parcel")
def find_parcel():
    parcel = request.args.get("parcel")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    # 1. Search by Parcel ID
    if parcel:
        # Try both Number and String formats
        queries = [f"SERIAL_NUM = {parcel}", f"SERIAL_NUM = '{parcel}'", f"PropertyID = '{parcel}'"]
        for q in queries:
            try:
                resp = requests.get(CLARK_GIS_TAXLOTS, params={"where": q, "outFields": "*", "f": "json", "returnGeometry": "true"}, timeout=5)
                if resp.ok and resp.json().get("features"): return jsonify({"result": resp.json()})
            except: continue
        return jsonify({"error": "Parcel not found"}), 404

    # 2. Search by Lat/Lon
    if lat and lon:
        params = {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "f": "json", "returnGeometry": "true"}
        resp = requests.get(CLARK_GIS_TAXLOTS, params=params, timeout=5)
        return jsonify({"result": resp.json()}) if resp.json().get("features") else (jsonify({"error": "No parcel found"}), 404)


    # 3. Search by Legal Name
    ###Use cursor or Gemini or something to develop this part. 
    # Maybe using 


    return jsonify({"error": "Invalid input"}), 400

@app.route("/api/generate_report_data")
def generate_report_data():
    parcel_id = request.args.get("parcel")
    
    # 1. Get Core Parcel Data
    params = {"where": f"SERIAL_NUM = {parcel_id}", "outFields": "*", "f": "json"}
    resp = requests.get(CLARK_GIS_TAXLOTS, params=params)
    data = resp.json()
    
    if not data.get("features"):
        # Try fallback string query
        params["where"] = f"SERIAL_NUM = '{parcel_id}'"
        resp = requests.get(CLARK_GIS_TAXLOTS, params=params)
        data = resp.json()
    
    if not data.get("features"):
         return jsonify({"error": "Data not found"}), 404

    attrs = data['features'][0]['attributes']
    zip_code = str(attrs.get('ZipCode', '98607')).split('-')[0]
    
    # 2. Get External Data
    demographics = get_demographics(zip_code)
    rmls = get_rmls_data(parcel_id) # The "Bridge"
    
    # 3. Build Report JSON
    report = {
        "project": {
            "name": attrs.get('SiteAddress') or attrs.get('SitusAddress', 'Unknown'),
            "city": attrs.get('City', 'Vancouver'),
            "zip": zip_code,
            "builder": "Wollam Custom (Mock)",
            "status": "Active"
        },
        "metrics": {
            "price": f"${attrs.get('SalePrice', 0):,.0f}",
            "sqft": f"{attrs.get('BldgSqFt', 0):,.0f}",
            "lot_size": f"{attrs.get('LandAcres', 0)} acres",
            "year_built": attrs.get('YearBuilt', 'N/A'),
            # NEW: Developer Metrics
            "zoning": attrs.get('ZoningDescription') or attrs.get('Zoning') or "R1-6 (Assumed)",
            "comp_plan": attrs.get('ComprehensivePlan') or "Urban Low",
            "jurisdiction": attrs.get('Jurisdiction') or "Clark County"
        },
        "demographics": demographics,
        "market": rmls, # <--- RMLS Data Injection
        "location": {"lat": 45.63, "lon": -122.65}
    }
    
    if 'geometry' in data['features'][0]:
        report['location']['lat'] = data['features'][0]['geometry'].get('y', 45.63)
        report['location']['lon'] = data['features'][0]['geometry'].get('x', -122.65)

    return jsonify(report)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)