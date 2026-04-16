from flask import Blueprint, request
from models.db import query, success, error

sources_bp = Blueprint("sources", __name__)

# GET /api/energy-sources?user_id=
@sources_bp.route("/", methods=["GET"])
def get_all():
    uid = request.args.get("user_id")
    sql = """SELECT es.*, rs.source_name, sm.meter_serial_number
             FROM energy_sources es
             JOIN renewable_sources rs ON rs.source_id = es.source_id
             LEFT JOIN smart_meters sm ON sm.meter_id = es.meter_id
             WHERE es.is_active=1"""
    args = []
    if uid:
        sql += " AND es.user_id=%s"
        args.append(uid)
    data, err = query(sql, args)
    if err: return error(err)
    return success(data)

# POST /api/energy-sources
@sources_bp.route("/", methods=["POST"])
def create():
    b = request.get_json()
    for f in ["user_id", "source_id", "capacity_kw"]:
        if b.get(f) is None: return error(f"{f} is required")
    data, err = query(
        """INSERT INTO energy_sources (user_id, source_id, meter_id, capacity_kw, installation_date)
           VALUES (%s,%s,%s,%s,%s)""",
        (b["user_id"], b["source_id"], b.get("meter_id"),
         b["capacity_kw"], b.get("installation_date")), fetch="none"
    )
    if err: return error(err)
    return success({"energy_source_id": data["lastrowid"]}, "Energy source added", 201)

# DELETE /api/energy-sources/<id>
@sources_bp.route("/<int:esid>", methods=["DELETE"])
def delete(esid):
    data, err = query(
        "UPDATE energy_sources SET is_active=0 WHERE energy_source_id=%s",
        (esid,), fetch="none"
    )
    if err: return error(err)
    return success(message="Energy source deactivated")
