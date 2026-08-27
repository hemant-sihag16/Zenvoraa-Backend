import os
import random
from datetime import datetime, timedelta

import aiosmtplib
from email.message import EmailMessage

from app.models.otp import CustomerOTP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests

from app.database.connection import SessionLocal
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.schemas.customer import CustomerCreate, CustomerLogin

router = APIRouter(tags=["Customers"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# CUSTOMER REGISTER
# =========================

@router.post("/customers")
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    existing_customer = db.query(Customer).filter(
        Customer.email == customer.email
    ).first()

    if existing_customer:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_customer = Customer(
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        password=customer.password
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    return {
        "success": True,
        "message": "Customer registered successfully",
        "customer": {
            "id": new_customer.id,
            "name": new_customer.name,
            "email": new_customer.email,
            "phone": new_customer.phone
        }
    }


# =========================
# CUSTOMER LOGIN
# =========================

@router.post("/customers/login")
def customer_login(
    customer: CustomerLogin,
    db: Session = Depends(get_db)
):
    existing_customer = db.query(Customer).filter(
        Customer.email == customer.email
    ).first()

    if not existing_customer:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if existing_customer.password != customer.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "success": True,
        "message": "Login successful",
        "customer": {
            "id": existing_customer.id,
            "name": existing_customer.name,
            "email": existing_customer.email,
            "phone": existing_customer.phone
        }
    }


# =========================
# GET ALL CUSTOMERS
# =========================

@router.get("/customers")
def get_customers(
    db: Session = Depends(get_db)
):
    customers = db.query(Customer).all()

    data = []

    for c in customers:
        data.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone
        })

    return {
        "success": True,
        "count": len(data),
        "customers": data
    }


# =========================
# GET CUSTOMER BY ID
# =========================

@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        return {
            "success": False,
            "message": "Customer not found"
        }

    return {
        "success": True,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone
        }
    }
# =========================
# GET CUSTOMER ENQUIRIES
# =========================

@router.get("/customers/{customer_id}/enquiries")
def get_customer_enquiries(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    enquiries = db.query(Enquiry).filter(
        Enquiry.customer_id == customer_id
    ).all()

    data = []

    for enquiry in enquiries:
        data.append({
            "id": enquiry.id,
            "property_id": enquiry.property_id,
            "message": enquiry.message,
            "status": enquiry.status,
            "created_at": enquiry.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "enquiries": data
    }
# =========================
# SEND REGISTRATION OTP
# =========================

@router.post("/customers/send-otp")
async def send_registration_otp(
    email: str,
    db: Session = Depends(get_db)
):
    existing_customer = db.query(Customer).filter(
        Customer.email == email
    ).first()

    if existing_customer:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    otp = str(random.randint(100000, 999999))

    # Remove old OTPs for this email
    db.query(CustomerOTP).filter(
        CustomerOTP.email == email
    ).delete()

    new_otp = CustomerOTP(
        email=email,
        otp=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )

    db.add(new_otp)
    db.commit()

    resend_api_key = os.getenv("RESEND_API_KEY")

    if not resend_api_key:
        raise HTTPException(
            status_code=500,
            detail="Email service is not configured"
        )

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "from": "Zenvoraa <onboarding@resend.dev>",
            "to": [email],
            "subject": "Zenvoraa Registration OTP",
            "html": f"""
                <h2>Zenvoraa Registration</h2>
                <p>Your registration OTP is:</p>
                <h1>{otp}</h1>
                <p>This OTP is valid for 5 minutes.</p>
            """
        },
        timeout=20
    )

    if response.status_code >= 400:
     print("OTP API STATUS:", response.status_code)
     print("OTP API RESPONSE:", response.text)

    raise HTTPException(
        status_code=500,
        detail=f"Unable to send OTP email: {response.text}"
    )

    return {
        "success": True,
        "message": "OTP sent successfully"
    }