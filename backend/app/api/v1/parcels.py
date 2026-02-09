import os
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from pydantic import BaseModel
from typing import List
from openai import OpenAI  # <--- NEW: The AI Library

router = APIRouter()

# --- Initialize OpenAI ---
# It tries to get the key from your environment variables
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- Request Models ---
class GeometryRequest(BaseModel):
    type: str
    coordinates: List[List[List[float]]]

# --- AI Brain Function ---
def generate_shark_insight(parcel_count, total_acres, total_value, zoning_mix):
    """
    Sends stats to GPT-4o to get a ruthless developer analysis.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        return "AI Analysis Unavailable (Missing API Key in .env)"

    try:
        # Calculate avg value for context
        avg_val = total_value / parcel_count if parcel_count else 0
        
        prompt = f"""
        Act as a ruthless, high-stakes real estate developer named "Terry". 
        Analyze this land selection in Clark County, WA:
        
        - Total Parcels: {parcel_count}
        - Total Acres: {total_acres:.2f}
        - Total Value: ${total_value:,.2f}
        - Avg Parcel Value: ${avg_val:,.2f}
        - Zoning Breakdown: {zoning_mix}
        
        Give me a 3-sentence "Investment Verdict". 
        Be direct. Tell me if this is good for high-density development, flipping, or if I should stay away. 
        Focus on profit potential.
        """

        response = client.chat.completions.create(
            model="gpt-4o",  # Using the flagship model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "AI Brain is offline. (Check backend logs)"

# --- Endpoints ---

@router.post("/analyze")
def analyze_area(
    geo_request: GeometryRequest, 
    db: Session = Depends(get_db)
):
    """
    Analyze parcels within a drawn polygon and get AI insights.
    """
    geojson_str = json.dumps(geo_request.dict())
    
    # 1. THE SQL QUERY (Optimized for your database columns)
    query = text("""
        SELECT 
            parcel_id, 
            site_address, 
            owner_name, 
            zoning_code,
            land_value, 
            building_value, 
            (COALESCE(land_value, 0) + COALESCE(building_value, 0)) AS total_value,
            year_built, 
            acres,
            ST_AsGeoJSON(geometry) as geometry
        FROM parcels 
        WHERE ST_Intersects(geometry, ST_GeomFromGeoJSON(:geojson))
        LIMIT 500;
    """)
    
    try:
        results = db.execute(query, {"geojson": geojson_str}).fetchall()
    except Exception as e:
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    parcels_data = []
    total_acres = 0
    total_value = 0
    zoning_counts = {}

    # 2. PROCESS RESULTS
    for row in results:
        p = dict(row._mapping)
        
        if p['geometry']:
            p['geometry'] = json.loads(p['geometry'])
        parcels_data.append(p)
        
        # Aggregate Stats
        if p['acres']:
            total_acres += float(p['acres'])
        if p['total_value']:
            total_value += float(p['total_value'])
            
        # Count Zoning for the AI
        z_code = p['zoning_code'] or "Unknown"
        zoning_counts[z_code] = zoning_counts.get(z_code, 0) + 1

    # 3. CALL THE AI BRAIN
    ai_thought = generate_shark_insight(
        len(parcels_data), 
        total_acres, 
        total_value, 
        str(zoning_counts)
    )

    return {
        "total_parcels": len(parcels_data),
        "total_acreage": total_acres,
        "total_value": total_value,
        "average_score": 7.5, 
        "parcels": parcels_data,
        "ai_summary": ai_thought  # <--- The Real AI Response
    }

@router.get("/lookup")
def lookup_parcel(
    lat: float = Query(..., description="Latitude of the click"), 
    lng: float = Query(..., description="Longitude of the click"), 
    db: Session = Depends(get_db)
):
    """
    Find a single parcel by clicking coordinates (Lat/Lng).
    """
    query = text("""
        SELECT 
            parcel_id, 
            site_address, 
            owner_name, 
            zoning_code,
            land_value, 
            building_value, 
            (COALESCE(land_value, 0) + COALESCE(building_value, 0)) AS total_value,
            year_built, 
            acres,
            ST_AsGeoJSON(geometry) as geometry
        FROM parcels 
        WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
        LIMIT 1;
    """)
    
    try:
        result = db.execute(query, {"lat": lat, "lng": lng}).fetchone()
    except Exception as e:
        print(f"❌ Database Error in Lookup: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    if not result:
        return {"found": False, "message": "No parcel found here"}
        
    parcel = dict(result._mapping)
    
    if parcel['geometry']:
        parcel['geometry'] = json.loads(parcel['geometry'])
        
    return {"found": True, "data": parcel}