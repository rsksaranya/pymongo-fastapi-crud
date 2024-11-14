from fastapi import APIRouter, HTTPException
from pymongo import MongoClient, errors
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import ValidationError
from datetime import datetime
import bcrypt
from models import UserCreate, UserUpdate

# Import company collection for validation
from company import collection as company_collection

# Initialize the router
router = APIRouter()

# Connect to MongoDB
try:
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
    db = client["companydb"]
    user_collection = db["users"]
    client.server_info()  # Test database connection
except errors.ServerSelectionTimeoutError:
    raise HTTPException(status_code=500, detail="Database connection failed")

# Helper function to convert MongoDB object to JSON-friendly format
def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "phone": user["phone"],
        "gender": user["gender"],
        "dob": user["dob"],
        "role_id": user.get("role_id"),
        "company_id": user["company_id"],
        "status": user["status"],
        "created_by": user.get("created_by"),
        "updated_by": user.get("updated_by"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at")
    }

# Function to validate if a company exists
def is_valid_company(company_id: str) -> bool:
    try:
        return company_collection.find_one({"_id": ObjectId(company_id)}) is not None
    except (InvalidId, errors.PyMongoError):
        return False

# Function to check if an email is unique
def is_email_unique(email: str, user_id: str = None) -> bool:
    query = {"email": email}
    if user_id:
        query["_id"] = {"$ne": ObjectId(user_id)}
    return user_collection.find_one(query) is None

# Function to hash a password
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Function to verify a password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

### CRUD Endpoints with Secure Password Handling ###

# Create a new user with validation and password hashing
@router.post("/users", response_model=dict)
async def create_user(user: UserCreate):
    try:
        # Check if the company_id is valid
        if not is_valid_company(user.company_id):
            raise HTTPException(status_code=400, detail="Invalid company_id: Company does not exist")

        # Check if the email is unique
        if not is_email_unique(user.email):
            raise HTTPException(status_code=400, detail="Email is already in use")

        # Hash the password before saving
        hashed_password = hash_password(user.password)

        new_user = user.dict()
        new_user["password"] = hashed_password
        new_user["status"] = 1
        new_user["created_at"] = datetime.utcnow()
        new_user["updated_at"] = None

        result = user_collection.insert_one(new_user)
        created_user = user_collection.find_one({"_id": result.inserted_id})
        return user_helper(created_user)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input data: {str(e)}")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Update a user by ID with validation, including password update if provided
@router.put("/users/{user_id}", response_model=dict)
async def update_user(user_id: str, user: UserUpdate):
    try:
        updated_data = {k: v for k, v in user.dict().items() if v is not None}
        updated_data["updated_at"] = datetime.utcnow()

        # Validate company_id if it is being updated
        if "company_id" in updated_data and not is_valid_company(updated_data["company_id"]):
            raise HTTPException(status_code=400, detail="Invalid company_id: Company does not exist")

        # Validate email uniqueness if email is being updated
        if "email" in updated_data and not is_email_unique(updated_data["email"], user_id):
            raise HTTPException(status_code=400, detail="Email is already in use")

        # If password is being updated, hash the new password
        if "password" in updated_data:
            updated_data["password"] = hash_password(updated_data["password"])

        result = user_collection.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        updated_user = user_collection.find_one({"_id": ObjectId(user_id)})
        return user_helper(updated_user)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Soft delete a user
@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(user_id: str, updated_by: str):
    try:
        result = user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"status": 0, "updated_by": updated_by, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        deleted_user = user_collection.find_one({"_id": ObjectId(user_id)})
        return user_helper(deleted_user)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Retrieve all active users
@router.get("/users", response_model=list)
async def get_users():
    try:
        users = user_collection.find({"status": 1})
        return [user_helper(user) for user in users]
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
