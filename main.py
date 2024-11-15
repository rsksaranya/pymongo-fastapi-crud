from fastapi import FastAPI
from dotenv import dotenv_values
from pymongo import MongoClient
from routes import router as crud_router
from company import router as company_router  # Import the router from company.py
from user import router as user_router  # Import the user router


config = dotenv_values(".env")

app = FastAPI()

@app.on_event("startup")
def startup_db_client():
    app.mongodb_client = MongoClient(config["ATLAS_URI"])
    app.database = app.mongodb_client[config["DB_NAME"]]

@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()

app.include_router(crud_router, prefix="/api")
app.include_router(company_router, prefix="/api/v1")  # You can use a prefix if needed
app.include_router(user_router, prefix="/api/v1")