import uuid
from typing import Optional
from pydantic import BaseModel,EmailStr, Field


class CompanyBase(BaseModel):
    name: str
    code: str
    address: str
    pincode: str
    email: EmailStr
    mobile_no: str
    phone: Optional[str] = None
    gst_number: str

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str]
    code: Optional[str]
    address: Optional[str]
    pincode: Optional[str]
    email: Optional[EmailStr]
    mobile_no: Optional[str]
    phone: Optional[str]
    gst_number: Optional[str]

# New User Models
class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone: str
    gender: Optional[str]  # "male", "female", or "other"
    dob: str               # Date of Birth (format: YYYY-MM-DD)
    password: str

    role_id: Optional[str]  # Role ID for user role association
    company_id: str         # Company ID for associating the user with a company

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str]
    email: Optional[EmailStr]
    phone: Optional[str]
    gender: Optional[str]
    dob: Optional[str]
    password: Optional[str]

    role_id: Optional[str]
    company_id: Optional[str]
