from pymongo import MongoClient, ASCENDING, DESCENDING
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["SocialMediaDB"]

users_col    = db["users"]
posts_col    = db["posts"]
comments_col = db["comments"]

# Ensure indexes
users_col.create_index([("username", ASCENDING)], unique=True)
users_col.create_index([("email", ASCENDING)], unique=True)
posts_col.create_index([("author.user_id", ASCENDING)])
posts_col.create_index([("timestamp", DESCENDING)])
posts_col.create_index([("metrics.likes", DESCENDING)])
comments_col.create_index([("post_id", ASCENDING)])
comments_col.create_index([("user_id", ASCENDING)])
