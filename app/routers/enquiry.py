from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import SessionLocal
from app.models.enquiry import Enquiry
from app.schemas.enquiry import EnquiryCreate, EnquiryStatusUpdate
from app.models.property import Property

router = APIRouter(tags=["Enquiries"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/enquiries")
def create_enquiry(
    enquiry: EnquiryCreate,
    db: Session = Depends(get_db)
):

    new_enquiry = Enquiry(
        customer_id=enquiry.customer_id,
        property_id=enquiry.property_id,
        message=enquiry.message
    )

    db.add(new_enquiry)
    db.commit()
    db.refresh(new_enquiry)

    return {
        "success": True,
        "message": "Enquiry created successfully",
        "enquiry": {
            "id": new_enquiry.id,
            "customer_id": new_enquiry.customer_id,
            "property_id": new_enquiry.property_id,
            "message": new_enquiry.message,
            "status": new_enquiry.status
        }
    }


@router.get("/enquiries")
def get_enquiries(
    db: Session = Depends(get_db)
):

    enquiries = db.query(Enquiry).all()

    data = []

    for e in enquiries:

        property_data = db.query(Property).filter(
            Property.id == e.property_id
        ).first()

        data.append({
            "id": e.id,
            "customer_id": e.customer_id,
            "property_id": e.property_id,
            "property_title": property_data.title if property_data else "Property",
            "property_location": property_data.location if property_data else "",
            "property_price": property_data.price if property_data else 0,
            "message": e.message,
            "status": e.status,
            "created_at": e.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "enquiries": data
    }

@router.put("/enquiries/{enquiry_id}")
def update_enquiry_status(
    enquiry_id: int,
    status_data: EnquiryStatusUpdate,
    db: Session = Depends(get_db)
):

    enquiry = db.query(Enquiry).filter(
        Enquiry.id == enquiry_id
    ).first()

    if not enquiry:
        return {
            "success": False,
            "message": "Enquiry not found"
        }

    enquiry.status = status_data.status

    db.commit()
    db.refresh(enquiry)

    return {
        "success": True,
        "message": "Enquiry status updated successfully",
        "enquiry": {
            "id": enquiry.id,
            "customer_id": enquiry.customer_id,
            "property_id": enquiry.property_id,
            "message": enquiry.message,
            "status": enquiry.status
        }
    }
@router.delete("/enquiries/{enquiry_id}")
def delete_enquiry(
    enquiry_id: int,
    db: Session = Depends(get_db)
):

    enquiry = db.query(Enquiry).filter(
        Enquiry.id == enquiry_id
    ).first()

    if not enquiry:
        return {
            "success": False,
            "message": "Enquiry not found"
        }

    db.delete(enquiry)
    db.commit()

    return {
        "success": True,
        "message": "Enquiry deleted successfully",
        "deleted_enquiry_id": enquiry_id
    }
@router.get("/enquiries/customer/{customer_id}")
def get_customer_enquiries(
    customer_id: int,
    db: Session = Depends(get_db)
):

    enquiries = db.query(Enquiry).filter(
        Enquiry.customer_id == customer_id
    ).all()

    data = []

    for e in enquiries:

        property_data = db.query(Property).filter(
            Property.id == e.property_id
        ).first()

        data.append({
            "id": e.id,
            "customer_id": e.customer_id,
            "property_id": e.property_id,
            "property_title": property_data.title if property_data else "Property",
            "property_location": property_data.location if property_data else "",
            "property_price": property_data.price if property_data else 0,
            "message": e.message,
            "status": e.status,
            "created_at": e.created_at
        })

    return {
        "success": True,
        "count": len(data),
        "enquiries": data
    }
@router.put("/enquiries/{enquiry_id}/status")
def update_enquiry_status(
    enquiry_id: int,
    status: str,
    db: Session = Depends(get_db)
):

    enquiry = db.query(Enquiry).filter(
        Enquiry.id == enquiry_id
    ).first()

    if not enquiry:
        raise HTTPException(
            status_code=404,
            detail="Enquiry not found"
        )

    allowed_statuses = ["Pending", "Contacted", "Closed"]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    enquiry.status = status

    db.commit()
    db.refresh(enquiry)

    return {
        "success": True,
        "message": "Enquiry status updated successfully",
        "enquiry_id": enquiry.id,
        "status": enquiry.status
    }