from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId
from database import users_col, posts_col
from auth_utils import get_current_user, serialize_user, serialize_post

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    version: int


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return serialize_user(current_user)


@router.get("/{user_id}")
def get_user(user_id: str):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "Invalid user ID")
    user = users_col.find_one({"_id": oid})
    if not user:
        raise HTTPException(404, "User not found")
    return serialize_user(user)


@router.get("/{user_id}/posts")
def get_user_posts(user_id: str, skip: int = 0, limit: int = 20):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "Invalid user ID")
    posts = list(
        posts_col.find({"author.user_id": oid})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    return [serialize_post(p) for p in posts]


@router.patch("/me")
def update_profile(req: UpdateProfileRequest, current_user=Depends(get_current_user)):
    """OCC-protected profile update."""
    updates = {}
    if req.email:
        if users_col.find_one({"email": req.email, "_id": {"$ne": current_user["_id"]}}):
            raise HTTPException(400, "Email already in use")
        updates["email"] = req.email
    if req.password:
        if len(req.password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")
        updates["password"] = req.password

    if not updates:
        raise HTTPException(400, "Nothing to update")

    result = users_col.update_one(
        {"_id": current_user["_id"], "version": req.version},
        {"$set": updates, "$inc": {"version": 1}}
    )
    if result.modified_count == 0:
        raise HTTPException(409, "OCC conflict: data was modified by another request. Please refresh and retry.")

    updated = users_col.find_one({"_id": current_user["_id"]})
    return serialize_user(updated)
