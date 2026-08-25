from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from app.database.connection import Base

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    location = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    bedrooms = Column(Integer)
    area = Column(Float)
    purpose = Column(String, nullable=False, default="sell")
    image_url = Column(String, nullable=True)

    status = Column(String, nullable=False, default="Available")

    created_at = Column(DateTime, default=datetime.utcnow)