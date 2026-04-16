from flask import Blueprint, request
from models.db import query, success, error

transactions_bp = Blueprint("transactions", __name__)

# GET /api/transactions?buyer_id=&seller_id=&status=
@transactions_bp.route("/", methods=["GET"])
def get_all():
    filters, args = [], []
    bid = request.args.get("buyer_id")
    sid = request.args.get("seller_id")
    st  = request.args.get("status")
    uid = request.args.get("user_id")   # buyer OR seller
    if uid:
        filters.append("(t.buyer_id=%s OR t.seller_id=%s)")
        args += [uid, uid]
    else:
        if bid: filters.append("t.buyer_id=%s");  args.append(bid)
        if sid: filters.append("t.seller_id=%s"); args.append(sid)
    if st: filters.append("t.status=%s"); args.append(st)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT t.*,
               b.full_name AS buyer_name,
               s.full_name AS seller_name,
               tm.units_matched_kwh AS units_kwh
        FROM transactions t
        JOIN users b ON b.user_id = t.buyer_id
        JOIN users s ON s.user_id = t.seller_id
        LEFT JOIN trade_matches tm ON tm.match_id = t.match_id
        {where}
        ORDER BY t.created_at DESC
    """
    data, err = query(sql, args)
    if err: return error(err)
    return success(data)

# GET /api/transactions/<id>
@transactions_bp.route("/<int:tid>", methods=["GET"])
def get_one(tid):
    sql = """
        SELECT t.*, b.full_name AS buyer_name, s.full_name AS seller_name,
               tm.units_matched_kwh AS units_kwh, tm.agreed_price_per_kwh
        FROM transactions t
        JOIN users b ON b.user_id = t.buyer_id
        JOIN users s ON s.user_id = t.seller_id
        LEFT JOIN trade_matches tm ON tm.match_id = t.match_id
        WHERE t.transaction_id=%s
    """
    data, err = query(sql, (tid,), fetch="one")
    if err: return error(err)
    if not data: return error("Transaction not found", 404)
    return success(data)
