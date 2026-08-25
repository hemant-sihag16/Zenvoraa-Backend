from pydantic import BaseModel


class PropertyCreate(BaseModel):
    title: str
    location: str
    price: float
    bedrooms: int
    area: float
    purpose: str = "sell"
    image_url: str | None = None
    customer_id: int