from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pymongo import errors
from bson import ObjectId
from bson.errors import InvalidId

# Secret key and JWT configurations
SECRET_KEY = "4f9eb39592cbc1efc59339c6e72130e4e81dac2a3bd5201c6d1d154101a10d37effbb9ea8529e5236f4dd1470b78eecb46f91d113a41e788138bc61d412baceb01b17bbc7aab4f466c34bab13a8f666a67bd911240e3052f2a3b4506b1f14b003515470f2b033d29a5735d95baff01d6a01096f56d4a4e6231d04a4aa910f35c"  # Use a strong secret key here
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer tokenUrl indicates the endpoint to get the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Hash and verify passwords
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password):
    return pwd_context.hash(password)

# Authenticate user function
async def authenticate_user(email: str, password: str, user_collection):
    try:
        user = user_collection.find_one({"email": email, "status": 1})
        if not user:
            return False
        if not verify_password(password, user["password"]):
            return False
        return user
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Generate JWT access token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Get current user based on the token
async def get_current_user(token: str = Depends(oauth2_scheme), user_collection = Depends()):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        user = user_collection.find_one({"_id": ObjectId(user_id), "status": 1})
        if user is None:
            raise credentials_exception
    except (InvalidId, errors.PyMongoError):
        raise credentials_exception

    return user
