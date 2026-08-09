from passlib.context import CryptContext
import jwt
import os
import secrets
import hashlib
import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15)))
    to_encode.update({"exp": expire, "iat": datetime.datetime.utcnow(), "iss": "3dvc-ai", "aud": "3dvc-client"})
    return jwt.encode(to_encode, os.getenv("JWT_SECRET"), algorithm="HS256")

def generate_refresh_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash

def hash_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()
