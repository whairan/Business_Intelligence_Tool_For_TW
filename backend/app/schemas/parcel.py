from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- INPUT SCHEMA ---
class LassoRequest(BaseModel):
    """
    The payload sent when a user draws a shape.
    """
    type: str = "Polygon"
    coordinates: List[List[List[float]]] = Field(
        ..., 
        description="GeoJSON coordinates of the lasso area [[[-122.5, 45.6], ...]]"
    )

# --- OUTPUT SCHEMAS ---
class ParcelResponse(BaseModel):
    """
    A single property returned to the frontend.
    """
    parcel_id: str
    address: Optional[str]
    owner_name: Optional[str]
    zoning_code: Optional[str]
    acres: Optional[float]
    market_value: Optional[float] = Field(alias="total_value")
    investment_score: Optional[float]
    
    # We return the geometry so the map can highlight individual lots
    geometry: Dict[str, Any] 

    class Config:
        from_attributes = True

class AreaAnalysisResponse(BaseModel):
    """
    The full dashboard data packet.
    """
    parcels: List[ParcelResponse]
    total_parcels: int
    average_score: float
    total_acreage: float
    ai_summary: Optional[str] = "Analysis pending..."