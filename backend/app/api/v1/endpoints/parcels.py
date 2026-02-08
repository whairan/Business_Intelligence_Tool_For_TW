from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from pydantic import BaseModel
from typing import List, Optional
import json

router = APIRouter()

# --- Request Models ---
class GeometryRequest(BaseModel):
    type: str
    coordinates: List[List[List[float]]]

# --- Endpoints ---

@router.post("/analyze")
def analyze_area(
    geo_request: GeometryRequest, 
    db: Session = Depends(get_db)
):
    """
    Analyze parcels within a drawn polygon.
    """
    # Convert the Pydantic model to a GeoJSON string for PostGIS
    geojson_str = json.dumps(geo_request.dict())
    
    # CORRECTED SQL: 
    # 1. Calculates 'total_value' on the fly (since the column doesn't exist)
    # 2. Removed 'investment_score' (since it doesn't exist yet)
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
    
    for row in results:
        # Convert row to dict
        p = dict(row._mapping)
        
        # Parse GeoJSON string so React can read it
        if p['geometry']:
            p['geometry'] = json.loads(p['geometry'])
            
        parcels_data.append(p)
        
        # Aggregate Stats
        if p['acres']:
            total_acres += float(p['acres'])
        if p['total_value']:
            total_value += float(p['total_value'])

    return {
        "total_parcels": len(parcels_data),
        "total_acreage": total_acres,
        "total_value": total_value,
        "average_score": 7.5, # Placeholder until we build the AI model
        "parcels": parcels_data,
        "ai_summary": f"Analyzed {len(parcels_data)} parcels. The data is now loading correctly from the database."
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
    # CORRECTED SQL for Lookup
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