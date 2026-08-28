from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.property import Property
from app.schemas.property import PropertyCreate
import cloudinary
import cloudinary.uploader
import os

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


# GET ALL PROPERTIES
@router.get("/properties")
def get_properties(
    purpose: str = None,
    location: str = None,
    min_price: float = None,
    max_price: float = None,
    bedrooms: int = None,
    min_area: float = None,
    max_area: float = None,
    status: str = None,
    db: Session = Depends(get_db)
):

    query = db.query(Property)

    if purpose:
        query = query.filter(Property.purpose == purpose)

    if location:
        query = query.filter(Property.location == location)

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

    properties = query.all()

    data = []

    for p in properties:
        data.append({
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "price": p.price,
            "bedrooms": p.bedrooms,
            "area": p.area,
            "purpose": p.purpose,
           "image_url": p.image_url,
        })

    return {
        "success": True,
        "count": len(data),
        "properties": data
    }
@router.get("/properties/rent")
def get_rent_properties(db: Session = Depends(get_db)):

    properties = db.query(Property).filter(
        Property.purpose == "rent"
    ).all()

    data = []

    for p in properties:
        data.append({
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "price": p.price,
            "bedrooms": p.bedrooms,
            "area": p.area,
            "purpose": p.purpose,
            "image_url": p.image_url,
        })

    return {
        "success": True,
        "count": len(data),
        "properties": data
    }
@router.get("/properties/buy")
def get_buy_properties(db: Session = Depends(get_db)):

    properties = db.query(Property).filter(
        Property.purpose == "buy"
    ).all()

    data = []

    for p in properties:
        data.append({
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "price": p.price,
            "bedrooms": p.bedrooms,
            "area": p.area,
            "purpose": p.purpose,
            "image_url": p.image_url,
        })

    return {
        "success": True,
        "count": len(data),
        "properties": data
    }
@router.get("/properties/sell")
def get_sell_properties(db: Session = Depends(get_db)):

    properties = db.query(Property).filter(
        Property.purpose == "sell"
    ).all()

    data = []

    for p in properties:
        data.append({
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "price": p.price,
            "bedrooms": p.bedrooms,
            "area": p.area,
            "purpose": p.purpose,
            "image_url": p.image_url,
        })

    return {
        "success": True,
        "count": len(data),
        "properties": data
    }
@router.get("/properties/{property_id}")
def get_property(
    property_id: int,
    db: Session = Depends(get_db)
):

    property = db.query(Property).filter(
        Property.id == property_id
    ).first()

    if not property:
        return {
            "success": False,
            "message": "Property not found"
        }

    return {
        "success": True,
        "property": {
            "id": property.id,
            "title": property.title,
            "location": property.location,
            "price": property.price,
            "bedrooms": property.bedrooms,
            "area": property.area,
            "purpose": property.purpose,
            "status": property.status,
            "image_url": property.image_url,
        }
    }


# CREATE PROPERTY
@router.post("/properties")
def create_property(
    property: PropertyCreate,
    db: Session = Depends(get_db)
):

    new_property = Property(
        title=property.title,
        location=property.location,
        price=property.price,
        bedrooms=property.bedrooms,
        area=property.area,
        purpose=property.purpose,
        customer_id=property.customer_id,
        image_url=property.image_url
    )

    db.add(new_property)
    db.commit()
    db.refresh(new_property)

    return {
        "success": True,
        "message": "Property created successfully",
        "property": {
            "id": new_property.id,
            "title": new_property.title,
            "location": new_property.location,
            "price": new_property.price,
            "bedrooms": new_property.bedrooms,
            "area": new_property.area,
            "purpose": new_property.purpose,
        "image_url": new_property.image_url,
        "customer_id": new_property.customer_id 
        }
    }


# UPDATE PROPERTY
@router.put("/properties/{property_id}")
def update_property(
    property_id: int,
    property_data: PropertyCreate,
    customer_id: int,
    db: Session = Depends(get_db)
):

    property = db.query(Property).filter(
        Property.id == property_id
    ).first()

    if not property:
        return {
            "success": False,
            "message": "Property not found"
        }

    # Security: customer can update only their own property
    if property.customer_id != customer_id:
        return {
            "success": False,
            "message": "You can only update your own property"
        }

    property.title = property_data.title
    property.location = property_data.location
    property.price = property_data.price
    property.bedrooms = property_data.bedrooms
    property.area = property_data.area
    property.purpose = property_data.purpose
    property.image_url = property_data.image_url

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
# UPDATE PROPERTY STATUS
@router.put("/properties/{property_id}/status")
def update_property_status(
    property_id: int,
    status: str,
    customer_id: int,
    db: Session = Depends(get_db)
):

    property = db.query(Property).filter(
        Property.id == property_id
    ).first()

    if not property:
        return {
            "success": False,
            "message": "Property not found"
        }

    # Security: only property owner can change status
    if property.customer_id != customer_id:
        return {
            "success": False,
            "message": "You can only update your own property"
        }

    status = status.lower()

    if status not in ["available", "rented", "sold"]:
        return {
            "success": False,
            "message": "Status must be available, rented or sold"
        }

    property.status = status.capitalize()

    db.commit()
    db.refresh(property)

    return {
        "success": True,
        "message": "Property status updated successfully",
        "property": {
            "id": property.id,
            "title": property.title,
            "status": property.status
        }
    }
# DELETE PROPERTY
@router.delete("/properties/{property_id}")
def delete_property(
    property_id: int,
    customer_id: int,
    db: Session = Depends(get_db)
):

    property = db.query(Property).filter(
        Property.id == property_id
    ).first()

    if not property:
        return {
            "success": False,
            "message": "Property not found"
        }

    if property.customer_id != customer_id:
        return {
            "success": False,
            "message": "You can only delete your own property"
        }

    db.delete(property)
    db.commit()

    return {
        "success": True,
        "message": "Property deleted successfully"
    }
# GET CUSTOMER PROPERTIES
@router.get("/properties/customer/{customer_id}")
def get_customer_properties(
    customer_id: int,
    db: Session = Depends(get_db)
):

    properties = db.query(Property).filter(
        Property.customer_id == customer_id
    ).all()

    data = []

    for p in properties:
        data.append({
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "price": p.price,
            "bedrooms": p.bedrooms,
            "area": p.area,
            "purpose": p.purpose,
            "status": p.status,
            "image_url": p.image_url,
            "customer_id": p.customer_id,
            "status": p.status,
            "created_at": p.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "properties": data
    }
@router.post("/properties/upload-image")
async def upload_property_image(
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()

        result = cloudinary.uploader.upload(
            contents,
            folder="zenvoraa/properties"
        )

        return {
            "success": True,
            "message": "Image uploaded successfully",
            "image_url": result["secure_url"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )