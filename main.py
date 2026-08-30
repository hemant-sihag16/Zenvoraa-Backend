from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import engine, Base, SessionLocal
from app.models.property import Property
from app.models.customer import Customer
from app.models.enquiry import Enquiry
from app.models.otp import CustomerOTP
from app.routers.property import router as property_router
from app.routers.customer import router as customer_router
from app.routers.enquiry import router as enquiry_router
from passlib.context import CryptContext
from sqlalchemy import text

# Ensure base tables exist
Base.metadata.create_all(bind=engine)

def auto_migrate_schema():
    """Ensure newly added columns exist in database without breaking on invalid transactions"""
    migration_statements = [
        # Customer table columns
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'customer';",
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS city VARCHAR DEFAULT '';",
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS location VARCHAR DEFAULT '';",
        
        # Property table columns
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS city VARCHAR DEFAULT 'Jaipur';",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS latitude FLOAT DEFAULT 26.9124;",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS longitude FLOAT DEFAULT 75.7873;",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS verification_status VARCHAR DEFAULT 'unverified';",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS owner_legal_name VARCHAR DEFAULT '';",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS registry_number VARCHAR DEFAULT '';",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS document_url VARCHAR DEFAULT '';",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS verified_by VARCHAR DEFAULT '';",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS verification_notes VARCHAR DEFAULT '';",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';",

        # Enquiry table columns
        "ALTER TABLE enquiries ADD COLUMN IF NOT EXISTS customer_location VARCHAR DEFAULT '';",
        "ALTER TABLE enquiries ADD COLUMN IF NOT EXISTS admin_notes TEXT DEFAULT '';",

        # OTP table columns
        "ALTER TABLE customer_otps ADD COLUMN IF NOT EXISTS phone VARCHAR DEFAULT '';",
        "ALTER TABLE customer_otps ADD COLUMN IF NOT EXISTS purpose VARCHAR DEFAULT 'registration';",
        "ALTER TABLE customer_otps ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;"
    ]

    try:
        with engine.connect() as conn:
            for stmt in migration_statements:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception:
                    conn.rollback()
        print("✅ Database schema auto-migration executed successfully")
    except Exception as e:
        print(f"Auto-migration notice: {e}")

# Run automatic schema migration
auto_migrate_schema()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_owner_on_startup():
    """Auto-seed or update the Website Owner (Super Admin) credentials on startup"""
    try:
        db = SessionLocal()
        # Delete user #9 if exists
        db.query(Customer).filter(Customer.id == 9).delete()

        # Update user #8 if exists
        user_8 = db.query(Customer).filter(Customer.id == 8).first()
        if user_8:
            user_8.phone = "9050978815"
            user_8.city = "Sirsa"
            user_8.location = "Sirsa, Haryana, India"

        owner_accounts = [
            {"email": "zenvoraa.support@gmail.com", "phone": "9050978815", "name": "Zenvoraa Official Support (Owner)"},
            {"email": "hemantsihag42@gmail.com", "phone": "9050978815", "name": "Hemant Sihag (Zenvoraa Owner)"},
            {"email": "owner@zenvoraa.com", "phone": "9000000000", "name": "Hemant Sihag (Zenvoraa Owner)"}
        ]
        owner_pass = "Sihag@95186"
        hashed = pwd_context.hash(owner_pass)

        for acc in owner_accounts:
            owner = db.query(Customer).filter(Customer.email == acc["email"]).first()
            if not owner:
                owner = Customer(
                    name=acc["name"],
                    email=acc["email"],
                    phone=acc["phone"],
                    password=hashed,
                    role="super_admin",
                    city="Sirsa",
                    location="Sirsa, Haryana, India"
                )
                db.add(owner)
            else:
                owner.name = acc["name"]
                owner.role = "super_admin"
                owner.phone = acc["phone"]
                owner.city = "Sirsa"
                owner.location = "Sirsa, Haryana, India"
                owner.password = hashed

        # Also rename any old Govind Kasnia entries or govind email if present
        govind_entries = db.query(Customer).filter(
            (Customer.name.like("%Govind%")) | (Customer.email.like("%govind%"))
        ).all()
        for g in govind_entries:
            g.name = "Hemant Sihag (Zenvoraa Owner)"
            g.email = "hemantsihag42@gmail.com"
            g.phone = "9050978815"
            g.city = "Sirsa"
            g.location = "Sirsa, Haryana, India"

        db.commit()
        db.close()
        print("🚀 Primary Website Owner updated: Hemant Sihag (zenvoraa.support@gmail.com)")
    except Exception as e:
        print(f"Seed notice: {e}")

# Run owner seed
seed_owner_on_startup()

app = FastAPI(
    title="Zenvoraa API",
    description="Smart Real Estate Platform API - RBAC, OTP Auth, Verification & Geo-Mapping",
    version="2.0.0"
)

# Allow React frontend to access FastAPI from any local or deployed domain
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://zenvoraa-frontend.onrender.com",
        "https://zenvoraa.onrender.com"
    ],
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