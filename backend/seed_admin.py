from pymongo import MongoClient
from passlib.context import CryptContext
from datetime import datetime, timezone
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["SocialMediaDB"]
users_col = db["users"]



def seed_admin():
    admin_uname = "admin_user"
    if users_col.find_one({"username": admin_uname}):
        print("Admin user already exists.")
        return

    admin_doc = {
        "username": admin_uname,
        "email": "admin@pulsenet.com",
        "password": "admin123", # Default password
        "joined_at": datetime.now(timezone.utc),
        "stats": {"post_count": 0, "follower_count": 0},
        "version": 1,
    }
    users_col.insert_one(admin_doc)
    print(f"Admin user '{admin_uname}' created with password 'admin123'.")

if __name__ == "__main__":
    seed_admin()
