from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from database import users_col
from auth_utils import (
      create_access_token,
    serialize_user, ADMIN_USERNAME
)

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(req: RegisterRequest):
    if len(req.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    if users_col.find_one({"username": req.username}):
        raise HTTPException(400, "Username already taken")
    if users_col.find_one({"email": req.email}):
        raise HTTPException(400, "Email already registered")

    user_doc = {
        "username": req.username,
        "email": req.email,
        "password": req.password,
        "joined_at": datetime.now(timezone.utc),
        "stats": {"post_count": 0, "follower_count": 0},
        "version": 1,
    }
    result = users_col.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    token = create_access_token({"sub": str(result.inserted_id)})
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(user_doc)}


@router.post("/login")
def login(req: LoginRequest):
    user = users_col.find_one({"username": req.username})
    if not user or not (req.password == user["password"]):
        raise HTTPException(401, "Invalid username or password")

    token = create_access_token({"sub": str(user["_id"])})
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}
