from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import engine, Base
from app.models.property import Property
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.models.otp import CustomerOTP

from app.routers.property import router as property_router
from app.routers.customer import router as customer_router
from app.routers.enquiry import router as enquiry_router

# Ensure tables exist
Base.metadata.create_all(bind=engine)

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