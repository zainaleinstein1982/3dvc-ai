import bcrypt
import jwt
import os
import secrets
import hashlib
import datetime

def hash_password(password: str) -> str:
    # Truncate password to maximum 72 bytes for bcrypt safety
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    # Truncate password to maximum 72 bytes for bcrypt safety
    password_bytes = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed.encode("utf-8"))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15)))
    to_encode.update({"exp": expire, "iat": datetime.datetime.utcnow(), "iss": "3dvc-ai", "aud": "3dvc-client"})
    secret = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY", "default-secret-key-change-me")
    return jwt.encode(to_encode, secret, algorithm="HS256")

def generate_refresh_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash

def hash_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()