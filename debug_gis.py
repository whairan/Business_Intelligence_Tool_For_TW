import requests
import json

# The Base URL for Clark County Land Records
BASE_URL = "https://gis.clark.wa.gov/arcgisfed2/rest/services/MapsOnline/LandRecords/MapServer"

def diagnose():
    print("--- 1. CHECKING LAYERS ---")
    # Ask the server: "What layers do you have?"
    try:
        r = requests.get(f"{BASE_URL}?f=json", timeout=10)
        data = r.json()
        if "layers" in data:
            for layer in data["layers"]:
                print(f"ID: {layer['id']} | Name: {layer['name']}")
        else:
            print("ERROR: Could not list layers. Server might be down or URL is wrong.")
    except Exception as e:
        print(f"Connection Failed: {e}")
        return

    print("\n--- 2. CHECKING FIELDS (Layer 0) ---")
    # Ask the server: "What columns are in Layer 0?"
    try:
        r = requests.get(f"{BASE_URL}/0?f=json", timeout=10)
        data = r.json()
        if "fields" in data:
            print("Found these fields (Columns):")
            # List first 10 fields to see the naming convention
            for field in data["fields"][:15]: 
                print(f"- {field['name']} ({field['type']})")
        else:
            print("ERROR: Layer 0 has no fields.")
    except Exception as e:
        print(f"Connection Failed: {e}")

    print("\n--- 3. TEST QUERY (Known Parcel) ---")
    # Try a raw test on a parcel you provided
    test_parcel = "986035637"
    # Try common field names
    fields_to_try = ["SERIAL_NUM", "PARCEL_NUMBER", "PropertyID", "SN"]
    
    for field in fields_to_try:
        query_url = f"{BASE_URL}/0/query"
        params = {
            "where": f"{field} = '{test_parcel}'", # Try String
            "f": "json",
            "outFields": "*"
        }
        r = requests.get(query_url, params=params)
        data = r.json()
        if data.get("features"):
            print(f"✅ SUCCESS! The correct field name is: {field}")
            print(f"   Data Sample: {data['features'][0]['attributes']['SiteAddress']}")
            return
        
        # Try Number
        params["where"] = f"{field} = {test_parcel}"
        r = requests.get(query_url, params=params)
        data = r.json()
        if data.get("features"):
            print(f"✅ SUCCESS! The correct field name is: {field} (as Number)")
            return

    print("❌ FAILED: Could not find parcel with standard names.")

if __name__ == "__main__":
    diagnose()