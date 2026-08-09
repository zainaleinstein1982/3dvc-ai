from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import os
from app.db.database import get_db
from app.db import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> dict:
    credentials_exception = HTTPException(status_code=401, detail="Invalid credentials")
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"], issuer="3dvc-ai", audience="3dvc-client", options={"require": ["exp", "iat", "iss", "aud", "sub"]})
        user_id = payload.get("sub")
        if user_id is None: raise credentials_exception
    except jwt.PyJWTError: raise credentials_exception
    
    user = await db.get(models.User, user_id)
    if not user or user.status != "ACTIVE": raise HTTPException(status_code=403, detail="Inactive or invalid user")
    
    return {
        "userId": str(user.id),
        "tenantId": str(user.tenant_id),
        "role": user.role,
        "email": user.email
    }

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] not in ["ADMIN", "MODERATOR"]:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
