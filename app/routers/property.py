import os
import random
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database.connection import SessionLocal
from app.models.property import Property
from app.models.customer import Customer
from app.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyStatusUpdate,
    PropertyVerificationSubmit,
    PropertyVerifyAction,
)
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

router = APIRouter(tags=["Properties"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# 1. GET ALL PROPERTIES (WITH FILTERS & GEO)
# ==========================================
@router.get("/properties")
def get_properties(
    purpose: Optional[str] = None,
    location: Optional[str] = None,
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    bedrooms: Optional[int] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    status: Optional[str] = None,
    verified_only: Optional[bool] = False,
    verification_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Property)

    if purpose:
        query = query.filter(Property.purpose == purpose.lower())

    if location:
        query = query.filter(Property.location.ilike(f"%{location.strip()}%"))

    if city:
        query = query.filter(Property.city.ilike(f"%{city.strip()}%"))

    if min_price is not None:
        query = query.filter(Property.price >= min_price)

    if max_price is not None:
        query = query.filter(Property.price <= max_price)

    if bedrooms is not None:
        query = query.filter(Property.bedrooms == bedrooms)

    if min_area is not None:
        query = query.filter(Property.area >= min_area)

    if max_area is not None:
        query = query.filter(Property.area <= max_area)

    if status:
        query = query.filter(Property.status == status)

    if verified_only:
        query = query.filter(Property.is_verified == True)

    if verification_status:
        query = query.filter(Property.verification_status == verification_status)

    properties = query.order_by(Property.created_at.desc()).all()

    data = []
    for p in properties:
        owner_name = None
        if p.customer_id:
            owner = db.query(Customer).filter(Customer.id == p.customer_id).first()
            if owner:
                owner_name = owner.name

        data.append({
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "city": p.city or "",
            "latitude": p.latitude,
            "longitude": p.longitude,
            "price": p.price,
            "bedrooms": p.bedrooms,
            "area": p.area,
            "purpose": p.purpose,
            "image_url": p.image_url,
            "description": p.description or "",
            "status": p.status,
            "customer_id": p.customer_id,
            "owner_name": owner_name,
            # Verification fields
            "is_verified": p.is_verified,
            "verification_status": p.verification_status or "unverified",
            "owner_legal_name": p.owner_legal_name,
            "registry_number": p.registry_number,
            "verified_at": p.verified_at,
            "created_at": p.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "properties": data
    }


# ==========================================
# 2. QUICK FILTER ROUTES
# ==========================================
@router.get("/properties/rent")
def get_rent_properties(db: Session = Depends(get_db)):
    return get_properties(purpose="rent", db=db)


@router.get("/properties/buy")
def get_buy_properties(db: Session = Depends(get_db)):
    return get_properties(purpose="buy", db=db)


@router.get("/properties/sell")
def get_sell_properties(db: Session = Depends(get_db)):
    return get_properties(purpose="sell", db=db)


# ==========================================
# 3. GET SINGLE PROPERTY
# ==========================================
@router.get("/properties/{property_id}")
def get_property(
    property_id: int,
    db: Session = Depends(get_db)
):
    property = db.query(Property).filter(Property.id == property_id).first()

    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    owner_info = None
    if property.customer_id:
        owner = db.query(Customer).filter(Customer.id == property.customer_id).first()
        if owner:
            owner_info = {
                "id": owner.id,
                "name": owner.name,
                "email": owner.email,
                "phone": owner.phone,
                "role": owner.role
            }

    return {
        "success": True,
        "property": {
            "id": property.id,
            "title": property.title,
            "location": property.location,
            "city": property.city or "",
            "latitude": property.latitude,
            "longitude": property.longitude,
            "price": property.price,
            "bedrooms": property.bedrooms,
            "area": property.area,
            "purpose": property.purpose,
            "status": property.status,
            "image_url": property.image_url,
            "description": property.description or "",
            "customer_id": property.customer_id,
            "owner": owner_info,
            # Verification status
            "is_verified": property.is_verified,
            "verification_status": property.verification_status or "unverified",
            "owner_legal_name": property.owner_legal_name,
            "registry_number": property.registry_number,
            "document_url": property.document_url,
            "verified_at": property.verified_at,
            "verified_by": property.verified_by,
            "verification_notes": property.verification_notes,
            "created_at": property.created_at
        }
    }


# ==========================================
# 4. PUBLIC PROPERTY AUTHENTICITY LOOKUP TOOL
# ==========================================
@router.get("/properties/verify-check/{lookup_query}")
def check_property_authenticity(
    lookup_query: str,
    db: Session = Depends(get_db)
):
    query_str = lookup_query.strip()

    # Search by property ID (numeric) or Registry Number / Title
    prop = None
    if query_str.isdigit():
        prop = db.query(Property).filter(Property.id == int(query_str)).first()

    if not prop:
        prop = db.query(Property).filter(
            or_(
                Property.registry_number.ilike(f"%{query_str}%"),
                Property.title.ilike(f"%{query_str}%")
            )
        ).first()

    if not prop:
        return {
            "success": False,
            "found": False,
            "message": f"No property found matching identifier '{query_str}'. Please check the Property ID or Registry number."
        }

    return {
        "success": True,
        "found": True,
        "verification": {
            "property_id": prop.id,
            "title": prop.title,
            "location": prop.location,
            "city": prop.city or "",
            "is_verified": prop.is_verified,
            "verification_status": prop.verification_status,
            "owner_legal_name": prop.owner_legal_name or "Not Registered on Record",
            "registry_number": prop.registry_number or "N/A",
            "price": prop.price,
            "purpose": prop.purpose,
            "status": prop.status,
            "verified_at": prop.verified_at,
            "verified_by": prop.verified_by or "Zenvoraa Legal Verification Team",
            "certificate_status": "AUTHENTIC & VERIFIED" if prop.is_verified else "UNVERIFIED / PENDING VERIFICATION"
        }
    }


# ==========================================
# 5. CREATE PROPERTY (HOUSE OWNER / SELLER)
# ==========================================
@router.post("/properties")
def create_property(
    property: PropertyCreate,
    db: Session = Depends(get_db)
):
    # Auto approximate coordinates if not provided based on city
    lat = property.latitude
    lng = property.longitude
    if not lat or not lng:
        # Default coords near India major real estate centers if unspecified
        lat = 26.9124 + round(random.uniform(-0.08, 0.08), 4)
        lng = 75.7873 + round(random.uniform(-0.08, 0.08), 4)

    new_property = Property(
        title=property.title.strip(),
        location=property.location.strip(),
        city=property.city.strip() if property.city else property.location.split(",")[-1].strip(),
        latitude=lat,
        longitude=lng,
        price=property.price,
        bedrooms=property.bedrooms,
        area=property.area,
        purpose=property.purpose.lower(),
        customer_id=property.customer_id,
        image_url=property.image_url,
        description=property.description,
        is_verified=False,
        verification_status="unverified"
    )

    db.add(new_property)
    db.commit()
    db.refresh(new_property)

    return {
        "success": True,
        "message": "Property listed successfully! You can now submit ownership verification documents.",
        "property": {
            "id": new_property.id,
            "title": new_property.title,
            "location": new_property.location,
            "city": new_property.city,
            "latitude": new_property.latitude,
            "longitude": new_property.longitude,
            "price": new_property.price,
            "bedrooms": new_property.bedrooms,
            "area": new_property.area,
            "purpose": new_property.purpose,
            "image_url": new_property.image_url,
            "customer_id": new_property.customer_id,
            "is_verified": new_property.is_verified,
            "verification_status": new_property.verification_status
        }
    }


# ==========================================
# 6. SUBMIT PROPERTY FOR VERIFICATION (HOUSE OWNER)
# ==========================================
@router.post("/properties/{property_id}/submit-verification")
def submit_property_verification(
    property_id: int,
    payload: PropertyVerificationSubmit,
    customer_id: int = Query(...),
    db: Session = Depends(get_db)
):
    property = db.query(Property).filter(Property.id == property_id).first()

    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Security check: only property owner can submit verification
    if property.customer_id != customer_id:
        # Check if user is super admin
        user = db.query(Customer).filter(Customer.id == customer_id).first()
        if not user or user.role != "super_admin":
            raise HTTPException(status_code=403, detail="You can only submit verification for your own property")

    property.owner_legal_name = payload.owner_legal_name.strip()
    property.registry_number = payload.registry_number.strip()
    if payload.document_url:
        property.document_url = payload.document_url
    if payload.notes:
        property.verification_notes = payload.notes

    property.verification_status = "pending"
    db.commit()
    db.refresh(property)

    return {
        "success": True,
        "message": "Property verification request submitted successfully! Admin will review within 24 hours.",
        "property": {
            "id": property.id,
            "title": property.title,
            "owner_legal_name": property.owner_legal_name,
            "registry_number": property.registry_number,
            "verification_status": property.verification_status
        }
    }


# ==========================================
# 7. ADMIN / OWNER VERIFY OR REJECT PROPERTY
# ==========================================
@router.put("/properties/{property_id}/verify")
def verify_property_action(
    property_id: int,
    action: PropertyVerifyAction,
    reviewer_id: int = Query(...),
    db: Session = Depends(get_db)
):
    reviewer = db.query(Customer).filter(Customer.id == reviewer_id).first()
    if not reviewer or reviewer.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Access Denied: Only Website Owner or Admins can verify properties"
        )

    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    target_status = action.status.lower()
    if target_status not in ["verified", "rejected", "pending"]:
        raise HTTPException(status_code=400, detail="Status must be 'verified', 'rejected' or 'pending'")

    if target_status == "verified":
        property.is_verified = True
        property.verification_status = "verified"
        property.verified_at = datetime.utcnow()
        property.verified_by = reviewer.name or action.verified_by or "Super Admin"
    elif target_status == "rejected":
        property.is_verified = False
        property.verification_status = "rejected"
    else:
        property.is_verified = False
        property.verification_status = "pending"

    if action.verification_notes:
        property.verification_notes = action.verification_notes

    db.commit()
    db.refresh(property)

    return {
        "success": True,
        "message": f"Property verification status updated to '{property.verification_status.upper()}' ✅",
        "property": {
            "id": property.id,
            "title": property.title,
            "is_verified": property.is_verified,
            "verification_status": property.verification_status,
            "owner_legal_name": property.owner_legal_name,
            "registry_number": property.registry_number,
            "verified_by": property.verified_by,
            "verified_at": property.verified_at
        }
    }


# ==========================================
# 8. UPDATE PROPERTY
# ==========================================
@router.put("/properties/{property_id}")
def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    customer_id: int = Query(...),
    db: Session = Depends(get_db)
):
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Security check: customer owns property or is super_admin
    user = db.query(Customer).filter(Customer.id == customer_id).first()
    if property.customer_id != customer_id and (not user or user.role != "super_admin"):
        raise HTTPException(status_code=403, detail="You can only update your own property")

    if property_data.title:
        property.title = property_data.title.strip()
    if property_data.location:
        property.location = property_data.location.strip()
    if property_data.city:
        property.city = property_data.city.strip()
    if property_data.price is not None:
        property.price = property_data.price
    if property_data.bedrooms is not None:
        property.bedrooms = property_data.bedrooms
    if property_data.area is not None:
        property.area = property_data.area
    if property_data.purpose:
        property.purpose = property_data.purpose.lower()
    if property_data.image_url:
        property.image_url = property_data.image_url
    if property_data.description is not None:
        property.description = property_data.description

    db.commit()
    db.refresh(property)

    return {
        "success": True,
        "message": "Property updated successfully",
        "property": {
            "id": property.id,
            "title": property.title,
            "location": property.location,
            "price": property.price,
            "bedrooms": property.bedrooms,
            "area": property.area,
            "purpose": property.purpose,
            "image_url": property.image_url,
            "customer_id": property.customer_id
        }
    }


# ==========================================
# 9. UPDATE PROPERTY STATUS (AVAILABLE / RENTED / SOLD)
# ==========================================
@router.put("/properties/{property_id}/status")
def update_property_status(
    property_id: int,
    status: str,
    customer_id: int = Query(...),
    db: Session = Depends(get_db)
):
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    user = db.query(Customer).filter(Customer.id == customer_id).first()
    if property.customer_id != customer_id and (not user or user.role not in ["super_admin", "admin"]):
        raise HTTPException(status_code=403, detail="You can only update your own property status")

    status_clean = status.strip().capitalize()
    if status_clean not in ["Available", "Rented", "Sold"]:
        raise HTTPException(status_code=400, detail="Status must be Available, Rented, or Sold")

    property.status = status_clean
    db.commit()
    db.refresh(property)

    return {
        "success": True,
        "message": f"Property status updated to {property.status}",
        "property": {
            "id": property.id,
            "title": property.title,
            "status": property.status
        }
    }


# ==========================================
# 10. DELETE PROPERTY
# ==========================================
@router.delete("/properties/{property_id}")
def delete_property(
    property_id: int,
    customer_id: int = Query(...),
    db: Session = Depends(get_db)
):
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    user = db.query(Customer).filter(Customer.id == customer_id).first()
    if property.customer_id != customer_id and (not user or user.role != "super_admin"):
        raise HTTPException(status_code=403, detail="You can only delete your own property")

    db.delete(property)
    db.commit()

    return {
        "success": True,
        "message": "Property deleted successfully"
    }


# ==========================================
# 11. GET CUSTOMER / HOUSE OWNER PROPERTIES
# ==========================================
@router.get("/properties/customer/{customer_id}")
def get_customer_properties(
    customer_id: int,
    db: Session = Depends(get_db)
):
    properties = db.query(Property).filter(
        Property.customer_id == customer_id
    ).order_by(Property.created_at.desc()).all()

    data = []
    for p in properties:
        data.append({
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "city": p.city or "",
            "price": p.price,
            "bedrooms": p.bedrooms,
            "area": p.area,
            "purpose": p.purpose,
            "status": p.status,
            "image_url": p.image_url,
            "customer_id": p.customer_id,
            "is_verified": p.is_verified,
            "verification_status": p.verification_status or "unverified",
            "owner_legal_name": p.owner_legal_name,
            "registry_number": p.registry_number,
            "document_url": p.document_url,
            "created_at": p.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "properties": data
    }


# ==========================================
# 12. UPLOAD IMAGE / DOCUMENT
# ==========================================
@router.post("/properties/upload-image")
async def upload_property_image(
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()

        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        if cloud_name:
            result = cloudinary.uploader.upload(
                contents,
                folder="zenvoraa/properties"
            )
            return {
                "success": True,
                "message": "Image uploaded successfully",
                "image_url": result["secure_url"]
            }
        else:
            # Fallback high quality placeholder
            return {
                "success": True,
                "message": "Image uploaded (placeholder mode)",
                "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=900&q=85"
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )