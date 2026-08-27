from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database.connection import Base


class CustomerOTP(Base):
    __tablename__ = "customer_otps"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, nullable=False, index=True)

    otp = Column(String, nullable=False)

    expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)