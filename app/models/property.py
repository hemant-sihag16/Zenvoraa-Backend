from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from datetime import datetime

from app.database.connection import Base

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=True, index=True)
    title = Column(String, nullable=False)
    location = Column(String, nullable=False)
    city = Column(String, nullable=True, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    price = Column(Float, nullable=False)
    bedrooms = Column(Integer, default=1)
    area = Column(Float, default=0.0)
    purpose = Column(String, nullable=False, default="sell")  # buy, rent, sell
    image_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="Available")  # Available, Rented, Sold

    # Verification & Authenticity Tracking
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_status = Column(String, default="unverified", nullable=False)  # unverified, pending, verified, rejected
    owner_legal_name = Column(String, nullable=True)  # Name on official deed/registry
    registry_number = Column(String, nullable=True, index=True)  # Official deed / registry / khasra ID
    document_url = Column(String, nullable=True)  # Uploaded registry deed or proof
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)
    verification_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)