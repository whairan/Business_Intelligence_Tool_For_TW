import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Any

from app.db.session import get_db
from app.schemas.parcel import LassoRequest, AreaAnalysisResponse, ParcelResponse
from app.models.parcel import Parcel

router = APIRouter()

@router.post("/analyze", response_model=AreaAnalysisResponse)
async def analyze_area(
    lasso: LassoRequest, 
    db: Session = Depends(get_db)
) -> Any:
    """
    Receives a GeoJSON polygon.
    Returns all parcels intersecting that polygon + aggregate stats.
    """
    
    # 1. Convert Pydantic model to raw GeoJSON string for PostGIS
    geojson_str = json.dumps(lasso.dict())

    # 2. The Spatial Query
    # ST_Intersects: Finds overlap
    # ST_AsGeoJSON: Converts DB geometry back to JSON for the frontend
    query = text("""
        SELECT 
            id, parcel_id, site_address, owner_name, zoning_code, 
            total_value, acres, investment_score,
            ST_AsGeoJSON(geometry) as geometry_json
        FROM parcels
        WHERE ST_Intersects(
            geometry, 
            ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
        )
        LIMIT 200; 
    """)
    
    # Execute query
    result = db.execute(query, {"geojson": geojson_str}).fetchall()

    if not result:
        return {
            "parcels": [],
            "total_parcels": 0,
            "average_score": 0.0,
            "total_acreage": 0.0,
            "ai_summary": "No parcels found in this selection."
        }

    # 3. Process Results
    parcels_data = []
    total_score = 0
    total_acres = 0

    for row in result:
        # Deserialize the geometry string from DB
        geom = json.loads(row.geometry_json)
        
        parcels_data.append(ParcelResponse(
            parcel_id=row.parcel_id,
            address=row.site_address,
            owner_name=row.owner_name,
            zoning_code=row.zoning_code,
            total_value=row.total_value,
            acres=row.acres,
            investment_score=row.investment_score,
            geometry=geom
        ))
        
        # Aggregate Stats
        if row.investment_score:
            total_score += float(row.investment_score)
        if row.acres:
            total_acres += float(row.acres)

    # 4. Final Aggregation
    avg_score = total_score / len(result) if result else 0
    
    return {
        "parcels": parcels_data,
        "total_parcels": len(parcels_data),
        "average_score": round(avg_score, 2),
        "total_acreage": round(total_acres, 2),
        "ai_summary": f"Identified {len(parcels_data)} lots. Dominant zoning appears to be Residential." 
        # ^ In the next step, we will replace this string with a call to OpenAI.
    }