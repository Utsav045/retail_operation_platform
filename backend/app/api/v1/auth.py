from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

from app.core.database import get_db
from app.models.user import User
from app.services.auth.security import (
    hash_password,
    verify_password,
    generate_otp,
    create_access_token,
    verify_access_token,
)
from app.services.auth.email import send_otp_email

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])


# Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


# Helper dependency for authenticated requests
async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token"
        )
    token = authorization.split(" ")[1]
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    
    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    return user


async def ensure_default_user_seeded(db: AsyncSession):
    """Ensures default manager user is present in the database from dynamic settings."""
    default_email = settings.DEFAULT_MANAGER_EMAIL.strip().lower()
    result = await db.execute(select(User).where(User.email == default_email))
    existing_user = result.scalar_one_or_none()
    
    if not existing_user:
        new_user = User(
            email=default_email,
            name=settings.DEFAULT_MANAGER_NAME,
            hashed_password=hash_password(settings.DEFAULT_MANAGER_PASSWORD),
            role=settings.DEFAULT_MANAGER_ROLE,
            is_active=True
        )
        db.add(new_user)
        await db.commit()


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Always ensure default user exists
    await ensure_default_user_seeded(db)
    
    clean_email = req.email.strip().lower()
    result = await db.execute(select(User).where(User.email == clean_email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact administrator."
        )
    
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "name": user.name, "role": user.role},
        expires_delta=timedelta(days=7)
    )
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    )


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    await ensure_default_user_seeded(db)
    
    clean_email = req.email.strip().lower()
    result = await db.execute(select(User).where(User.email == clean_email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No account registered with email {clean_email}."
        )
    
    # Generate 6-digit OTP and set expiry from dynamic settings
    otp = generate_otp()
    user.reset_otp = otp
    user.reset_otp_expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    await db.commit()
    
    # Dispatch email
    send_otp_email(user.email, otp, user_name=user.name)
    
    return {
        "status": "SUCCESS",
        "message": f"A 6-digit verification code has been sent to {user.email}."
    }


@router.post("/verify-otp")
async def verify_otp(req: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    clean_email = req.email.strip().lower()
    clean_otp = req.otp.strip()
    
    result = await db.execute(select(User).where(User.email == clean_email))
    user = result.scalar_one_or_none()
    
    if not user or not user.reset_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active password reset request found for this email."
        )
    
    if user.reset_otp != clean_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 6-digit verification code. Please check your email."
        )
    
    if user.reset_otp_expires_at and datetime.utcnow() > user.reset_otp_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new code."
        )
    
    return {
        "status": "VALID",
        "message": "Verification code confirmed. You may now enter your new password."
    }


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    clean_email = req.email.strip().lower()
    clean_otp = req.otp.strip()
    
    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long."
        )
    
    result = await db.execute(select(User).where(User.email == clean_email))
    user = result.scalar_one_or_none()
    
    if not user or not user.reset_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active password reset request found."
        )
    
    if user.reset_otp != clean_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )
    
    if user.reset_otp_expires_at and datetime.utcnow() > user.reset_otp_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired."
        )
    
    # Update password and clear OTP
    user.hashed_password = hash_password(req.new_password)
    user.reset_otp = None
    user.reset_otp_expires_at = None
    user.updated_at = datetime.utcnow()
    await db.commit()
    
    return {
        "status": "SUCCESS",
        "message": "Password successfully updated! You can now sign in with your new password."
    }


@router.get("/me")
async def get_current_user_profile(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "created_at": user.created_at.isoformat()
    }
