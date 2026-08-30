import os
import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import requests

from app.database.connection import SessionLocal
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.models.property import Property
from app.models.otp import CustomerOTP
from app.schemas.customer import (
    CustomerCreate,
    CustomerLogin,
    CustomerRoleUpdate,
    CustomerUpdateProfile,
    SendOTPRequest,
    VerifyOTPRequest,
)
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

router = APIRouter(tags=["Customers"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# 1. SEND REGISTRATION OTP (EMAIL & PHONE UNIQUE CHECK)
# ==========================================
@router.post("/customers/send-otp")
async def send_registration_otp(
    payload: SendOTPRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.strip().lower() if payload.email else None
    phone = payload.phone.strip() if payload.phone else None

    if not email and not phone:
        raise HTTPException(
            status_code=400,
            detail="Email or phone number is required"
        )

    # 1 Email = 1 Register Check
    if email:
        existing_email = db.query(Customer).filter(Customer.email == email).first()
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="This email is already registered. Please login instead."
            )

    # 1 Phone = 1 Register Check
    if phone:
        existing_phone = db.query(Customer).filter(Customer.phone == phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=400,
                detail="This phone number is already registered. 1 phone number can register only once."
            )

    # Generate 6 digit numeric OTP
    otp = f"{random.randint(100000, 999999)}"

    # Clean old OTPs for this email/phone
    if email:
        db.query(CustomerOTP).filter(CustomerOTP.email == email).delete()
    if phone:
        db.query(CustomerOTP).filter(CustomerOTP.phone == phone).delete()

    new_otp = CustomerOTP(
        email=email,
        phone=phone,
        otp=otp,
        purpose=payload.purpose or "register",
        is_verified=False,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )

    db.add(new_otp)
    db.commit()

    email_sent = False
    error_note = None

    # Try sending via Resend API if configured
    resend_api_key = os.getenv("RESEND_API_KEY")
    if resend_api_key and email:
        try:
            res = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": "Zenvoraa <onboarding@resend.dev>",
                    "to": [email],
                    "subject": "Your Zenvoraa Verification OTP",
                    "html": f"""
                        <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
                            <h2 style="color: #2563eb;">🏠 Zenvoraa Smart Real Estate</h2>
                            <p>Hello,</p>
                            <p>Your One-Time Password (OTP) for registration is:</p>
                            <div style="background-color: #f1f5f9; padding: 15px; text-align: center; border-radius: 6px; margin: 20px 0;">
                                <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1e293b;">{otp}</span>
                            </div>
                            <p style="color: #64748b; font-size: 14px;">This OTP is valid for 10 minutes. For security reasons, do not share this OTP with anyone.</p>
                            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
                            <p style="color: #94a3b8; font-size: 12px;">Zenvoraa Platform © 2026</p>
                        </div>
                    """
                },
                timeout=15
            )
            if res.status_code < 400:
                email_sent = True
            else:
                error_note = res.text
        except Exception as ex:
            error_note = str(ex)

    return {
        "success": True,
        "message": f"OTP generated and sent to {email or phone}",
        "otp_sent_to": email or phone,
        "email_delivered": email_sent,
        "dev_otp": otp if not email_sent else None,
        "note": "Use dev_otp for local development or check your email inbox." if not email_sent else "OTP sent to your email."
    }


# ==========================================
# 2. VERIFY OTP
# ==========================================
@router.post("/customers/verify-otp")
def verify_registration_otp(
    payload: VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.strip().lower() if payload.email else None
    phone = payload.phone.strip() if payload.phone else None
    otp_entered = payload.otp.strip()

    query = db.query(CustomerOTP)
    if email:
        query = query.filter(CustomerOTP.email == email)
    elif phone:
        query = query.filter(CustomerOTP.phone == phone)
    else:
        raise HTTPException(status_code=400, detail="Email or phone is required")

    otp_record = query.order_by(CustomerOTP.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP requested for this contact")

    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new OTP.")

    if otp_record.otp != otp_entered:
        raise HTTPException(status_code=400, detail="Invalid OTP code. Please enter the correct 6-digit code.")

    otp_record.is_verified = True
    db.commit()

    return {
        "success": True,
        "message": "OTP verified successfully ✅"
    }


# ==========================================
# 3. REGISTER WITH OTP & UNIQUE CHECKS
# ==========================================
@router.post("/customers/register")
@router.post("/customers")
def register_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    email = customer.email.strip().lower()
    phone = customer.phone.strip()

    # 1. Unique Email Check
    if db.query(Customer).filter(Customer.email == email).first():
        raise HTTPException(
            status_code=400,
            detail="This email is already registered. 1 email can register only once."
        )

    # 2. Unique Phone Check
    if db.query(Customer).filter(Customer.phone == phone).first():
        raise HTTPException(
            status_code=400,
            detail="This phone number is already registered. 1 phone number can register only once."
        )

    # 3. OTP verification check (if OTP provided or required)
    if customer.otp:
        otp_rec = db.query(CustomerOTP).filter(
            (CustomerOTP.email == email) | (CustomerOTP.phone == phone)
        ).order_by(CustomerOTP.created_at.desc()).first()

        if not otp_rec or otp_rec.otp != customer.otp.strip():
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP code. Please verify your OTP before registering."
            )
        if datetime.utcnow() > otp_rec.expires_at:
            raise HTTPException(
                status_code=400,
                detail="OTP expired. Please request a fresh OTP."
            )

    # Allowed initial self-registration roles: customer or house_owner
    assigned_role = customer.role if customer.role in ["customer", "house_owner", "admin", "super_admin"] else "customer"

    # Website owner special check: first user or owner@zenvoraa can be super_admin
    total_users = db.query(Customer).count()
    if total_users == 0 or email in ["owner@zenvoraa.com", "superadmin@zenvoraa.com", "admin@zenvoraa.com"]:
        assigned_role = "super_admin"

    new_customer = Customer(
        name=customer.name.strip(),
        email=email,
        phone=phone,
        password=pwd_context.hash(customer.password),
        role=assigned_role,
        city=customer.city.strip() if customer.city else "",
        location=customer.location.strip() if customer.location else ""
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    # Delete OTP record after successful registration
    db.query(CustomerOTP).filter((CustomerOTP.email == email) | (CustomerOTP.phone == phone)).delete()
    db.commit()

    return {
        "success": True,
        "message": "Account registered successfully! Welcome to Zenvoraa 🚀",
        "customer": {
            "id": new_customer.id,
            "name": new_customer.name,
            "email": new_customer.email,
            "phone": new_customer.phone,
            "role": new_customer.role,
            "city": new_customer.city,
            "location": new_customer.location
        }
    }


# ==========================================
# 4. CUSTOMER LOGIN (EMAIL OR PHONE)
# ==========================================
@router.post("/customers/login")
def customer_login(
    customer: CustomerLogin,
    db: Session = Depends(get_db)
):
    login_id = customer.email.strip().lower()
    clean_phone = login_id.replace("+91", "").strip()
    with_plus91 = f"+91{clean_phone}" if clean_phone.isdigit() else login_id

    # Support login by email or phone (with or without +91)
    existing_customer = db.query(Customer).filter(
        (Customer.email == login_id) |
        (Customer.phone == login_id) |
        (Customer.phone == clean_phone) |
        (Customer.phone == with_plus91)
    ).first()

    if not existing_customer:
        raise HTTPException(
            status_code=401,
            detail="Account not found with this email or phone number"
        )

    if not pwd_context.verify(customer.password, existing_customer.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password. Please try again."
        )

    return {
        "success": True,
        "message": "Login successful 🎉",
        "customer": {
            "id": existing_customer.id,
            "name": existing_customer.name,
            "email": existing_customer.email,
            "phone": existing_customer.phone,
            "role": existing_customer.role or "customer",
            "city": existing_customer.city or "",
            "location": existing_customer.location or ""
        }
    }


# ==========================================
# 5. GET ALL USERS (SUPER ADMIN / OWNER ACCESS)
# ==========================================
@router.get("/customers")
def get_customers(
    role: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Customer)
    if role:
        query = query.filter(Customer.role == role)

    customers = query.order_by(Customer.created_at.desc()).all()

    data = []
    for c in customers:
        prop_count = db.query(Property).filter(Property.customer_id == c.id).count()
        enq_count = db.query(Enquiry).filter(Enquiry.customer_id == c.id).count()

        data.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "role": c.role or "customer",
            "city": c.city or "",
            "location": c.location or "",
            "properties_count": prop_count,
            "enquiries_count": enq_count,
            "created_at": c.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "customers": data
    }


# ==========================================
# 6. GET SINGLE USER
# ==========================================
@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "success": True,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "role": customer.role or "customer",
            "city": customer.city or "",
            "location": customer.location or "",
            "created_at": customer.created_at
        }
    }


# ==========================================
# 7. UPDATE USER ROLE (SUPER ADMIN / OWNER ONLY)
# ==========================================
@router.put("/customers/{customer_id}/role")
def update_user_role(
    customer_id: int,
    role_data: CustomerRoleUpdate,
    db: Session = Depends(get_db)
):
    valid_roles = ["super_admin", "admin", "house_owner", "customer"]
    if role_data.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="User not found")

    customer.role = role_data.role
    db.commit()
    db.refresh(customer)

    return {
        "success": True,
        "message": f"User role updated to '{customer.role}' successfully",
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "role": customer.role
        }
    }


# ==========================================
# 8. UPDATE PROFILE
# ==========================================
@router.put("/customers/{customer_id}/profile")
def update_customer_profile(
    customer_id: int,
    profile_data: CustomerUpdateProfile,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="User not found")

    if profile_data.name:
        customer.name = profile_data.name.strip()
    if profile_data.phone:
        existing_phone = db.query(Customer).filter(
            Customer.phone == profile_data.phone.strip(),
            Customer.id != customer_id
        ).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone number already in use by another account")
        customer.phone = profile_data.phone.strip()
    if profile_data.city is not None:
        customer.city = profile_data.city.strip()
    if profile_data.location is not None:
        customer.location = profile_data.location.strip()

    db.commit()
    db.refresh(customer)

    return {
        "success": True,
        "message": "Profile updated successfully",
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "role": customer.role,
            "city": customer.city,
            "location": customer.location
        }
    }


# ==========================================
# 9. PLATFORM OVERVIEW & ANALYTICS STATS
# ==========================================
@router.get("/customers/stats/overview")
def get_platform_overview_stats(
    db: Session = Depends(get_db)
):
    total_properties = db.query(Property).count()
    verified_properties = db.query(Property).filter(Property.is_verified == True).count()
    pending_verifications = db.query(Property).filter(Property.verification_status == "pending").count()
    available_properties = db.query(Property).filter(Property.status == "Available").count()

    total_customers = db.query(Customer).filter(Customer.role == "customer").count()
    total_house_owners = db.query(Customer).filter(Customer.role == "house_owner").count()
    total_admins = db.query(Customer).filter(Customer.role.in_(["admin", "super_admin"])).count()
    total_users = db.query(Customer).count()

    total_enquiries = db.query(Enquiry).count()
    pending_enquiries = db.query(Enquiry).filter(Enquiry.status == "Pending").count()
    contacted_enquiries = db.query(Enquiry).filter(Enquiry.status == "Contacted").count()
    closed_enquiries = db.query(Enquiry).filter(Enquiry.status == "Closed").count()

    return {
        "success": True,
        "properties": {
            "total": total_properties,
            "verified": verified_properties,
            "pending_verification": pending_verifications,
            "available": available_properties
        },
        "users": {
            "total": total_users,
            "customers": total_customers,
            "house_owners": total_house_owners,
            "admins": total_admins
        },
        "enquiries": {
            "total": total_enquiries,
            "pending": pending_enquiries,
            "contacted": contacted_enquiries,
            "closed": closed_enquiries
        }
    }


# ==========================================
# 10. SEED DEFAULT OWNER ACCOUNT
# ==========================================
@router.post("/customers/seed-owner")
def seed_default_owner(
    db: Session = Depends(get_db)
):
    # Primary Website Owner: govindkasnia42@gmail.com
    owner_email = "govindkasnia42@gmail.com"
    owner_phone = "9876543210"
    owner_pass = "Sihag@95186"

    owner = db.query(Customer).filter(
        (Customer.email == owner_email) | (Customer.phone == owner_phone)
    ).first()

    if not owner:
        owner = Customer(
            name="Govind Kasnia (Zenvoraa Owner)",
            email=owner_email,
            phone=owner_phone,
            password=pwd_context.hash(owner_pass),
            role="super_admin",
            city="Jaipur",
            location="Headquarters, Jaipur"
        )
        db.add(owner)
        db.commit()
        db.refresh(owner)
        return {
            "success": True,
            "message": "Website Owner (Super Admin) account created successfully 🎉",
            "email": owner_email,
            "phone": owner_phone,
            "role": "super_admin"
        }
    else:
        owner.name = "Govind Kasnia (Zenvoraa Owner)"
        owner.role = "super_admin"
        owner.email = owner_email
        owner.phone = owner_phone
        owner.password = pwd_context.hash(owner_pass)
        db.commit()
        return {
            "success": True,
            "message": "Website Owner account updated to Super Admin with latest password 🎉",
            "email": owner.email,
            "phone": owner.phone,
            "role": owner.role
        }
