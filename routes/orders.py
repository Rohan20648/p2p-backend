from flask import Blueprint, request
from models.db import query, transact_with_cursor, success, error

orders_bp = Blueprint("orders", __name__)

# GET /api/orders?buyer_id=&status=
@orders_bp.route("/", methods=["GET"])
def get_all():
    filters, args = [], []
    bid = request.args.get("buyer_id")
    st  = request.args.get("status")
    if bid: filters.append("po.buyer_id=%s"); args.append(bid)
    if st:  filters.append("po.status=%s");   args.append(st)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT po.*, u.full_name AS buyer_name,
               el.price_per_kwh AS listing_price,
               gz.zone_code, ts.slot_name
        FROM purchase_orders po
        JOIN users u           ON u.user_id   = po.buyer_id
        JOIN energy_listings el ON el.listing_id = po.listing_id
        JOIN grid_zones gz     ON gz.zone_id  = po.zone_id
        JOIN time_slots ts     ON ts.slot_id  = po.slot_id
        {where} ORDER BY po.requested_at DESC
    """
    data, err = query(sql, args)
    if err: return error(err)
    return success(data)

# GET /api/orders/<id>
@orders_bp.route("/<int:oid>", methods=["GET"])
def get_one(oid):
    sql = """
        SELECT po.*, u.full_name AS buyer_name,
               gz.zone_code, ts.slot_name,
               tm.match_id, tm.units_matched_kwh, tm.agreed_price_per_kwh, tm.status AS match_status
        FROM purchase_orders po
        JOIN users u       ON u.user_id   = po.buyer_id
        JOIN grid_zones gz ON gz.zone_id  = po.zone_id
        JOIN time_slots ts ON ts.slot_id  = po.slot_id
        LEFT JOIN trade_matches tm ON tm.order_id = po.order_id
        WHERE po.order_id=%s
    """
    data, err = query(sql, (oid,), fetch="one")
    if err: return error(err)
    if not data: return error("Order not found", 404)
    return success(data)

# POST /api/orders  — fully atomic: one connection, one transaction
@orders_bp.route("/", methods=["POST"])
def create():
    b = request.get_json()
    for f in ["buyer_id", "listing_id", "units_requested_kwh"]:
        if b.get(f) is None: return error(f"{f} is required")

    units = float(b["units_requested_kwh"])

    def _atomic(conn, cur):
        # ── FIX #2 & #3: Everything in one connection/transaction ────────
        # Lock listing row with FOR UPDATE to prevent overselling
        cur.execute(
            "SELECT * FROM energy_listings WHERE listing_id=%s "
            "AND status IN ('active','partially_sold') FOR UPDATE",
            (b["listing_id"],)
        )
        listing = cur.fetchone()
        if not listing:
            raise ValueError("Listing not available")

        if units > float(listing["units_available_kwh"]):
            raise ValueError("Requested units exceed available units")

        price      = float(listing["price_per_kwh"])
        amount     = round(units * price, 4)
        fee        = round(amount * 0.025, 4)
        total      = round(amount + fee, 4)
        net_seller = round(amount - fee, 4)

        # FIX #3: Lock buyer wallet with FOR UPDATE — prevents TOCTOU race
        cur.execute(
            "SELECT * FROM wallets WHERE user_id=%s FOR UPDATE",
            (b["buyer_id"],)
        )
        wallet = cur.fetchone()
        if not wallet:
            raise ValueError("Buyer wallet not found")
        if float(wallet["balance"]) < total:
            raise ValueError("Insufficient wallet balance")

        # Lock seller wallet
        cur.execute(
            "SELECT wallet_id FROM wallets WHERE user_id=%s FOR UPDATE",
            (listing["seller_id"],)
        )
        s_wallet = cur.fetchone()
        if not s_wallet:
            raise ValueError("Seller wallet not found")

        buyer_wallet_id  = wallet["wallet_id"]
        seller_wallet_id = s_wallet["wallet_id"]

        # Insert purchase order
        cur.execute(
            """INSERT INTO purchase_orders
               (buyer_id, listing_id, zone_id, slot_id, units_requested_kwh, max_price_per_kwh, status)
               VALUES (%s,%s,%s,%s,%s,%s,'matched')""",
            (b["buyer_id"], b["listing_id"], listing["zone_id"],
             listing["slot_id"], units, price)
        )
        order_id = cur.lastrowid

        # Insert trade match
        cur.execute(
            """INSERT INTO trade_matches
               (order_id, listing_id, buyer_id, seller_id, units_matched_kwh, agreed_price_per_kwh, status)
               VALUES (%s,%s,%s,%s,%s,%s,'confirmed')""",
            (order_id, listing["listing_id"], b["buyer_id"],
             listing["seller_id"], units, price)
        )
        match_id = cur.lastrowid

        # Insert transaction record
        cur.execute(
            """INSERT INTO transactions
               (match_id, buyer_id, seller_id, amount, platform_fee, net_seller_amount, status)
               VALUES (%s,%s,%s,%s,%s,%s,'completed')""",
            (match_id, b["buyer_id"], listing["seller_id"], amount, fee, net_seller)
        )
        tx_id = cur.lastrowid

        # Debit buyer wallet (guarded: only proceeds if balance still sufficient)
        cur.execute(
            "UPDATE wallets SET balance=balance-%s WHERE user_id=%s AND balance>=%s",
            (total, b["buyer_id"], total)
        )
        if cur.rowcount == 0:
            raise ValueError("Insufficient wallet balance (concurrent update)")

        # Credit seller wallet
        cur.execute(
            "UPDATE wallets SET balance=balance+%s WHERE user_id=%s",
            (net_seller, listing["seller_id"])
        )

        # Payment records
        cur.execute(
            """INSERT INTO payments (transaction_id, wallet_id, payment_type, amount, status, paid_at)
               VALUES (%s,%s,'debit',%s,'success',NOW())""",
            (tx_id, buyer_wallet_id, total)
        )
        cur.execute(
            """INSERT INTO payments (transaction_id, wallet_id, payment_type, amount, status, paid_at)
               VALUES (%s,%s,'credit',%s,'success',NOW())""",
            (tx_id, seller_wallet_id, net_seller)
        )

        # Update listing units / status (trigger also does this, but be explicit)
        # Use round() + max() to guard against floating-point underflow producing
        # tiny negatives (e.g. 10.0 - 10.0 == -1.4e-14) which violates
        # the energy_listings_chk_1 constraint (units_available_kwh >= 0).
        new_units = max(0.0, round(float(listing["units_available_kwh"]) - units, 4))
        new_status = "sold" if new_units == 0 else "active"
        cur.execute(
            "UPDATE energy_listings SET units_available_kwh=%s, status=%s WHERE listing_id=%s",
            (new_units, new_status, listing["listing_id"])
        )

        return {
            "order_id":       order_id,
            "match_id":       match_id,
            "transaction_id": tx_id,
            "amount_charged": total,
            "platform_fee":   fee,
        }

    result, err = transact_with_cursor(_atomic)
    if err:
        # Surface user-friendly messages for expected errors
        msg = str(err)
        if "Listing not available" in msg or "Insufficient" in msg or "exceed" in msg:
            return error(msg, 400)
        return error(f"Order failed: {msg}")

    return success(result, "Order placed and payment processed", 201)

# PUT /api/orders/<id>/cancel
@orders_bp.route("/<int:oid>/cancel", methods=["PUT"])
def cancel(oid):
    data, err = query("UPDATE purchase_orders SET status='cancelled' WHERE order_id=%s",
                      (oid,), fetch="none")
    if err: return error(err)
    return success(message="Order cancelled")
