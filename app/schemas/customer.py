from pydantic import BaseModel, EmailStr
from typing import Optional


class SendOTPRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    purpose: str = "register"  # register, login, verify


class VerifyOTPRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    otp: str
    purpose: str = "register"


class CustomerCreate(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    otp: Optional[str] = None
    role: Optional[str] = "customer"  # customer, house_owner
    city: Optional[str] = None
    location: Optional[str] = None


class CustomerLogin(BaseModel):
    email: str
    password: str


class CustomerRoleUpdate(BaseModel):
    role: str  # super_admin, admin, house_owner, customer


class CustomerUpdateProfile(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    location: Optional[str] = None