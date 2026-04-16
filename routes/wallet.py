from flask import Blueprint, request
from models.db import query, success, error

wallet_bp = Blueprint("wallet", __name__)

# GET /api/wallet/<user_id>
@wallet_bp.route("/<int:uid>", methods=["GET"])
def get_balance(uid):
    data, err = query("SELECT * FROM wallets WHERE user_id=%s", (uid,), fetch="one")
    if err: return error(err)
    if not data: return error("Wallet not found", 404)
    return success(data)

# POST /api/wallet/<user_id>/recharge
@wallet_bp.route("/<int:uid>/recharge", methods=["POST"])
def recharge(uid):
    b = request.get_json()
    amount = b.get("amount")
    method = b.get("payment_method", "upi")
    ref    = b.get("gateway_reference", f"REF{uid}-{__import__('time').time_ns()}")

    if not amount or float(amount) < 50:
        return error("Minimum recharge is ₹50")
    if float(amount) > 50000:
        return error("Maximum recharge is ₹50,000")

    wallet, err = query("SELECT wallet_id FROM wallets WHERE user_id=%s", (uid,), fetch="one")
    if err: return error(err)
    if not wallet: return error("Wallet not found", 404)
    wid = wallet["wallet_id"]

    # Log recharge
    r_data, err2 = query(
        """INSERT INTO wallet_recharge_logs
           (wallet_id, amount, payment_method, gateway_reference, status, completed_at)
           VALUES (%s,%s,%s,%s,'success',NOW())""",
        (wid, amount, method, ref), fetch="none"
    )
    if err2: return error(err2)

    # Credit wallet
    query("UPDATE wallets SET balance=balance+%s WHERE wallet_id=%s",
          (amount, wid), fetch="none")

    # Fetch updated balance
    updated, _ = query("SELECT balance FROM wallets WHERE wallet_id=%s", (wid,), fetch="one")
    return success({"new_balance": updated["balance"], "recharged": amount}, "Wallet recharged")

# GET /api/wallet/<user_id>/recharge-history
@wallet_bp.route("/<int:uid>/recharge-history", methods=["GET"])
def recharge_history(uid):
    sql = """
        SELECT wrl.*
        FROM wallet_recharge_logs wrl
        JOIN wallets w ON w.wallet_id = wrl.wallet_id
        WHERE w.user_id=%s
        ORDER BY wrl.initiated_at DESC
    """
    data, err = query(sql, (uid,))
    if err: return error(err)
    return success(data)
