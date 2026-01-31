from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter()

@router.post("/analyze-area")
async def analyze_area(lasso_polygon: dict, db: Session = Depends(get_db)):
    """
    Input: GeoJSON Polygon from Frontend Lasso
    Output: List of Parcels + AI Summary
    """
    # 1. Convert GeoJSON to WKT (Well-Known Text) for SQL
    wkt_polygon = convert_geojson_to_wkt(lasso_polygon)
    
    # 2. Run High-Speed Spatial Query
    query = text("""
        SELECT parcel_id, address, investment_score, ST_AsGeoJSON(geometry)
        FROM parcels
        WHERE ST_Intersects(geometry, ST_GeomFromText(:wkt, 4326))
        LIMIT 100;
    """)
    
    results = db.execute(query, {"wkt": wkt_polygon}).fetchall()
    
    # 3. Trigger Async AI Job (if area is large)
    if len(results) > 50:
        analyze_large_area_task.delay(lasso_polygon)
        
    return {"parcels": results}