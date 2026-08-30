from pydantic import BaseModel
from typing import Optional


class EnquiryCreate(BaseModel):
    customer_id: int
    property_id: int
    message: str
    customer_location: Optional[str] = None


class EnquiryStatusUpdate(BaseModel):
    status: str
    admin_notes: Optional[str] = None