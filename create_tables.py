from app.database.connection import engine, Base
from app.models.property import Property
from app.models.customer import Customer
from app.models.enquiry import Enquiry


print("Creating tables...")


Base.metadata.create_all(bind=engine)


print("✅ Tables created successfully!")