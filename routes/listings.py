from flask import Blueprint, request
from models.db import query, success, error

listings_bp = Blueprint("listings", __name__)

# GET /api/listings  — supports ?zone_id=&slot_id=&status=&source=
@listings_bp.route("/", methods=["GET"])
def get_all():
    filters, args = [], []
    z = request.args.get("zone_id")
    sl = request.args.get("slot_id")
    st = request.args.get("status", "active")
    src = request.args.get("source")

    if z:   filters.append("el.zone_id=%s");          args.append(z)
    if sl:  filters.append("el.slot_id=%s");           args.append(sl)
    if st:  filters.append("el.status=%s");            args.append(st)
    if src: filters.append("rs.source_name=%s");       args.append(src)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT el.*, u.full_name AS seller_name,
               gz.zone_code, gz.zone_name,
               ts.slot_name, ts.slot_type,
               rs.source_name AS source_type
        FROM energy_listings el
        JOIN users u   ON u.user_id   = el.seller_id
        JOIN grid_zones gz ON gz.zone_id = el.zone_id
        JOIN time_slots ts ON ts.slot_id = el.slot_id
        LEFT JOIN energy_sources es ON es.energy_source_id = el.energy_source_id
        LEFT JOIN renewable_sources rs ON rs.source_id = es.source_id
        {where}
        ORDER BY el.created_at DESC
    """
    data, err = query(sql, args)
    if err: return error(err)
    return success(data)

# GET /api/listings/<id>
@listings_bp.route("/<int:lid>", methods=["GET"])
def get_one(lid):
    sql = """
        SELECT el.*, u.full_name AS seller_name,
               gz.zone_code, gz.zone_name,
               ts.slot_name, ts.slot_type,
               rs.source_name AS source_type
        FROM energy_listings el
        JOIN users u   ON u.user_id   = el.seller_id
        JOIN grid_zones gz ON gz.zone_id = el.zone_id
        JOIN time_slots ts ON ts.slot_id = el.slot_id
        LEFT JOIN energy_sources es ON es.energy_source_id = el.energy_source_id
        LEFT JOIN renewable_sources rs ON rs.source_id = es.source_id
        WHERE el.listing_id=%s
    """
    data, err = query(sql, (lid,), fetch="one")
    if err: return error(err)
    if not data: return error("Listing not found", 404)
    return success(data)

# GET /api/listings/seller/<seller_id>
@listings_bp.route("/seller/<int:sid>", methods=["GET"])
def get_by_seller(sid):
    sql = """
        SELECT el.*, gz.zone_code, ts.slot_name, rs.source_name AS source_type
        FROM energy_listings el
        JOIN grid_zones gz ON gz.zone_id = el.zone_id
        JOIN time_slots ts ON ts.slot_id = el.slot_id
        LEFT JOIN energy_sources es ON es.energy_source_id = el.energy_source_id
        LEFT JOIN renewable_sources rs ON rs.source_id = es.source_id
        WHERE el.seller_id=%s ORDER BY el.created_at DESC
    """
    data, err = query(sql, (sid,))
    if err: return error(err)
    return success(data)

# POST /api/listings
@listings_bp.route("/", methods=["POST"])
def create():
    b = request.get_json()
    for f in ["seller_id", "zone_id", "slot_id", "units_available_kwh", "price_per_kwh", "listing_date"]:
        if b.get(f) is None: return error(f"{f} is required")

    sql = """INSERT INTO energy_listings
             (seller_id, zone_id, slot_id, energy_source_id, units_available_kwh,
              price_per_kwh, listing_date, expires_at, status)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'active')"""
    data, err = query(sql, (
        b["seller_id"], b["zone_id"], b["slot_id"],
        b.get("energy_source_id"), b["units_available_kwh"],
        b["price_per_kwh"], b["listing_date"],
        b.get("expires_at")
    ), fetch="none")
    if err: return error(err)
    return success({"listing_id": data["lastrowid"]}, "Listing created", 201)

# PUT /api/listings/<id>/cancel
@listings_bp.route("/<int:lid>/cancel", methods=["PUT"])
def cancel(lid):
    data, err = query("UPDATE energy_listings SET status='cancelled' WHERE listing_id=%s",
                      (lid,), fetch="none")
    if err: return error(err)
    return success(message="Listing cancelled")

# DELETE /api/listings/<id>
@listings_bp.route("/<int:lid>", methods=["DELETE"])
def delete(lid):
    data, err = query("DELETE FROM energy_listings WHERE listing_id=%s", (lid,), fetch="none")
    if err: return error(err)
    return success(message="Listing deleted")
