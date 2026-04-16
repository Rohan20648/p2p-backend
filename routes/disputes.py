from flask import Blueprint, request
from models.db import query, success, error

disputes_bp = Blueprint("disputes", __name__)

# GET /api/disputes?status=open&user_id=
@disputes_bp.route("/", methods=["GET"])
def get_all():
    filters, args = [], []
    st  = request.args.get("status")
    uid = request.args.get("user_id")
    if st:  filters.append("d.status=%s");                     args.append(st)
    if uid: filters.append("(d.raised_by=%s OR d.against_user_id=%s)"); args += [uid, uid]
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT d.*, rb.full_name AS raised_by_name, ag.full_name AS against_name
        FROM disputes d
        JOIN users rb ON rb.user_id = d.raised_by
        JOIN users ag ON ag.user_id = d.against_user_id
        {where} ORDER BY d.raised_at DESC
    """
    data, err = query(sql, args)
    if err: return error(err)
    return success(data)

# GET /api/disputes/<id>
@disputes_bp.route("/<int:did>", methods=["GET"])
def get_one(did):
    sql = """SELECT d.*, rb.full_name AS raised_by_name, ag.full_name AS against_name
             FROM disputes d
             JOIN users rb ON rb.user_id = d.raised_by
             JOIN users ag ON ag.user_id = d.against_user_id
             WHERE d.dispute_id=%s"""
    data, err = query(sql, (did,), fetch="one")
    if err: return error(err)
    if not data: return error("Dispute not found", 404)
    return success(data)

# POST /api/disputes
@disputes_bp.route("/", methods=["POST"])
def create():
    b = request.get_json()
    for f in ["transaction_id", "raised_by", "against_user_id", "reason"]:
        if not b.get(f): return error(f"{f} is required")
    data, err = query(
        """INSERT INTO disputes (transaction_id, raised_by, against_user_id, reason)
           VALUES (%s,%s,%s,%s)""",
        (b["transaction_id"], b["raised_by"], b["against_user_id"], b["reason"]),
        fetch="none"
    )
    if err: return error(err)
    return success({"dispute_id": data["lastrowid"]}, "Dispute raised", 201)

# PUT /api/disputes/<id>/resolve  (admin)
@disputes_bp.route("/<int:did>/resolve", methods=["PUT"])
def resolve(did):
    b = request.get_json()
    data, err = query(
        """UPDATE disputes SET status='resolved', resolution=%s,
           resolved_at=NOW(), resolved_by=%s WHERE dispute_id=%s""",
        (b.get("resolution"), b.get("resolved_by"), did), fetch="none"
    )
    if err: return error(err)
    return success(message="Dispute resolved")
