from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from app.models.schemas import Document
from app.models.database import documents_collection
from app.services.auth import get_current_user, verify_token
from nlp_modules.text_extractor import extract_text_from_file
from nlp_modules.converter import convert_to_pdf
from datetime import datetime
from bson import ObjectId
import aiofiles
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10485760))

@router.post("/upload", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Upload a document and extract text"""
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
    
    # Convert DOCX/PPTX to PDF for preview (Windows only for DOCX)
    pdf_path = None
    if file_extension in ["docx", "pptx"]:
        pdf_path = file_path.replace(f".{file_extension}", "_preview.pdf")
        success = convert_to_pdf(file_path, pdf_path)
        if not success:
            pdf_path = None  # Conversion failed, will use original file
    
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
        "filename": file.filename,
        "file_type": file_extension,
        "file_path": file_path,
        "pdf_path": pdf_path,
        "processed_text": extracted_text,
        "uploaded_at": datetime.utcnow()
    }
    
    if folder_id:
        document_dict["folder_id"] = folder_id
    
    result = await documents_collection.insert_one(document_dict)
    document_dict["id"] = str(result.inserted_id)
    
    return Document(
        id=document_dict["id"],
        user_id=document_dict["user_id"],
        filename=document_dict["filename"],
        file_type=document_dict["file_type"],
        folder_id=document_dict.get("folder_id"),
        uploaded_at=document_dict["uploaded_at"],
        processed_text=document_dict["processed_text"]
    )

@router.get("/", response_model=List[Document])
async def get_all_documents(
    folder_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user)
):
    """Get all documents for current user, optionally filtered by folder"""
    query = {"user_id": user_id}
    
    if folder_id:
        query["folder_id"] = folder_id
    else:
        # Get documents not in any folder (root level)
        query["folder_id"] = {"$exists": False}
    
    documents = []
    cursor = documents_collection.find(query).sort("uploaded_at", -1)
    
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

@router.get("/{document_id}", response_model=Document)
async def get_document(document_id: str, user_id: str = Depends(get_current_user)):
    """Get a specific document"""
    document = await documents_collection.find_one({
        "_id": ObjectId(document_id),
        "user_id": user_id
    })
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return Document(
        id=str(document["_id"]),
        user_id=document["user_id"],
        filename=document["filename"],
        file_type=document["file_type"],
        folder_id=document.get("folder_id"),
        uploaded_at=document["uploaded_at"],
        processed_text=document.get("processed_text")
    )

@router.delete("/{document_id}")
async def delete_document(document_id: str, user_id: str = Depends(get_current_user)):
    """Delete a document"""
    document = await documents_collection.find_one({
        "_id": ObjectId(document_id),
        "user_id": user_id
    })
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file from filesystem
    if os.path.exists(document["file_path"]):
        os.remove(document["file_path"])
    
    # Delete PDF preview if exists
    if document.get("pdf_path") and os.path.exists(document["pdf_path"]):
        os.remove(document["pdf_path"])
    
    # Delete from database
    await documents_collection.delete_one({"_id": ObjectId(document_id)})
    
    return {"message": "Document deleted successfully"}

@router.get("/{document_id}/file")
async def get_document_file(document_id: str, token: Optional[str] = Query(None)):
    """Serve the actual document file - returns PDF preview for DOCX/PPTX"""
    # Verify token from query parameter
    user_id = None
    if token:
        user_id = verify_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        document = await documents_collection.find_one({
            "_id": ObjectId(document_id),
            "user_id": user_id
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document ID: {str(e)}"
        )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # For DOCX/PPTX, return PDF preview if available
    file_type = document.get("file_type", "pdf")
    if file_type in ["docx", "pptx"] and document.get("pdf_path"):
        file_path = document.get("pdf_path")
        media_type = "application/pdf"
        content_disposition_type = "inline"
    else:
        file_path = document.get("file_path")
        # Determine media type based on file extension
        media_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }
        media_type = media_types.get(file_type, "application/octet-stream")
        # Use 'inline' for PDF to display in browser, 'attachment' for office docs
        content_disposition_type = "inline" if file_type == "pdf" else "attachment"
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on server"
        )
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={
            "Content-Disposition": f'{content_disposition_type}; filename="{document.get("filename", f"document.{file_type}")}"'
        }
    )
