from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from pymongo import MongoClient, errors
from bson import ObjectId
from bson.errors import InvalidId
from auth import authenticate_user, create_access_token, hash_password, get_current_user
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

# Token generation endpoint for user login
@router.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password, user_collection)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Get current logged-in user
@router.get("/users/me", response_model=dict)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

# Function to validate if a company exists
def is_valid_company(company_id: str) -> bool:
    try:
        return company_collection.find_one({"_id": ObjectId(company_id)}) is not None
    except (InvalidId, errors.PyMongoError):
        return False
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
        "company_id": user["company_id"]
    }
# Function to check if an email is unique
def is_email_unique(email: str, user_id: str = None) -> bool:
    query = {"email": email}
    if user_id:
        # Exclude the current user if checking for an update
        query["_id"] = {"$ne": ObjectId(user_id)}
    return user_collection.find_one(query) is None


# Create a new user with validation and password hashing
@router.post("/users", response_model=dict)
async def create_user(user: UserCreate):
    try: 
         # Check if the company_id is valid
        if not is_valid_company(user.company_id):
            raise HTTPException(status_code=400, detail="Invalid company_id: Company does not exist")

        if not is_email_unique(user.email):
            raise HTTPException(status_code=400, detail="Email is already in use")

        hashed_password = hash_password(user.password)
        new_user = user.dict()
        new_user["password"] = hashed_password
        new_user["status"] = 1
        new_user["created_at"] = datetime.utcnow()
        new_user["updated_at"] = None

        result = user_collection.insert_one(new_user)
        created_user = user_collection.find_one({"_id": result.inserted_id})
        return user_helper(created_user)
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Protect routes by requiring authentication
@router.get("/users", response_model=list)
async def get_users(current_user: dict = Depends(get_current_user)):
    try:
        users = user_collection.find({"status": 1})
        return [user_helper(user) for user in users]
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
