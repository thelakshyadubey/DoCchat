from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.models.schemas import SummaryRequest, Summary, ExplanationRequest, Explanation
from app.models.database import documents_collection, summaries_collection, explanations_collection
from app.services.auth import get_current_user
from nlp_modules.summarizer import generate_summary
from nlp_modules.explainer import generate_explanation
from nlp_modules.api_client import generate_key_points_with_api, generate_short_notes_with_api
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel

router = APIRouter()

class StudyNotesResponse(BaseModel):
    key_points: str
    short_notes: str

@router.post("/summarize", response_model=Summary)
async def summarize_document(
    request: SummaryRequest,
    user_id: str = Depends(get_current_user)
):
    """Generate a summary for a document"""
    # Get document
    document = await documents_collection.find_one({
        "_id": ObjectId(request.document_id),
        "user_id": user_id
    })
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if not document.get("processed_text"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text not available"
        )
    
    # Generate summary
    try:
        summary_text = await generate_summary(
            document["processed_text"],
            summary_type=request.type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization failed: {str(e)}"
        )
    
    # Save summary to database
    summary_dict = {
        "document_id": request.document_id,
        "summary_text": summary_text,
        "summary_type": request.type,
        "created_at": datetime.utcnow()
    }
    
    result = await summaries_collection.insert_one(summary_dict)
    summary_dict["id"] = str(result.inserted_id)
    
    return Summary(**summary_dict)

@router.get("/summaries/{document_id}", response_model=List[Summary])
async def get_summaries(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get all summaries for a document"""
    # Verify document ownership
    document = await documents_collection.find_one({
        "_id": ObjectId(document_id),
        "user_id": user_id
    })
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get summaries
    summaries = []
    cursor = summaries_collection.find({"document_id": document_id}).sort("created_at", -1)
    
    async for summary in cursor:
        summaries.append(Summary(
            id=str(summary["_id"]),
            document_id=summary["document_id"],
            summary_text=summary["summary_text"],
            summary_type=summary["summary_type"],
            created_at=summary["created_at"]
        ))
    
    return summaries

@router.post("/explain", response_model=Explanation)
async def explain_text(
    request: ExplanationRequest,
    user_id: str = Depends(get_current_user)
):
    """Generate an explanation for text"""
    # Verify document ownership
    document = await documents_collection.find_one({
        "_id": ObjectId(request.document_id),
        "user_id": user_id
    })
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Generate explanation
    try:
        explained_text = await generate_explanation(
            request.text,
            tone=request.tone
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation failed: {str(e)}"
        )
    
    # Save explanation to database
    explanation_dict = {
        "document_id": request.document_id,
        "original_text": request.text,
        "explained_text": explained_text,
        "tone": request.tone,
        "created_at": datetime.utcnow()
    }
    
    result = await explanations_collection.insert_one(explanation_dict)
    explanation_dict["id"] = str(result.inserted_id)
    
    return Explanation(**explanation_dict)


@router.post("/study-notes/{document_id}", response_model=StudyNotesResponse)
async def generate_study_notes(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Generate exam-ready key points and short notes for a document"""
    # Get document
    document = await documents_collection.find_one({
        "_id": ObjectId(document_id),
        "user_id": user_id
    })
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if not document.get("processed_text"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text not available"
        )
    
    # Generate key points and short notes
    try:
        print(f"📚 Generating study notes for document: {document.get('filename', 'Unknown')}")
        key_points = await generate_key_points_with_api(document["processed_text"])
        short_notes = await generate_short_notes_with_api(document["processed_text"])
        
        return StudyNotesResponse(
            key_points=key_points,
            short_notes=short_notes
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Study notes generation failed: {str(e)}"
        )

