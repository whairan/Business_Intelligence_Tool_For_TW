from sqlalchemy import Column, Integer, String, Numeric
from geoalchemy2 import Geometry
from app.db.base import Base

class Parcel(Base):
    __tablename__ = "parcels"

    # Primary Key
    parcel_id = Column(String, primary_key=True, unique=True, index=True)
    site_address = Column(String)
    owner_name = Column(String)
    zoning_code = Column(String)
    
    # Financials
    land_value = Column(Numeric(15, 2))
    building_value = Column(Numeric(15, 2))
    total_value = Column(Numeric(15, 2))
    year_built = Column(Integer)
    acres = Column(Numeric(10, 4))
    
    # AI Scoring
    investment_score = Column(Numeric(5, 2), default=0.0)
    
    # Spatial Column
    geometry = Column(Geometry("MULTIPOLYGON", srid=4326))