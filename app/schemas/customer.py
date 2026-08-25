from pydantic import BaseModel


class CustomerCreate(BaseModel):
    name: str
    email: str
    phone: str
    password: str


class CustomerLogin(BaseModel):
    email: str
    password: str