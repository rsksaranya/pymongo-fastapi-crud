import json
import os
from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder
from typing import List

from pymongo import MongoClient

from models import Book, BookUpdate

router = APIRouter()

@router.post("/", response_description="Create a new book", status_code=status.HTTP_201_CREATED, response_model=Book)
def create_book(request: Request, book: Book = Body(...)):
    book = jsonable_encoder(book)
    new_book = request.app.database["books"].insert_one(book)
    created_book = request.app.database["books"].find_one(
        {"_id": new_book.inserted_id}
    )

    return created_book


@router.get("/", response_description="List all books", response_model=List[Book])
def list_books(request: Request):
    books = list(request.app.database["books"].find(limit=100))
    return books


@router.get("/{id}", response_description="Get a single book by id", response_model=Book)
def find_book(id: str, request: Request):
    if (book := request.app.database["books"].find_one({"_id": id})) is not None:
        return book

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with ID {id} not found")


@router.put("/{id}", response_description="Update a book", response_model=Book)
def update_book(id: str, request: Request, book: BookUpdate = Body(...)):
    book = {k: v for k, v in book.dict().items() if v is not None}

    if len(book) >= 1:
        update_result = request.app.database["books"].update_one(
            {"_id": id}, {"$set": book}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with ID {id} not found")

    if (
        existing_book := request.app.database["books"].find_one({"_id": id})
    ) is not None:
        return existing_book

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with ID {id} not found")


@router.delete("/{id}", response_description="Delete a book")
def delete_book(id: str, request: Request, response: Response):
    delete_result = request.app.database["books"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with ID {id} not found")

@router.post("/process-json")
async def process_json():
    # Check if file exists
    if not os.path.exists("data.json"):
        raise HTTPException(status_code=404, detail="JSON file not found.")
    
    # Load JSON data from file
    with open("data.json", "r") as f:
        operations = json.load(f)

    results = []

    # Process each operation in JSON file
    for entry in operations:
        operation = entry.get("operation")
        data = entry.get("data")
        if operation and data:
            result = process_operation(operation, data)
            results.append(result)
        else:
            results.append({"status": "error", "detail": "Invalid entry"})

    return {"results": results}

# MongoDB setup
client = MongoClient("mongodb://localhost:27017")
db = client["mydatabase"]
collection = db["mycollection"]

def process_operation(operation, data):
    # Same CRUD function as before
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

