from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import engine, Base, SessionLocal
from app.models.property import Property
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.models.otp import CustomerOTP
from passlib.context import CryptContext

from app.routers.property import router as property_router
from app.routers.customer import router as customer_router
from app.routers.enquiry import router as enquiry_router

# Ensure tables exist
Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_owner_on_startup():
    """Auto-seed or update the Website Owner (Super Admin) credentials on startup"""
    try:
        db = SessionLocal()
        owner_email = "zenvoraa.support@gmail.com"
        owner_phone = "905078815"
        owner_pass = "Sihag@95186"

        owner = db.query(Customer).filter(
            (Customer.email == owner_email) | (Customer.phone == owner_phone)
        ).first()

        if not owner:
            owner = Customer(
                name="Hemant Sihag (Zenvoraa Owner)",
                email=owner_email,
                phone=owner_phone,
                password=pwd_context.hash(owner_pass),
                role="super_admin",
                city="Jaipur",
                location="Zenvoraa Headquarters, Jaipur"
            )
            db.add(owner)
            db.commit()
            print("🚀 Primary Website Owner seeded: zenvoraa.support@gmail.com")
        else:
            owner.role = "super_admin"
            owner.email = owner_email
            owner.phone = owner_phone
            owner.password = pwd_context.hash(owner_pass)
            db.commit()
            print("🚀 Primary Website Owner updated to super_admin")
        db.close()
    except Exception as e:
        print(f"Seed notice: {e}")

# Run owner seed
seed_owner_on_startup()

app = FastAPI(
    title="Zenvoraa API",
    description="Smart Real Estate Platform API - RBAC, OTP Auth, Verification & Geo-Mapping",
    version="2.0.0"
)

# Allow React frontend to access FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://zenvoraa-frontend.onrender.com"
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "project": "Zenvoraa",
        "message": "Welcome to Zenvoraa Smart Real Estate API 🚀",
        "features": [
            "OTP-based registration with unique email and phone constraints",
            "4-Tier RBAC (Super Admin / Owner, Admin, House Owner, Customer)",
            "Property Authenticity Verification with official badges & certificate check",
            "Interactive Geo-Location mapping for properties and inquiries"
        ],
        "status": "Running Successfully"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Zenvoraa API",
        "version": "2.0.0"
    }


app.include_router(property_router)
app.include_router(customer_router)
app.include_router(enquiry_router)