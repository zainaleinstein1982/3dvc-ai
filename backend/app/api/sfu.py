from fastapi import APIRouter, HTTPException, Depends
import os
from livekit import api
from app.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/token")
async def get_token(room: str = "demo-room", user: dict = Depends(get_current_user)):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    
    if not api_key or not api_secret:
        raise HTTPException(status_code=503, detail="LiveKit credentials not configured")
        
    secure_room = f"{user['tenantId']}_{room}"
    
    token = api.AccessToken(api_key, api_secret) \
        .with_identity(user["userId"]) \
        .with_name(user["email"]) \
        .with_grants(api.VideoGrants(room_join=True, room=secure_room, can_publish=True, can_subscribe=True, can_publish_data=True)) \
        .to_jwt()
        
    return {"token": token, "url": livekit_url, "room": secure_room}
