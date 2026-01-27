# app.py
# Business Intelligence Tool for Terry Wollam
# Version: Configurable Data Sources (JSON)

from flask import Flask, request, jsonify, render_template
import requests
import json
import os
import uuid  # For generating unique IDs for new sources

app = Flask(__name__, static_folder="static", static_url_path="/static")

# ==========================================
# 1. CONFIGURATION & FILE PATHS
# ==========================================

DATA_SOURCES_FILE = "data_sources.json"
GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
CLARK_GIS_TAXLOTS = "https://gis.clark.wa.gov/arcgisfed2/rest/services/MapsOnline/LandRecords/MapServer/2/query"
DATA_COMMONS_API = "https://api.datacommons.org/stat/series"

# ==========================================
# 2. DATA SOURCE MANAGER (NEW!)
# ==========================================

def load_sources():
    """Reads the JSON list of data sources."""
    if not os.path.exists(DATA_SOURCES_FILE):
        return []
    with open(DATA_SOURCES_FILE, 'r') as f:
        return json.load(f)

def save_sources(sources):
    """Writes the list back to the JSON file."""
    with open(DATA_SOURCES_FILE, 'w') as f:
        json.dump(sources, f, indent=2)

@app.route("/api/sources", methods=["GET"])
def get_sources():
    return jsonify(load_sources())

@app.route("/api/sources", methods=["POST"])
def add_source():
    """Adds a new source from the UI."""
    new_source = request.json
    sources = load_sources()
    
    # Simple validation
    if not new_source.get("name") or not new_source.get("url"):
        return jsonify({"error": "Name and URL required"}), 400
        
    new_source["id"] = str(uuid.uuid4())[:8] # Generate a short ID
    new_source["active"] = True
    sources.append(new_source)
    
    save_sources(sources)
    return jsonify({"success": True, "sources": sources})

@app.route("/api/sources/<source_id>", methods=["DELETE"])
def delete_source(source_id):
    """Removes a source."""
    sources = load_sources()
    sources = [s for s in sources if s["id"] != source_id]
    save_sources(sources)
    return jsonify({"success": True, "sources": sources})

@app.route("/api/sources/<source_id>/toggle", methods=["POST"])
def toggle_source(source_id):
    """Turns a source On/Off."""
    sources = load_sources()
    for s in sources:
        if s["id"] == source_id:
            s["active"] = not s["active"]
            break
    save_sources(sources)
    return jsonify({"success": True, "sources": sources})

# ==========================================
# 3. CORE LOGIC (EXISTING)
# ==========================================

# ... [Keep your existing helper functions like get_demographics here] ...
def get_demographics(zip_code):
    try:
        dc_geo = f"zip/{zip_code}"
        payload = {"places": [dc_geo], "stat_vars": ["Median_Income_Person", "Median_Age_Person"]}
        resp = requests.post(DATA_COMMONS_API, json=payload, timeout=3)
        data = resp.json()
        income = data['data'][dc_geo]['Median_Income_Person']['val'] if 'Median_Income_Person' in data['data'][dc_geo] else 75000
        age = data['data'][dc_geo]['Median_Age_Person']['val'] if 'Median_Age_Person' in data['data'][dc_geo] else 38
        return {"median_income": income, "median_age": age, "affordability_index": round(income / 2820 * 100, 2)}
    except:
        return {"median_income": 72000, "median_age": 39, "affordability_index": 115.5}

def format_currency(value):
    return f"${value:,.0f}" if value else "N/A"

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
    parcel_input = request.args.get("parcel")
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    
    if parcel_input:
        queries = [f"SERIAL_NUM = {parcel_input}", f"SERIAL_NUM = '{parcel_input}'", f"PropertyID = {parcel_input}"]
        for q in queries:
            try:
                resp = requests.get(CLARK_GIS_TAXLOTS, params={"where": q, "outFields": "*", "f": "json", "returnGeometry": "true"}, timeout=5)
                if resp.ok and resp.json().get("features"): return jsonify({"result": resp.json()})
            except: continue
        return jsonify({"error": "Parcel not found"}), 404

    if lat and lon:
        params = {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "f": "json", "returnGeometry": "true"}
        resp = requests.get(CLARK_GIS_TAXLOTS, params=params, timeout=10)
        return jsonify({"result": resp.json()}) if resp.json().get("features") else (jsonify({"error": "No parcel found"}), 404)

    return jsonify({"error": "Invalid request"}), 400

@app.route("/api/links")
def links():
    pan = request.args.get("parcel")
    out = {}
    if pan:
        out["Property Information Center (PIC)"] = f"https://property.clark.wa.gov/?parcel={pan}"
        out["MapsOnline"] = f"https://gis.clark.wa.gov/mapsonline/?parcel={pan}"
        out["Generate Zonda Report"] = f"/report?parcel={pan}"
    return jsonify(out)

@app.route("/api/generate_report_data")
def generate_report_data():
    parcel_id = request.args.get("parcel")
    # ... [Keep your existing report logic] ...
    # Fetch Basic Data
    params = {"where": f"SERIAL_NUM = {parcel_id}", "outFields": "*", "f": "json"}
    data = requests.get(CLARK_GIS_TAXLOTS, params=params).json()
    
    # Fetch Active Data Sources (This injects your JSON config into the report!)
    active_sources = [s for s in load_sources() if s['active']]

    if not data.get("features"): return jsonify({"error": "Data not found"}), 404
    attrs = data['features'][0]['attributes']
    zip_code = str(attrs.get('ZipCode', '98607')).split('-')[0]
    
    report = {
        "project": {
            "name": attrs.get('SiteAddress') or "Unknown",
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
        "location": {"lat": 45.63, "lon": -122.65},
        "sources_used": active_sources  # <--- NEW: Passed to frontend
    }
    return jsonify(report)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)