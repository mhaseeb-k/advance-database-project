from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone
from database import posts_col, comments_col, users_col
from auth_utils import get_current_user, serialize_comment

router = APIRouter()


class CreateCommentRequest(BaseModel):
    post_id: str
    text: str


class UpdateCommentRequest(BaseModel):
    text: str
    version: int


@router.get("/post/{post_id}")
def get_comments(post_id: str, skip: int = 0, limit: int = 30):
    try:
        oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(400, "Invalid post ID")

    raw = list(
        comments_col.find({"post_id": oid})
        .sort("timestamp", 1)
        .skip(skip)
        .limit(limit)
    )

    # Enrich with usernames
    user_ids = list({c["user_id"] for c in raw})
    users = {u["_id"]: u["username"] for u in users_col.find({"_id": {"$in": user_ids}}, {"username": 1})}
    for c in raw:
        c["username"] = users.get(c["user_id"], "Unknown")

    return [serialize_comment(c) for c in raw]


@router.post("/")
def add_comment(req: CreateCommentRequest, current_user=Depends(get_current_user)):
    try:
        post_oid = ObjectId(req.post_id)
    except Exception:
        raise HTTPException(400, "Invalid post ID")

    post = posts_col.find_one({"_id": post_oid}, {"version": 1})
    if not post:
        raise HTTPException(404, "Post not found")

    if not req.text.strip():
        raise HTTPException(400, "Comment cannot be empty")

    comment_doc = {
        "post_id": post_oid,
        "user_id": current_user["_id"],
        "username": current_user["username"],
        "text": req.text.strip(),
        "timestamp": datetime.now(timezone.utc),
        "version": 1,
    }
    comments_col.insert_one(comment_doc)

    # OCC update comment count on post
    result = posts_col.update_one(
        {"_id": post_oid, "version": post["version"]},
        {"$inc": {"metrics.comment_count": 1, "version": 1}}
    )
    if result.modified_count == 0:
        # retry once with fresh version
        post2 = posts_col.find_one({"_id": post_oid}, {"version": 1})
        if post2:
            posts_col.update_one(
                {"_id": post_oid, "version": post2["version"]},
                {"$inc": {"metrics.comment_count": 1, "version": 1}}
            )

    comment_doc["username"] = current_user["username"]
    return serialize_comment(comment_doc)


@router.patch("/{comment_id}")
def update_comment(comment_id: str, req: UpdateCommentRequest, current_user=Depends(get_current_user)):
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(400, "Invalid comment ID")

    comment = comments_col.find_one({"_id": oid})
    if not comment:
        raise HTTPException(404, "Comment not found")

    is_admin = current_user.get("username") == "admin_user"
    is_owner = str(comment["user_id"]) == str(current_user["_id"])
    if not is_admin and not is_owner:
        raise HTTPException(403, "Not authorized")

    if not req.text.strip():
        raise HTTPException(400, "Comment cannot be empty")

    result = comments_col.update_one(
        {"_id": oid, "version": req.version},
        {"$set": {"text": req.text.strip()}, "$inc": {"version": 1}}
    )
    if result.modified_count == 0:
        raise HTTPException(409, "OCC conflict: comment was modified. Please refresh and retry.")

    updated = comments_col.find_one({"_id": oid})
    updated["username"] = current_user["username"]
    return serialize_comment(updated)


@router.delete("/{comment_id}")
def delete_comment(comment_id: str, current_user=Depends(get_current_user)):
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(400, "Invalid comment ID")

    comment = comments_col.find_one({"_id": oid})
    if not comment:
        raise HTTPException(404, "Comment not found")

    is_admin = current_user.get("username") == "admin_user"
    is_owner = str(comment["user_id"]) == str(current_user["_id"])
    if not is_admin and not is_owner:
        raise HTTPException(403, "Not authorized")

    comments_col.delete_one({"_id": oid})

    # Decrement comment count (OCC)
    post = posts_col.find_one({"_id": comment["post_id"]}, {"version": 1})
    if post:
        posts_col.update_one(
            {"_id": comment["post_id"], "version": post["version"]},
            {"$inc": {"metrics.comment_count": -1, "version": 1}}
        )

    return {"message": "Comment deleted"}
