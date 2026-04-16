from flask import Blueprint, request
from models.db import query, success, error

stats_bp = Blueprint("stats", __name__)

# GET /api/stats/user/<user_id>  — per-user dashboard summary
@stats_bp.route("/user/<int:uid>", methods=["GET"])
def user_stats(uid):
    # Wallet balance
    wallet, _ = query("SELECT balance FROM wallets WHERE user_id=%s", (uid,), fetch="one")

    # Total produced
    produced, _ = query(
        """SELECT COALESCE(SUM(epl.units_produced_kwh),0) AS total
           FROM energy_production_logs epl
           JOIN smart_meters sm ON sm.meter_id = epl.meter_id
           WHERE sm.user_id=%s""", (uid,), fetch="one"
    )

    # Total consumed
    consumed, _ = query(
        """SELECT COALESCE(SUM(ecl.units_consumed_kwh),0) AS total
           FROM energy_consumption_logs ecl
           JOIN smart_meters sm ON sm.meter_id = ecl.meter_id
           WHERE sm.user_id=%s""", (uid,), fetch="one"
    )

    # Units sold (as seller)
    sold, _ = query(
        """SELECT COALESCE(SUM(tm.units_matched_kwh),0) AS total
           FROM trade_matches tm WHERE tm.seller_id=%s AND tm.status='completed'""",
        (uid,), fetch="one"
    )

    # Units bought (as buyer)
    bought, _ = query(
        """SELECT COALESCE(SUM(tm.units_matched_kwh),0) AS total
           FROM trade_matches tm WHERE tm.buyer_id=%s AND tm.status='completed'""",
        (uid,), fetch="one"
    )

    # Active listings count
    active_listings, _ = query(
        "SELECT COUNT(*) AS cnt FROM energy_listings WHERE seller_id=%s AND status='active'",
        (uid,), fetch="one"
    )

    # Total earnings (as seller)
    earnings, _ = query(
        """SELECT COALESCE(SUM(net_seller_amount),0) AS total
           FROM transactions WHERE seller_id=%s AND status='completed'""",
        (uid,), fetch="one"
    )

    # Total spent (as buyer, including fees)
    spent, _ = query(
        """SELECT COALESCE(SUM(amount + platform_fee),0) AS total
           FROM transactions WHERE buyer_id=%s AND status='completed'""",
        (uid,), fetch="one"
    )

    return success({
        "wallet_balance":    float(wallet["balance"])         if wallet else 0,
        "total_produced_kwh": float(produced["total"])        if produced else 0,
        "total_consumed_kwh": float(consumed["total"])        if consumed else 0,
        "units_sold_kwh":    float(sold["total"])             if sold else 0,
        "units_bought_kwh":  float(bought["total"])           if bought else 0,
        "active_listings":   int(active_listings["cnt"])      if active_listings else 0,
        "total_earnings":    float(earnings["total"])         if earnings else 0,
        "total_spent":       float(spent["total"])            if spent else 0,
    })

# GET /api/stats/platform  — admin overview
@stats_bp.route("/platform", methods=["GET"])
def platform_stats():
    users_count, _  = query("SELECT COUNT(*) AS cnt FROM users WHERE is_active=1", fetch="one")
    listings_cnt, _ = query("SELECT COUNT(*) AS cnt FROM energy_listings WHERE status='active'", fetch="one")
    tx_total, _     = query(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(amount),0) AS vol FROM transactions WHERE status='completed'",
        fetch="one"
    )
    energy_traded, _ = query(
        "SELECT COALESCE(SUM(units_matched_kwh),0) AS total FROM trade_matches WHERE status='completed'",
        fetch="one"
    )
    disputes_open, _ = query(
        "SELECT COUNT(*) AS cnt FROM disputes WHERE status='open'", fetch="one"
    )

    return success({
        "active_users":      int(users_count["cnt"])        if users_count else 0,
        "active_listings":   int(listings_cnt["cnt"])       if listings_cnt else 0,
        "total_transactions": int(tx_total["cnt"])          if tx_total else 0,
        "transaction_volume": float(tx_total["vol"])        if tx_total else 0,
        "energy_traded_kwh": float(energy_traded["total"])  if energy_traded else 0,
        "open_disputes":     int(disputes_open["cnt"])      if disputes_open else 0,
    })

# GET /api/stats/zone/<zone_id>
@stats_bp.route("/zone/<int:zid>", methods=["GET"])
def zone_stats(zid):
    listings, _ = query(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(units_available_kwh),0) AS units FROM energy_listings WHERE zone_id=%s AND status='active'",
        (zid,), fetch="one"
    )
    demand, _ = query(
        """SELECT predicted_demand_kwh, predicted_supply_kwh, confidence_pct
           FROM demand_forecasts WHERE zone_id=%s
           ORDER BY forecast_date DESC, forecast_id DESC LIMIT 1""",
        (zid,), fetch="one"
    )
    return success({
        "active_listings": int(listings["cnt"]) if listings else 0,
        "available_kwh":   float(listings["units"]) if listings else 0,
        "latest_forecast": demand or {}
    })
