from flask import Blueprint, request
from models.db import query, success, error

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
        JOIN users u       ON u.user_id   = po.buyer_id
        JOIN energy_listings el ON el.listing_id = po.listing_id
        JOIN grid_zones gz ON gz.zone_id  = po.zone_id
        JOIN time_slots ts ON ts.slot_id  = po.slot_id
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

# POST /api/orders  — place a buy order and auto-match + process payment
@orders_bp.route("/", methods=["POST"])
def create():
    b = request.get_json()
    for f in ["buyer_id", "listing_id", "units_requested_kwh"]:
        if b.get(f) is None: return error(f"{f} is required")

    # Fetch listing
    listing, err = query(
        "SELECT * FROM energy_listings WHERE listing_id=%s AND status IN ('active','partially_sold')",
        (b["listing_id"],), fetch="one"
    )
    if err: return error(err)
    if not listing: return error("Listing not available", 404)

    units = float(b["units_requested_kwh"])
    if units > float(listing["units_available_kwh"]):
        return error("Requested units exceed available units")

    price = float(listing["price_per_kwh"])
    amount = round(units * price, 4)
    fee    = round(amount * 0.025, 4)
    total  = round(amount + fee, 4)

    # Check buyer wallet
    wallet, err2 = query("SELECT * FROM wallets WHERE user_id=%s", (b["buyer_id"],), fetch="one")
    if err2: return error(err2)
    if not wallet: return error("Buyer wallet not found")
    if float(wallet["balance"]) < total:
        return error("Insufficient wallet balance")

    # Insert order
    o_data, err3 = query(
        """INSERT INTO purchase_orders
           (buyer_id, listing_id, zone_id, slot_id, units_requested_kwh, max_price_per_kwh, status)
           VALUES (%s,%s,%s,%s,%s,%s,'matched')""",
        (b["buyer_id"], b["listing_id"], listing["zone_id"],
         listing["slot_id"], units, price), fetch="none"
    )
    if err3: return error(err3)
    order_id = o_data["lastrowid"]

    # Insert trade match
    m_data, err4 = query(
        """INSERT INTO trade_matches
           (order_id, listing_id, buyer_id, seller_id, units_matched_kwh, agreed_price_per_kwh, status)
           VALUES (%s,%s,%s,%s,%s,%s,'confirmed')""",
        (order_id, listing["listing_id"], b["buyer_id"],
         listing["seller_id"], units, price), fetch="none"
    )
    if err4: return error(err4)
    match_id = m_data["lastrowid"]

    # Insert transaction
    net_seller = round(amount - fee, 4)
    t_data, err5 = query(
        """INSERT INTO transactions
           (match_id, buyer_id, seller_id, amount, platform_fee, net_seller_amount, status)
           VALUES (%s,%s,%s,%s,%s,%s,'completed')""",
        (match_id, b["buyer_id"], listing["seller_id"], amount, fee, net_seller), fetch="none"
    )
    if err5: return error(err5)
    tx_id = t_data["lastrowid"]

    # Deduct buyer wallet
    query("UPDATE wallets SET balance=balance-%s WHERE user_id=%s",
          (total, b["buyer_id"]), fetch="none")
    # Credit seller wallet
    query("UPDATE wallets SET balance=balance+%s WHERE user_id=%s",
          (net_seller, listing["seller_id"]), fetch="none")

    # Payment records
    b_wallet_id = wallet["wallet_id"]
    s_wallet, _ = query("SELECT wallet_id FROM wallets WHERE user_id=%s",
                         (listing["seller_id"],), fetch="one")
    query("""INSERT INTO payments (transaction_id, wallet_id, payment_type, amount, status, paid_at)
             VALUES (%s,%s,'debit',%s,'success',NOW())""",
          (tx_id, b_wallet_id, total), fetch="none")
    if s_wallet:
        query("""INSERT INTO payments (transaction_id, wallet_id, payment_type, amount, status, paid_at)
                 VALUES (%s,%s,'credit',%s,'success',NOW())""",
              (tx_id, s_wallet["wallet_id"], net_seller), fetch="none")

    return success({
        "order_id": order_id,
        "match_id": match_id,
        "transaction_id": tx_id,
        "amount_charged": total,
        "platform_fee": fee
    }, "Order placed and payment processed", 201)

# PUT /api/orders/<id>/cancel
@orders_bp.route("/<int:oid>/cancel", methods=["PUT"])
def cancel(oid):
    data, err = query("UPDATE purchase_orders SET status='cancelled' WHERE order_id=%s",
                      (oid,), fetch="none")
    if err: return error(err)
    return success(message="Order cancelled")
