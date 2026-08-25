from pydantic import BaseModel


class EnquiryCreate(BaseModel):
    customer_id: int
    property_id: int
    message: str
class EnquiryStatusUpdate(BaseModel):
    status: str