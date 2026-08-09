from fastapi import APIRouter, Request
from livekit.api import WebhookReceiver, TokenVerifier
import os
from app.db.database import AsyncSessionLocal
from app.db import models
from sqlalchemy import update
import uuid

router = APIRouter()

key_provider = TokenVerifier(
    os.getenv("LIVEKIT_API_KEY", "devkey"),
    os.getenv("LIVEKIT_API_SECRET", "secret")
)
receiver = WebhookReceiver(key_provider)

@router.post("/sfu/webhook")
async def livekit_webhook(request: Request):
    body = await request.body()
    try:
        event = await receiver.receive(body, request.headers)
        async with AsyncSessionLocal() as db:
            if event.event == "participant_joined":
                await db.execute(update(models.RoomMember).where(models.RoomMember.user_id == uuid.UUID(event.participant.identity)).values(presence="ONLINE"))
            elif event.event == "participant_left":
                await db.execute(update(models.RoomMember).where(models.RoomMember.user_id == uuid.UUID(event.participant.identity)).values(presence="OFFLINE"))
            await db.commit()
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}