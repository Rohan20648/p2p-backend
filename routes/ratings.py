from flask import Blueprint, request
from models.db import query, success, error

ratings_bp = Blueprint("ratings", __name__)

# GET /api/ratings/user/<user_id>  — ratings received by a user
@ratings_bp.route("/user/<int:uid>", methods=["GET"])
def get_for_user(uid):
    sql = """SELECT r.*, u.full_name AS rater_name
             FROM ratings r JOIN users u ON u.user_id = r.rater_id
             WHERE r.rated_user_id=%s ORDER BY r.created_at DESC"""
    data, err = query(sql, (uid,))
    if err: return error(err)

    avg, _ = query(
        "SELECT ROUND(AVG(rating_value),2) AS avg_rating, COUNT(*) AS count FROM ratings WHERE rated_user_id=%s",
        (uid,), fetch="one"
    )
    return success({"ratings": data, "average": avg["avg_rating"] if avg else None, "count": avg["count"] if avg else 0})

# POST /api/ratings
@ratings_bp.route("/", methods=["POST"])
def create():
    b = request.get_json()
    for f in ["transaction_id", "rater_id", "rated_user_id", "rating_value"]:
        if b.get(f) is None: return error(f"{f} is required")
    if not (1 <= int(b["rating_value"]) <= 5):
        return error("rating_value must be 1-5")
    data, err = query(
        """INSERT INTO ratings (transaction_id, rater_id, rated_user_id, rating_value, review_text)
           VALUES (%s,%s,%s,%s,%s)""",
        (b["transaction_id"], b["rater_id"], b["rated_user_id"],
         b["rating_value"], b.get("review_text")), fetch="none"
    )
    if err: return error(err)
    return success({"rating_id": data["lastrowid"]}, "Rating submitted", 201)
