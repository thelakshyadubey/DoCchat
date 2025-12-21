from fastapi import APIRouter, HTTPException, status, Depends
from app.models.schemas import UserCreate, UserLogin, User, Token
from app.models.database import users_collection
from app.services.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.services.email_service import send_password_reset_email, send_password_changed_confirmation
from datetime import timedelta, datetime
from bson import ObjectId
import secrets
from pydantic import BaseModel, EmailStr

router = APIRouter()

# Additional request models for password reset
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user"""
    # Check if user already exists
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user_dict = {
        "email": user_data.email,
        "name": user_data.name,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    }
    
    result = await users_collection.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    
    # Create access token
    access_token = create_access_token(data={"sub": user_dict["id"]})
    
    user = User(
        id=user_dict["id"],
        email=user_dict["email"],
        name=user_dict["name"],
        created_at=user_dict["created_at"]
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login user"""
    # Find user
    user = await users_collection.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user["_id"])})
    
    user_obj = User(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        created_at=user["created_at"]
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_obj)

@router.get("/me", response_model=User)
async def get_current_user_info(user_id: str = Depends(get_current_user)):
    """Get current user information"""
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return User(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        created_at=user["created_at"]
    )

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Send password reset email
    
    Returns success message even if email doesn't exist (security best practice)
    """
    # Look up user
    user = await users_collection.find_one({"email": request.email})
    
    if user:
        # Generate secure reset token (32 bytes = 64 hex characters)
        reset_token = secrets.token_urlsafe(32)
        
        # Set token expiry (1 hour from now)
        expiry = datetime.utcnow() + timedelta(hours=1)
        
        # Store token in database
        await users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "reset_token": reset_token,
                    "reset_token_expiry": expiry
                }
            }
        )
        
        # Send email
        await send_password_reset_email(user["email"], reset_token)
    
    # Always return success message (don't reveal if email exists)
    return {
        "message": "If an account exists with this email, you will receive password reset instructions shortly."
    }

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using token from email
    """
    # Find user with valid token
    user = await users_collection.find_one({
        "reset_token": request.token,
        "reset_token_expiry": {"$gt": datetime.utcnow()}
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Hash new password
    hashed_password = get_password_hash(request.new_password)
    
    # Update password and remove reset token
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "hashed_password": hashed_password
            },
            "$unset": {
                "reset_token": "",
                "reset_token_expiry": ""
            }
        }
    )
    
    # Send confirmation email
    await send_password_changed_confirmation(user["email"], user["name"])
    
    return {"message": "Password reset successfully. You can now log in with your new password."}
