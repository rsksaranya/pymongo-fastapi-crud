from fastapi import APIRouter, HTTPException, Depends
from pymongo import MongoClient, errors
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, Field
from datetime import datetime

# Initialize the router
router = APIRouter()

# Connect to MongoDB
try:
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
    db = client["companydb"]
    collection = db["companies"]
    client.server_info()  # Test database connection
except errors.ServerSelectionTimeoutError:
    raise HTTPException(status_code=500, detail="Database connection failed")

# Helper function to convert MongoDB object to JSON-friendly format
def company_helper(company) -> dict:
    return {
        "id": str(company["_id"]),
        "name": company["name"],
        "code": company["code"],
        "address": company["address"],
        "pincode": company["pincode"],
        "email": company["email"],
        "mobile_no": company["mobile_no"],
        "phone": company["phone"],
        "gst_number": company["gst_number"],
        "status": company["status"],
        "created_by": company.get("created_by"),
        "updated_by": company.get("updated_by"),
        "created_at": company.get("created_at"),
        "updated_at": company.get("updated_at")
    }

# Pydantic models for input validation
class CompanyCreate(BaseModel):
    name: str
    code: str
    address: str
    pincode: str
    email: str
    mobile_no: str
    phone: str
    gst_number: str
    created_by: str  # ID of the user creating the company

class CompanyUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    pincode: str | None = None
    email: str | None = None
    mobile_no: str | None = None
    phone: str | None = None
    gst_number: str | None = None
    updated_by: str  # ID of the user updating the company

### CRUD Endpoints ###

# Create a new company
@router.post("/companies", response_model=dict)
async def create_company(company: CompanyCreate):
    try:
        new_company = company.dict()
        new_company["status"] = 1
        new_company["created_at"] = datetime.utcnow()
        new_company["updated_at"] = None

        result = collection.insert_one(new_company)
        created_company = collection.find_one({"_id": result.inserted_id})
        return company_helper(created_company)
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Update an existing company
@router.put("/companies/{company_id}", response_model=dict)
async def update_company(company_id: str, company: CompanyUpdate):
    try:
        updated_data = {k: v for k, v in company.dict().items() if v is not None}
        updated_data["updated_at"] = datetime.utcnow()

        result = collection.update_one({"_id": ObjectId(company_id)}, {"$set": updated_data})
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Company not found")
        
        updated_company = collection.find_one({"_id": ObjectId(company_id)})
        return company_helper(updated_company)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Soft delete a company
@router.delete("/companies/{company_id}", response_model=dict)
async def delete_company(company_id: str, updated_by: str):
    try:
        result = collection.update_one(
            {"_id": ObjectId(company_id)},
            {"$set": {"status": 0, "updated_by": updated_by, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Company not found")
        
        deleted_company = collection.find_one({"_id": ObjectId(company_id)})
        return company_helper(deleted_company)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Retrieve all active companies
@router.get("/companies", response_model=list)
async def get_companies():
    try:
        companies = collection.find({"status": 1})
        return [company_helper(company) for company in companies]
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
