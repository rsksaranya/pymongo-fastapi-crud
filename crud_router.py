from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import json
import os

router = APIRouter()

# MongoDB setup
client = MongoClient("mongodb://localhost:27017")
db = client["mydatabase"]
collection = db["mycollection"]

def process_operation(operation, data):
    if operation == "create":
        if collection.find_one({"_id": data["_id"]}):
            raise HTTPException(status_code=400, detail="Document with this ID already exists.")
        collection.insert_one(data)
        return {"status": "created", "data": data}
    elif operation == "update":
        result = collection.update_one({"_id": data["_id"]}, {"$set": data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"status": "updated", "data": data}
    elif operation == "read":
        document = collection.find_one({"_id": data["_id"]})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"status": "read", "data": document}
    elif operation == "delete":
        result = collection.delete_one({"_id": data["_id"]})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"status": "deleted", "data": data}
    else:
        raise HTTPException(status_code=400, detail="Invalid operation.")

@router.post("/process-json")
async def process_json():
    if not os.path.exists("data.json"):
        raise HTTPException(status_code=404, detail="JSON file not found.")
    
    with open("data.json", "r") as f:
        operations = json.load(f)

    results = []
    for entry in operations:
        operation = entry.get("operation")
        data = entry.get("data")
        if operation and data:
            result = process_operation(operation, data)
            results.append(result)
        else:
            results.append({"status": "error", "detail": "Invalid entry"})

    return {"results": results}
