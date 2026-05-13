from fastapi import APIRouter
from database import posts_col
from auth_utils import serialize_post

router = APIRouter()

TRENDING_WEIGHT_LIKES = 1.0
TRENDING_WEIGHT_COMMENTS = 2.0


@router.get("/trending")
def get_trending_feed(skip: int = 0, limit: int = 20):
    """
    Trending feed: sorted by a weighted score = likes + 2 * comment_count.
    Uses MongoDB aggregation pipeline.
    """
    pipeline = [
        {
            "$addFields": {
                "trending_score": {
                    "$add": [
                        {"$multiply": ["$metrics.likes", TRENDING_WEIGHT_LIKES]},
                        {"$multiply": ["$metrics.comment_count", TRENDING_WEIGHT_COMMENTS]},
                    ]
                }
            }
        },
        {"$sort": {"trending_score": -1}},
        {"$skip": skip},
        {"$limit": limit},
    ]
    posts = list(posts_col.aggregate(pipeline))
    return [serialize_post(p) for p in posts]


@router.get("/recent")
def get_recent_feed(skip: int = 0, limit: int = 20):
    """Latest posts feed."""
    posts = list(posts_col.find().sort("timestamp", -1).skip(skip).limit(limit))
    return [serialize_post(p) for p in posts]


@router.get("/top-liked")
def get_top_liked(skip: int = 0, limit: int = 20):
    """Top liked posts."""
    posts = list(posts_col.find().sort("metrics.likes", -1).skip(skip).limit(limit))
    return [serialize_post(p) for p in posts]
