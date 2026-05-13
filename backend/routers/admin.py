from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId
from database import users_col, posts_col, comments_col
from auth_utils import get_admin_user, serialize_user, serialize_post, serialize_comment

router = APIRouter()


class AdminUpdateUser(BaseModel):
    email: str | None = None
    password: str | None = None
    username: str | None = None


class AdminUpdatePost(BaseModel):
    content: str


class AdminUpdateComment(BaseModel):
    text: str


# ======================== USERS ========================

@router.get("/users")
def list_all_users(skip: int = 0, limit: int = 50, admin=Depends(get_admin_user)):
    users = list(users_col.find().skip(skip).limit(limit))
    return [serialize_user(u) for u in users]


@router.delete("/users/{user_id}")
def admin_delete_user(user_id: str, admin=Depends(get_admin_user)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "Invalid ID")
    if not users_col.find_one({"_id": oid}):
        raise HTTPException(404, "User not found")
    users_col.delete_one({"_id": oid})
    posts_col.delete_many({"author.user_id": oid})
    comments_col.delete_many({"user_id": oid})
    return {"message": "User and all their content deleted"}


@router.patch("/users/{user_id}")
def admin_update_user(user_id: str, req: AdminUpdateUser, admin=Depends(get_admin_user)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "Invalid ID")
    user = users_col.find_one({"_id": oid})
    if not user:
        raise HTTPException(404, "User not found")

    updates = {}
    if req.email:
        updates["email"] = req.email
    if req.username:
        updates["username"] = req.username
    if req.password:
        updates["password"] = req.password

    if updates:
        users_col.update_one(
            {"_id": oid, "version": user["version"]},
            {"$set": updates, "$inc": {"version": 1}}
        )
    return serialize_user(users_col.find_one({"_id": oid}))


# ======================== POSTS ========================

@router.get("/posts")
def list_all_posts(skip: int = 0, limit: int = 50, admin=Depends(get_admin_user)):
    posts = list(posts_col.find().sort("timestamp", -1).skip(skip).limit(limit))
    return [serialize_post(p) for p in posts]


@router.delete("/posts/{post_id}")
def admin_delete_post(post_id: str, admin=Depends(get_admin_user)):
    try:
        oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(400, "Invalid ID")
    post = posts_col.find_one({"_id": oid})
    if not post:
        raise HTTPException(404, "Post not found")
    posts_col.delete_one({"_id": oid})
    comments_col.delete_many({"post_id": oid})
    return {"message": "Post deleted"}


@router.patch("/posts/{post_id}")
def admin_update_post(post_id: str, req: AdminUpdatePost, admin=Depends(get_admin_user)):
    try:
        oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(400, "Invalid ID")
    post = posts_col.find_one({"_id": oid})
    if not post:
        raise HTTPException(404, "Post not found")
    posts_col.update_one(
        {"_id": oid, "version": post["version"]},
        {"$set": {"content": req.content}, "$inc": {"version": 1}}
    )
    return serialize_post(posts_col.find_one({"_id": oid}))


# ======================== COMMENTS ========================

@router.get("/comments")
def list_all_comments(skip: int = 0, limit: int = 50, admin=Depends(get_admin_user)):
    comments = list(comments_col.find().sort("timestamp", -1).skip(skip).limit(limit))
    return [serialize_comment(c) for c in comments]


@router.delete("/comments/{comment_id}")
def admin_delete_comment(comment_id: str, admin=Depends(get_admin_user)):
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(400, "Invalid ID")
    comment = comments_col.find_one({"_id": oid})
    if not comment:
        raise HTTPException(404, "Comment not found")
    comments_col.delete_one({"_id": oid})
    post = posts_col.find_one({"_id": comment["post_id"]}, {"version": 1})
    if post:
        posts_col.update_one(
            {"_id": comment["post_id"], "version": post["version"]},
            {"$inc": {"metrics.comment_count": -1, "version": 1}}
        )
    return {"message": "Comment deleted"}


@router.patch("/comments/{comment_id}")
def admin_update_comment(comment_id: str, req: AdminUpdateComment, admin=Depends(get_admin_user)):
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(400, "Invalid ID")
    comment = comments_col.find_one({"_id": oid})
    if not comment:
        raise HTTPException(404, "Comment not found")
    comments_col.update_one(
        {"_id": oid, "version": comment["version"]},
        {"$set": {"text": req.text}, "$inc": {"version": 1}}
    )
    return serialize_comment(comments_col.find_one({"_id": oid}))


# ======================== STATS ========================

@router.get("/stats")
def get_db_stats(admin=Depends(get_admin_user)):
    return {
        "total_users": users_col.count_documents({}),
        "total_posts": posts_col.count_documents({}),
        "total_comments": comments_col.count_documents({}),
    }
