from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from typing import List
from app.models.schemas import Folder, FolderCreate, Document
from app.models.database import database, documents_collection
from app.services.auth import get_current_user
from nlp_modules.text_extractor import extract_text_from_file
from datetime import datetime
from bson import ObjectId
import aiofiles
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

folders_collection = database.get_collection("folders")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

@router.post("/", response_model=Folder, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder: FolderCreate,
    user_id: str = Depends(get_current_user)
):
    """Create a new folder/subject"""
    # Check if folder with same name exists
    existing = await folders_collection.find_one({
        "user_id": user_id,
        "name": folder.name
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder with this name already exists"
        )
    
    folder_dict = {
        "user_id": user_id,
        "name": folder.name,
        "color": folder.color or "#6B7280",
        "created_at": datetime.utcnow()
    }
    
    result = await folders_collection.insert_one(folder_dict)
    folder_dict["id"] = str(result.inserted_id)
    
    # Count documents in this folder
    doc_count = await documents_collection.count_documents({
        "folder_id": folder_dict["id"]
    })
    
    return Folder(
        id=folder_dict["id"],
        user_id=folder_dict["user_id"],
        name=folder_dict["name"],
        color=folder_dict["color"],
        created_at=folder_dict["created_at"],
        document_count=doc_count
    )

@router.get("/", response_model=List[Folder])
async def get_all_folders(user_id: str = Depends(get_current_user)):
    """Get all folders for current user"""
    folders = []
    cursor = folders_collection.find({"user_id": user_id}).sort("created_at", -1)
    
    async for folder in cursor:
        # Count documents in this folder
        doc_count = await documents_collection.count_documents({
            "folder_id": str(folder["_id"])
        })
        
        folders.append(Folder(
            id=str(folder["_id"]),
            user_id=folder["user_id"],
            name=folder["name"],
            color=folder.get("color", "#6B7280"),
            created_at=folder["created_at"],
            document_count=doc_count
        ))
    
    return folders

@router.get("/{folder_id}", response_model=Folder)
async def get_folder(folder_id: str, user_id: str = Depends(get_current_user)):
    """Get a specific folder"""
    folder = await folders_collection.find_one({
        "_id": ObjectId(folder_id),
        "user_id": user_id
    })
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    # Count documents in this folder
    doc_count = await documents_collection.count_documents({
        "folder_id": folder_id
    })
    
    return Folder(
        id=str(folder["_id"]),
        user_id=folder["user_id"],
        name=folder["name"],
        color=folder.get("color", "#6B7280"),
        created_at=folder["created_at"],
        document_count=doc_count
    )

@router.get("/{folder_id}/documents", response_model=List[Document])
async def get_folder_documents(folder_id: str, user_id: str = Depends(get_current_user)):
    """Get all documents in a folder"""
    # Verify folder exists and belongs to user
    folder = await folders_collection.find_one({
        "_id": ObjectId(folder_id),
        "user_id": user_id
    })
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    documents = []
    cursor = documents_collection.find({
        "folder_id": folder_id,
        "user_id": user_id
    }).sort("uploaded_at", -1)
    
    async for doc in cursor:
        documents.append(Document(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            filename=doc["filename"],
            file_type=doc["file_type"],
            folder_id=doc.get("folder_id"),
            uploaded_at=doc["uploaded_at"],
            processed_text=doc.get("processed_text")
        ))
    
    return documents

@router.post("/{folder_id}/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document_to_folder(
    folder_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """Upload a document to a specific folder"""
    # Verify folder exists and belongs to user
    folder = await folders_collection.find_one({
        "_id": ObjectId(folder_id),
        "user_id": user_id
    })
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    # Validate file type
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not supported"
        )
    
    # Save file
    file_extension = file.filename.split(".")[-1]
    file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{datetime.utcnow().timestamp()}.{file_extension}")
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Extract text from file
    try:
        extracted_text = await extract_text_from_file(file_path, file_extension)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction failed: {str(e)}"
        )
    
    # Save document metadata to database
    document_dict = {
        "user_id": user_id,
        "folder_id": folder_id,
        "filename": file.filename,
        "file_type": file_extension,
        "file_path": file_path,
        "processed_text": extracted_text,
        "uploaded_at": datetime.utcnow()
    }
    
    result = await documents_collection.insert_one(document_dict)
    document_dict["id"] = str(result.inserted_id)
    
    return Document(
        id=document_dict["id"],
        user_id=document_dict["user_id"],
        filename=document_dict["filename"],
        file_type=document_dict["file_type"],
        folder_id=document_dict["folder_id"],
        uploaded_at=document_dict["uploaded_at"],
        processed_text=document_dict["processed_text"]
    )

@router.put("/{folder_id}")
async def update_folder(
    folder_id: str,
    folder_update: FolderCreate,
    user_id: str = Depends(get_current_user)
):
    """Update folder name or color"""
    folder = await folders_collection.find_one({
        "_id": ObjectId(folder_id),
        "user_id": user_id
    })
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    update_dict = {}
    if folder_update.name:
        update_dict["name"] = folder_update.name
    if folder_update.color:
        update_dict["color"] = folder_update.color
    
    if update_dict:
        await folders_collection.update_one(
            {"_id": ObjectId(folder_id)},
            {"$set": update_dict}
        )
    
    return {"message": "Folder updated successfully"}

@router.delete("/{folder_id}")
async def delete_folder(folder_id: str, user_id: str = Depends(get_current_user)):
    """Delete a folder and optionally move documents"""
    folder = await folders_collection.find_one({
        "_id": ObjectId(folder_id),
        "user_id": user_id
    })
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    # Move all documents in this folder to root (remove folder_id)
    await documents_collection.update_many(
        {"folder_id": folder_id},
        {"$unset": {"folder_id": ""}}
    )
    
    # Delete folder
    await folders_collection.delete_one({"_id": ObjectId(folder_id)})
    
    return {"message": "Folder deleted successfully"}
