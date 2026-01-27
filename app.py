# app.py
# Flask backend to query ArcGIS / Clark County feature services and return JSON
# Requirements: flask, requests
# Run: pip install flask requests
# Then: python app.py

from flask import Flask, request, jsonify
import requests
import os
import json
import socket

app = Flask(__name__, static_folder="static", static_url_path="/static")

# ---- CONFIG: endpoints (change if Clark County updates)
# ArcGIS World Geocoder (public)
GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"

# Clark County MapsOnline / LandRecords MapServer (example)
# We use a Taxlots/Parcels layer for geometry and attributes:
TAXLOTS_QUERY_URL = "https://gis.clark.wa.gov/arcgisfed2/rest/services/MapsOnline/LandRecords/MapServer/0/query"

# Clark County open-data assessor feature service (if available)
ASSESSOR_FEATURE_URL = "https://services.arcgis.com/.../arcgis/rest/services/Assessor_Property/FeatureServer/0/query"
# NOTE: replace ASSESSOR_FEATURE_URL with the county's actual assessor feature service endpoint if known.

# Utility: build a Clark County PIC link for a parcel (for user to click)
def make_pic_link(pan_or_parcel: str) -> str:
    # PIC often accepts tax account number (PAN) or parcel id
    return f"https://property.clark.wa.gov/?parcel={pan_or_parcel}"

# ---- routes ----

@app.route("/")
def index():
    # Serve static/index.html
    return app.send_static_file("index.html")

@app.route("/api/geocode")
def geocode():
    # q = address string
    address = request.args.get("q", "").strip()
    if not address:
        return jsonify({"error": "address required (q param)"}), 400

    params = {
        "SingleLine": address,
        "f": "json",
        "outFields": "Match_addr,Addr_type"
    }
    r = requests.get(GEOCODE_URL, params=params, timeout=15)
    r.raise_for_status()
    return jsonify(r.json())

@app.route("/api/find_parcel")
def find_parcel():
    # Accept either parcel number (PAN) or lat/lon to find parcel
    parcel = request.args.get("parcel")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    # ---- 1) by parcel id / PAN ----
    if parcel:
        # Try to query by PAN or PARCEL number field (try a few common fields)
        where_clauses = [
            f"PARCEL_NUMBER = '{parcel}'",
            f"PAN = '{parcel}'",
            f"TAXLOT = '{parcel}'",
            f"PARCELID = '{parcel}'",
        ]
        for where in where_clauses:
            params = {
                "where": where,
                "outFields": "*",
                "f": "json",
                "geometryPrecision": 5,
                "returnGeometry": "true",
            }
            resp = requests.get(TAXLOTS_QUERY_URL, params=params, timeout=15)
            if resp.ok:
                data = resp.json()
                if data.get("features"):
                    return jsonify({"source_where": where, "result": data})
        return jsonify({"error": "parcel not found in Taxlots layer"}), 404

    # ---- 2) by lat/lon (from geocoder) ----
    if lat and lon:
        try:
            latf = float(lat)
            lonf = float(lon)
        except ValueError:
            return jsonify({"error": "invalid lat/lon"}), 400

        geom = {"x": lonf, "y": latf, "spatialReference": {"wkid": 4326}}

        params = {
            "geometry": json.dumps(geom),          # << key fix: send JSON, not "x,y" string
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "f": "json",
            "returnGeometry": "true",
        }
        resp = requests.get(TAXLOTS_QUERY_URL, params=params, timeout=15)
        resp.raise_for_status()
        return jsonify(resp.json())

    return jsonify({"error": "provide parcel OR lat & lon"}), 400

@app.route("/api/assessor_by_parcel")
def assessor_by_parcel():
    # Query assessor open-data feature service by parcel id or by geometry
    parcel = request.args.get("parcel")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not parcel and (not lat or not lon):
        return jsonify({"error": "provide parcel or lat+lon"}), 400

    # Try parcel first if provided
    if parcel:
        where = f"PARCEL_ID = '{parcel}'"
        params = {"where": where, "outFields": "*", "f": "json"}
        # NOTE: ASSESSOR_FEATURE_URL placeholder must be updated to the real Clark County assessor feature service endpoint
        resp = requests.get(ASSESSOR_FEATURE_URL, params=params, timeout=15)
        if resp.ok and resp.json().get("features"):
            return jsonify(resp.json())
        # else fall through for lat/lon

    if lat and lon:
        try:
            latf = float(lat)
            lonf = float(lon)
        except ValueError:
            return jsonify({"error": "invalid lat/lon"}), 400

        geom = {"x": lonf, "y": latf, "spatialReference": {"wkid": 4326}}
        params = {
            "geometry": json.dumps(geom),
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "f": "json",
        }
        resp = requests.get(TAXLOTS_QUERY_URL, params=params, timeout=15)
        resp.raise_for_status()
        return jsonify(resp.json())

    return jsonify({"error": "no assessor data found"}), 404

# Simple helper to produce a recorded docs search link in Auditor system
@app.route("/api/links")
def links():
    pan = request.args.get("pan") or request.args.get("parcel")
    out = {}
    if pan:
        out["Property Information Center (PIC)"] = make_pic_link(pan)
        out["MapsOnline"] = f"https://gis.clark.wa.gov/mapsonline/?parcel={pan}"
        out["Recorded Documents (Auditor)"] = (
            f"https://e-docs.clark.wa.gov/LandmarkWeb/?query={pan}"
        )
    else:
        out["Property Information Center (PIC)"] = "https://property.clark.wa.gov"
    return jsonify(out)

# ---- app startup with auto free port ----
if __name__ == "__main__":
    def find_free_port(start=5000, end=5010):
        for port in range(start, end + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", port)) != 0:
                    return port
        raise RuntimeError("No free ports available in range.")

    env_port = os.environ.get("PORT")
    if env_port:
        port = int(env_port)
    else:
        port = find_free_port()

    print(f"\n🚀 Starting server on http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)