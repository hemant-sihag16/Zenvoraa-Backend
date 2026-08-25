from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from app.database.connection import Base


class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)

    message = Column(String, nullable=False)

    status = Column(String, nullable=False, default="Pending")

    created_at = Column(DateTime, default=datetime.utcnow)