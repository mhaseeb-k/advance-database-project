from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone
from database import posts_col, users_col, comments_col
from auth_utils import get_current_user, serialize_post

router = APIRouter()


class CreatePostRequest(BaseModel):
    content: str


class UpdatePostRequest(BaseModel):
    content: str
    version: int


@router.post("/")
def create_post(req: CreatePostRequest, current_user=Depends(get_current_user)):
    if not req.content.strip():
        raise HTTPException(400, "Content cannot be empty")
    if len(req.content) > 1000:
        raise HTTPException(400, "Post too long (max 1000 chars)")

    post_doc = {
        "author": {
            "user_id": current_user["_id"],
            "username": current_user["username"],
        },
        "content": req.content.strip(),
        "timestamp": datetime.now(timezone.utc),
        "metrics": {"likes": 0, "comment_count": 0},
        "version": 1,
    }
    result = posts_col.insert_one(post_doc)
    post_doc["_id"] = result.inserted_id

    # Update user post count (OCC)
    user_doc = users_col.find_one({"_id": current_user["_id"]}, {"version": 1, "stats": 1})
    users_col.update_one(
        {"_id": current_user["_id"], "version": user_doc["version"]},
        {"$inc": {"stats.post_count": 1, "version": 1}}
    )

    return serialize_post(post_doc)


@router.get("/{post_id}")
def get_post(post_id: str):
    try:
        oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(400, "Invalid post ID")
    post = posts_col.find_one({"_id": oid})
    if not post:
        raise HTTPException(404, "Post not found")
    return serialize_post(post)


@router.patch("/{post_id}")
def update_post(post_id: str, req: UpdatePostRequest, current_user=Depends(get_current_user)):
    """OCC-protected post update."""
    try:
        oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(400, "Invalid post ID")

    post = posts_col.find_one({"_id": oid})
    if not post:
        raise HTTPException(404, "Post not found")

    is_admin = current_user.get("username") == "admin_user"
    is_owner = str(post["author"]["user_id"]) == str(current_user["_id"])
    if not is_admin and not is_owner:
        raise HTTPException(403, "Not authorized to edit this post")

    if not req.content.strip():
        raise HTTPException(400, "Content cannot be empty")

    result = posts_col.update_one(
        {"_id": oid, "version": req.version},
        {"$set": {"content": req.content.strip()}, "$inc": {"version": 1}}
    )
    if result.modified_count == 0:
        raise HTTPException(409, "OCC conflict: post was modified. Please refresh and retry.")

    return serialize_post(posts_col.find_one({"_id": oid}))


@router.delete("/{post_id}")
def delete_post(post_id: str, current_user=Depends(get_current_user)):
    try:
        oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(400, "Invalid post ID")

    post = posts_col.find_one({"_id": oid})
    if not post:
        raise HTTPException(404, "Post not found")

    is_admin = current_user.get("username") == "admin_user"
    is_owner = str(post["author"]["user_id"]) == str(current_user["_id"])
    if not is_admin and not is_owner:
        raise HTTPException(403, "Not authorized to delete this post")

    posts_col.delete_one({"_id": oid})
    comments_col.delete_many({"post_id": oid})

    # Decrement post count for owner (OCC)
    user_doc = users_col.find_one({"_id": post["author"]["user_id"]}, {"version": 1})
    if user_doc:
        users_col.update_one(
            {"_id": post["author"]["user_id"], "version": user_doc["version"]},
            {"$inc": {"stats.post_count": -1, "version": 1}}
        )

    return {"message": "Post deleted"}


@router.post("/{post_id}/like")
def like_post(post_id: str, current_user=Depends(get_current_user)):
    try:
        oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(400, "Invalid post ID")

    post = posts_col.find_one({"_id": oid}, {"version": 1})
    if not post:
        raise HTTPException(404, "Post not found")

    result = posts_col.update_one(
        {"_id": oid, "version": post["version"]},
        {"$inc": {"metrics.likes": 1, "version": 1}}
    )
    if result.modified_count == 0:
        raise HTTPException(409, "OCC conflict on like. Please retry.")

    return {"message": "Liked"}
