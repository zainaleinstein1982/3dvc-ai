from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.db import models
from app.auth.dependencies import get_current_user
import uuid

router = APIRouter()

class RoomCreate(BaseModel):
    name: str

@router.post("")
async def create_room(req: RoomCreate, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    room = models.Room(tenant_id=uuid.UUID(user["tenantId"]), name=req.name, owner_id=uuid.UUID(user["userId"]))
    db.add(room)
    await db.flush()
    member = models.RoomMember(room_id=room.id, user_id=uuid.UUID(user["userId"]), role="OWNER", presence="OFFLINE", is_approved=True)
    db.add(member)
    await db.commit()
    return {"roomId": str(room.id), "name": room.name}

@router.get("")
async def list_rooms(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Room).filter_by(tenant_id=uuid.UUID(user["tenantId"]), status="ACTIVE"))
    return [{"id": str(r.id), "name": r.name} for r in result.scalars().all()]

@router.get("/{room_id}/members")
async def get_members(room_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User, models.RoomMember).join(models.RoomMember, models.User.id == models.RoomMember.user_id).filter(models.RoomMember.room_id == uuid.UUID(room_id)))
    members = []
    for u, m in result.all():
        members.append({"userId": str(u.id), "displayName": u.display_name, "role": m.role, "presence": m.presence, "is_muted": m.is_muted, "is_approved": m.is_approved})
    return members

@router.post("/{room_id}/join")
async def join_room(room_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    room = await db.get(models.Room, uuid.UUID(room_id))
    if not room or room.status != "ACTIVE": raise HTTPException(404, "Room not found or ended")
    if room.tenant_id != uuid.UUID(user["tenantId"]): raise HTTPException(403, "Cross-tenant access denied")

    result = await db.execute(select(models.RoomMember).filter_by(room_id=uuid.UUID(room_id), user_id=uuid.UUID(user["userId"])))
    member = result.scalars().first()
    if not member:
        member = models.RoomMember(room_id=uuid.UUID(room_id), user_id=uuid.UUID(user["userId"]), role="PARTICIPANT", presence="ONLINE", is_approved=user["role"] in ["ADMIN", "MODERATOR"])
        db.add(member)
    else:
        member.presence = "ONLINE"
    await db.commit()
    if not member.is_approved: raise HTTPException(403, "Waiting for moderator approval")
    return {"status": "joined", "roomId": room_id}

@router.post("/{room_id}/leave")
async def leave_room(room_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(update(models.RoomMember).where(models.RoomMember.room_id == uuid.UUID(room_id), models.RoomMember.user_id == uuid.UUID(user["userId"])).values(presence="OFFLINE"))
    await db.commit()
    return {"status": "left"}

@router.post("/{room_id}/kick/{target_id}")
async def kick_user(room_id: str, target_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.RoomMember).filter_by(room_id=uuid.UUID(room_id), user_id=uuid.UUID(user["userId"])))
    actor = result.scalars().first()
    if not actor or actor.role not in ["OWNER", "MODERATOR"]: raise HTTPException(403, "Insufficient privileges")
    await db.execute(update(models.RoomMember).where(models.RoomMember.room_id == uuid.UUID(room_id), models.RoomMember.user_id == uuid.UUID(target_id)).values(presence="OFFLINE", is_approved=False))
    await db.commit()
    return {"status": "kicked"}

@router.post("/{room_id}/end")
async def end_room(room_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.RoomMember).filter_by(room_id=uuid.UUID(room_id), user_id=uuid.UUID(user["userId"])))
    actor = result.scalars().first()
    if not actor or actor.role != "OWNER": raise HTTPException(403, "Only owner can end room")
    room = await db.get(models.Room, uuid.UUID(room_id))
    room.status = "ENDED"
    await db.execute(update(models.RoomMember).where(models.RoomMember.room_id == uuid.UUID(room_id)).values(presence="OFFLINE"))
    await db.commit()
    return {"status": "ended"}
