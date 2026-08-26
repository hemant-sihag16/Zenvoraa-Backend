from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.property import router as property_router
from app.routers.customer import router as customer_router
from app.routers.enquiry import router as enquiry_router


app = FastAPI(
    title="Zenvoraa API",
    description="Smart Real Estate Platform API",
    version="1.0.0"
)


# Allow React frontend to access FastAPI
app.add_middleware(
    CORSMiddleware,
  allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://zenvoraa-frontend.onrender.com"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "project": "Zenvoraa",
        "message": "Welcome to Zenvoraa 🚀",
        "developer": "Hemant Sihag",
        "status": "Running Successfully"
    }
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Zenvoraa API"
    }


app.include_router(property_router)
app.include_router(customer_router)
app.include_router(enquiry_router)