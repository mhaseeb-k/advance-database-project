import random
from pymongo import MongoClient, ASCENDING, DESCENDING
from faker import Faker
from pymongo.errors import DuplicateKeyError

client = MongoClient("mongodb://localhost:27017/")
db = client["SocialMediaDB"]
fake = Faker()


def setup_database():
    print("Resetting database...")

    db.users.drop()
    db.posts.drop()
    db.comments.drop()

    db.users.create_index([("username", ASCENDING)], unique=True)
    db.posts.create_index([("author.user_id", ASCENDING)])
    db.posts.create_index([("timestamp", DESCENDING)])
    db.comments.create_index([("post_id", ASCENDING)])


# =========================================================
# Optimistic Concurrency Control Helper
# =========================================================
def optimistic_update(collection, document_id, current_version, update_fields):
    """
    Update document only if version matches.
    """

    result = collection.update_one(
        {
            "_id": document_id,
            "version": current_version
        },
        {
            "$set": update_fields,
            "$inc": {"version": 1}
        }
    )

    return result.modified_count == 1


def insert_data():

    # ---------------- USERS ----------------
    print("Inserting users...")

    users = []
    seen = set()

    for _ in range(5000):

        while True:
            uname = f"{fake.user_name()}_{random.randint(1000, 9999)}"

            if uname not in seen:
                seen.add(uname)
                break

        users.append({
            "username": uname,

            "password": fake.password(
                length=8,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True
            ),
            "version": 1,

            "email": fake.unique.email(),
            "joined_at": fake.date_time_this_year(),

            "stats": {
                "post_count": 0,
                "follower_count": random.randint(0, 5000)
            }
})

    db.users.insert_many(users)

    # Reload users with IDs
    user_pool = list(
        db.users.find({}, {"_id": 1, "username": 1, "version": 1})
    )

    # ---------------- POSTS ----------------
    print("Inserting posts...")

    posts = []
    user_post_map = {u["_id"]: 0 for u in user_pool}

    for _ in range(25000):

        author = random.choice(user_pool)

        posts.append({
            "author": {
                "user_id": author["_id"],
                "username": author["username"]
            },

            "content": fake.text(max_nb_chars=280),
            "timestamp": fake.date_time_this_year(),

            # OCC VERSION FIELD
            "version": 1,

            "metrics": {
                "likes": random.randint(0, 1000),
                "comment_count": 0
            }
        })

        user_post_map[author["_id"]] += 1

    post_result = db.posts.insert_many(posts)
    post_ids = post_result.inserted_ids

    # =========================================================
    # OCC UPDATE: USER POST COUNTS
    # =========================================================
    print("Updating user post counts with OCC...")

    for user_id, count in user_post_map.items():

        user_doc = db.users.find_one(
            {"_id": user_id},
            {"version": 1}
        )

        success = optimistic_update(
            collection=db.users,
            document_id=user_id,
            current_version=user_doc["version"],
            update_fields={
                "stats.post_count": count
            }
        )

        if not success:
            print(f"[OCC CONFLICT] User {user_id} update failed.")

    # ---------------- COMMENTS ----------------
    print("Inserting comments...")

    comments = []
    post_comment_map = {pid: 0 for pid in post_ids}

    user_ids = [u["_id"] for u in user_pool]

    for _ in range(70000):

        pid = random.choice(post_ids)

        comments.append({
            "post_id": pid,
            "user_id": random.choice(user_ids),
            "text": fake.sentence(),
            "timestamp": fake.date_time_this_year(),

            # OCC VERSION FIELD
            "version": 1
        })

        post_comment_map[pid] += 1

    db.comments.insert_many(comments)

    # =========================================================
    # OCC UPDATE: COMMENT COUNTS
    # =========================================================
    print("Updating post comment counts with OCC...")

    for post_id, count in post_comment_map.items():

        post_doc = db.posts.find_one(
            {"_id": post_id},
            {"version": 1}
        )

        success = optimistic_update(
            collection=db.posts,
            document_id=post_id,
            current_version=post_doc["version"],
            update_fields={
                "metrics.comment_count": count
            }
        )

        if not success:
            print(f"[OCC CONFLICT] Post {post_id} update failed.")

    print("Done! Database created with OCC protection.")


if __name__ == "__main__":
    setup_database()
    insert_data()