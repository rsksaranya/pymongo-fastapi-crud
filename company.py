from fastapi import APIRouter, HTTPException
from pymongo import MongoClient, errors
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import ValidationError
from models import CompanyCreate, CompanyUpdate

# Initialize the router
router = APIRouter()

# Connect to MongoDB with error handling
try:
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)  # 5-second timeout
    db = client["companydb"]
    collection = db["companies"]
    # Check if MongoDB is available
    client.server_info()  # This will throw an exception if the server is unavailable
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
        "phone": company.get("phone"),
        "gst_number": company["gst_number"]
    }

### CRUD Endpoints ###

# Create a new company
@router.post("/companies", response_model=dict)
async def create_company(company: CompanyCreate):
    try:
        new_company = company.dict()
        result = collection.insert_one(new_company)
        created_company = collection.find_one({"_id": result.inserted_id})
        return company_helper(created_company)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input data: {str(e)}")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Get all companies
@router.get("/companies", response_model=list[dict])
async def get_companies():
    try:
        companies = []
        for company in collection.find():
            companies.append(company_helper(company))
        return companies
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Get a company by ID
@router.get("/companies/{company_id}", response_model=dict)
async def get_company(company_id: str):
    try:
        company = collection.find_one({"_id": ObjectId(company_id)})
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return company_helper(company)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Update a company by ID
@router.put("/companies/{company_id}", response_model=dict)
async def update_company(company_id: str, company: CompanyUpdate):
    try:
        updated_data = {k: v for k, v in company.dict().items() if v is not None}
        if not updated_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = collection.update_one({"_id": ObjectId(company_id)}, {"$set": updated_data})
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Company not found")
        
        updated_company = collection.find_one({"_id": ObjectId(company_id)})
        return company_helper(updated_company)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Delete a company by ID
@router.delete("/companies/{company_id}", response_model=dict)
async def delete_company(company_id: str):
    try:
        result = collection.delete_one({"_id": ObjectId(company_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Company not found")
        
        return {"detail": "Company deleted successfully"}
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
