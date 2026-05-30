from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.database import db

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserSyncPayload(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    subscription: Optional[str] = "free"

@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_user(payload: UserSyncPayload):
    """
    Synchronizes authenticated Supabase users into our local PostgreSQL database.
    """
    try:
        # Check if user already exists
        existing_user = await db.fetch_row(
            "SELECT id FROM users WHERE id = $1", 
            payload.id
        )
        
        if existing_user:
            # Update user information if changed
            await db.execute(
                "UPDATE users SET email = $1, name = $2, subscription = $3, updated_at = NOW() WHERE id = $4",
                payload.email, payload.name, payload.subscription, payload.id
            )
            return {"status": "synchronized", "message": "User profile successfully updated."}
        else:
            # Create a brand new user profile
            await db.execute(
                "INSERT INTO users (id, email, name, subscription, created_at, updated_at) VALUES ($1, $2, $3, $4, NOW(), NOW())",
                payload.id, payload.email, payload.name, payload.subscription
            )
            return {"status": "synchronized", "message": "New user profile created."}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database synchronization failed: {e}"
        )
