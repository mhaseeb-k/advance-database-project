from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import users_col
from bson import ObjectId

SECRET_KEY = "supersecret-adv-db-2026-change-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h

bearer_scheme = HTTPBearer()
ADMIN_USERNAME = "admin_user"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_admin_user(current_user=Depends(get_current_user)):
    if current_user.get("username") != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def serialize_user(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "username": u["username"],
        "email": u["email"],
        "joined_at": u["joined_at"].isoformat() if isinstance(u.get("joined_at"), datetime) else u.get("joined_at"),
        "stats": u.get("stats", {"post_count": 0, "follower_count": 0}),
        "version": u.get("version", 1),
        "is_admin": u.get("username") == ADMIN_USERNAME,
    }


def serialize_post(p: dict) -> dict:
    return {
        "id": str(p["_id"]),
        "author": {
            "user_id": str(p["author"]["user_id"]),
            "username": p["author"]["username"],
        },
        "content": p["content"],
        "timestamp": p["timestamp"].isoformat() if isinstance(p.get("timestamp"), datetime) else p.get("timestamp"),
        "metrics": p.get("metrics", {"likes": 0, "comment_count": 0}),
        "version": p.get("version", 1),
    }


def serialize_comment(c: dict) -> dict:
    return {
        "id": str(c["_id"]),
        "post_id": str(c["post_id"]),
        "user_id": str(c["user_id"]),
        "username": c.get("username", ""),
        "text": c["text"],
        "timestamp": c["timestamp"].isoformat() if isinstance(c.get("timestamp"), datetime) else c.get("timestamp"),
        "version": c.get("version", 1),
    }
