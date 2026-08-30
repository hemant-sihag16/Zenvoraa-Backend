from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.enquiry import Enquiry
from app.models.property import Property
from app.models.customer import Customer
from app.schemas.enquiry import EnquiryCreate, EnquiryStatusUpdate

router = APIRouter(tags=["Enquiries"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# 1. CREATE ENQUIRY
# ==========================================
@router.post("/enquiries")
def create_enquiry(
    enquiry: EnquiryCreate,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == enquiry.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    property_data = db.query(Property).filter(Property.id == enquiry.property_id).first()
    if not property_data:
        raise HTTPException(status_code=404, detail="Property not found")

    cust_loc = enquiry.customer_location or customer.city or customer.location or ""

    new_enquiry = Enquiry(
        customer_id=enquiry.customer_id,
        property_id=enquiry.property_id,
        message=enquiry.message.strip(),
        customer_location=cust_loc,
        status="Pending"
    )

    db.add(new_enquiry)
    db.commit()
    db.refresh(new_enquiry)

    return {
        "success": True,
        "message": "Enquiry sent successfully! Our team and property owner will reach out shortly. 📩",
        "enquiry": {
            "id": new_enquiry.id,
            "customer_id": new_enquiry.customer_id,
            "property_id": new_enquiry.property_id,
            "message": new_enquiry.message,
            "status": new_enquiry.status,
            "customer_location": new_enquiry.customer_location,
            "created_at": new_enquiry.created_at
        }
    }


# ==========================================
# 2. GET ALL ENQUIRIES (ADMIN & SUPER ADMIN ONLY)
# ==========================================
@router.get("/enquiries")
def get_all_enquiries(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Enquiry)
    if status:
        query = query.filter(Enquiry.status == status)

    enquiries = query.order_by(Enquiry.created_at.desc()).all()

    data = []
    for e in enquiries:
        prop = db.query(Property).filter(Property.id == e.property_id).first()
        cust = db.query(Customer).filter(Customer.id == e.customer_id).first()

        data.append({
            "id": e.id,
            "customer_id": e.customer_id,
            "customer_name": cust.name if cust else "Unknown User",
            "customer_email": cust.email if cust else "N/A",
            "customer_phone": cust.phone if cust else "N/A",
            "customer_location": e.customer_location or (cust.city if cust else "Not Specified"),
            "property_id": e.property_id,
            "property_title": prop.title if prop else "Property Removed",
            "property_location": prop.location if prop else "",
            "property_price": prop.price if prop else 0,
            "is_property_verified": prop.is_verified if prop else False,
            "property_owner_id": prop.customer_id if prop else None,
            "message": e.message,
            "status": e.status,
            "admin_notes": e.admin_notes or "",
            "created_at": e.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "enquiries": data
    }


# ==========================================
# 3. GET CUSTOMER SENT ENQUIRIES
# ==========================================
@router.get("/enquiries/customer/{customer_id}")
def get_customer_enquiries(
    customer_id: int,
    db: Session = Depends(get_db)
):
    enquiries = db.query(Enquiry).filter(
        Enquiry.customer_id == customer_id
    ).order_by(Enquiry.created_at.desc()).all()

    data = []
    for e in enquiries:
        prop = db.query(Property).filter(Property.id == e.property_id).first()

        data.append({
            "id": e.id,
            "customer_id": e.customer_id,
            "property_id": e.property_id,
            "property_title": prop.title if prop else f"Property #{e.property_id}",
            "property_location": prop.location if prop else "",
            "property_price": prop.price if prop else 0,
            "property_image": prop.image_url if prop else None,
            "is_property_verified": prop.is_verified if prop else False,
            "message": e.message,
            "status": e.status,
            "admin_notes": e.admin_notes or "",
            "created_at": e.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "enquiries": data
    }


# ==========================================
# 4. GET HOUSE OWNER PROPERTY ENQUIRIES
# ==========================================
@router.get("/enquiries/owner/{owner_id}")
def get_house_owner_enquiries(
    owner_id: int,
    db: Session = Depends(get_db)
):
    # Find all properties belonging to this owner
    owner_props = db.query(Property).filter(Property.customer_id == owner_id).all()
    owner_prop_ids = [p.id for p in owner_props]

    if not owner_prop_ids:
        return {
            "success": True,
            "count": 0,
            "enquiries": []
        }

    enquiries = db.query(Enquiry).filter(
        Enquiry.property_id.in_(owner_prop_ids)
    ).order_by(Enquiry.created_at.desc()).all()

    data = []
    for e in enquiries:
        prop = db.query(Property).filter(Property.id == e.property_id).first()
        cust = db.query(Customer).filter(Customer.id == e.customer_id).first()

        data.append({
            "id": e.id,
            "property_id": e.property_id,
            "property_title": prop.title if prop else "Your Property",
            "property_location": prop.location if prop else "",
            "property_price": prop.price if prop else 0,
            "customer_id": e.customer_id,
            "customer_name": cust.name if cust else "Prospective Buyer/Tenant",
            "customer_phone": cust.phone if cust else "N/A",
            "customer_location": e.customer_location or (cust.city if cust else ""),
            "message": e.message,
            "status": e.status,
            "created_at": e.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "enquiries": data
    }


# ==========================================
# 5. UPDATE ENQUIRY STATUS (ADMIN / SUPER ADMIN)
# ==========================================
@router.put("/enquiries/{enquiry_id}/status")
def update_enquiry_status(
    enquiry_id: int,
    status: str = Query(...),
    admin_notes: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    enquiry = db.query(Enquiry).filter(Enquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    allowed_statuses = ["Pending", "Contacted", "In Progress", "Closed"]
    status_clean = status.strip().title()

    if status_clean not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(allowed_statuses)}"
        )

    enquiry.status = status_clean
    if admin_notes is not None:
        enquiry.admin_notes = admin_notes.strip()

    db.commit()
    db.refresh(enquiry)

    return {
        "success": True,
        "message": f"Enquiry status updated to '{enquiry.status}' successfully ✅",
        "enquiry_id": enquiry.id,
        "status": enquiry.status,
        "admin_notes": enquiry.admin_notes
    }


# ==========================================
# 6. DELETE ENQUIRY
# ==========================================
@router.delete("/enquiries/{enquiry_id}")
def delete_enquiry(
    enquiry_id: int,
    db: Session = Depends(get_db)
):
    enquiry = db.query(Enquiry).filter(Enquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    db.delete(enquiry)
    db.commit()

    return {
        "success": True,
        "message": "Enquiry deleted successfully",
        "deleted_enquiry_id": enquiry_id
    }