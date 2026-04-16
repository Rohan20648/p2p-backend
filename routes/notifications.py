from flask import Blueprint, request
from models.db import query, success, error

notifications_bp = Blueprint("notifications", __name__)

# GET /api/notifications/<user_id>?unread=true
@notifications_bp.route("/<int:uid>", methods=["GET"])
def get_all(uid):
    unread = request.args.get("unread")
    sql = """SELECT n.*, nt.type_name
             FROM notifications n
             JOIN notification_types nt ON nt.type_id = n.type_id
             WHERE n.user_id=%s"""
    args = [uid]
    if unread == "true":
        sql += " AND n.is_read=0"
    sql += " ORDER BY n.sent_at DESC LIMIT 50"
    data, err = query(sql, args)
    if err: return error(err)
    return success(data)

# PUT /api/notifications/<id>/read
@notifications_bp.route("/<int:nid>/read", methods=["PUT"])
def mark_read(nid):
    data, err = query(
        "UPDATE notifications SET is_read=1, read_at=NOW() WHERE notification_id=%s",
        (nid,), fetch="none"
    )
    if err: return error(err)
    return success(message="Notification marked as read")

# PUT /api/notifications/read-all/<user_id>
@notifications_bp.route("/read-all/<int:uid>", methods=["PUT"])
def mark_all_read(uid):
    data, err = query(
        "UPDATE notifications SET is_read=1, read_at=NOW() WHERE user_id=%s AND is_read=0",
        (uid,), fetch="none"
    )
    if err: return error(err)
    return success(message="All notifications marked as read")

# POST /api/notifications  (internal / admin use)
@notifications_bp.route("/", methods=["POST"])
def create():
    b = request.get_json()
    for f in ["user_id", "type_id", "message"]:
        if not b.get(f): return error(f"{f} is required")
    data, err = query(
        "INSERT INTO notifications (user_id, type_id, message) VALUES (%s,%s,%s)",
        (b["user_id"], b["type_id"], b["message"]), fetch="none"
    )
    if err: return error(err)
    return success({"notification_id": data["lastrowid"]}, "Notification sent", 201)
