from pydantic import BaseModel
from typing import Optional


class PropertyCreate(BaseModel):
    title: str
    location: str
    city: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: float
    bedrooms: int = 1
    area: float = 0.0
    purpose: str = "sell"  # buy, rent, sell
    image_url: Optional[str] = None
    description: Optional[str] = None
    customer_id: int


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: Optional[float] = None
    bedrooms: Optional[int] = None
    area: Optional[float] = None
    purpose: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None


class PropertyStatusUpdate(BaseModel):
    status: str  # Available, Rented, Sold


class PropertyVerificationSubmit(BaseModel):
    owner_legal_name: str
    registry_number: str
    document_url: Optional[str] = None
    notes: Optional[str] = None


class PropertyVerifyAction(BaseModel):
    status: str  # verified, rejected
    verification_notes: Optional[str] = None
    verified_by: Optional[str] = "Admin"