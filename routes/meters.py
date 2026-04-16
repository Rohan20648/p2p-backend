from flask import Blueprint, request
from models.db import query, success, error

meters_bp = Blueprint("meters", __name__)

# GET /api/meters?user_id=
@meters_bp.route("/", methods=["GET"])
def get_all():
    uid = request.args.get("user_id")
    sql = """SELECT sm.*, gz.zone_code, gz.zone_name
             FROM smart_meters sm
             JOIN grid_zones gz ON gz.zone_id = sm.zone_id
             WHERE sm.is_active=1"""
    args = []
    if uid:
        sql += " AND sm.user_id=%s"
        args.append(uid)
    data, err = query(sql, args)
    if err: return error(err)
    return success(data)

# GET /api/meters/<id>
@meters_bp.route("/<int:mid>", methods=["GET"])
def get_one(mid):
    sql = """SELECT sm.*, gz.zone_code, u.full_name AS owner_name
             FROM smart_meters sm
             JOIN grid_zones gz ON gz.zone_id = sm.zone_id
             JOIN users u ON u.user_id = sm.user_id
             WHERE sm.meter_id=%s"""
    data, err = query(sql, (mid,), fetch="one")
    if err: return error(err)
    if not data: return error("Meter not found", 404)
    return success(data)

# POST /api/meters
@meters_bp.route("/", methods=["POST"])
def create():
    b = request.get_json()
    for f in ["user_id", "zone_id", "meter_serial_number", "meter_type", "installation_date"]:
        if not b.get(f): return error(f"{f} is required")
    sql = """INSERT INTO smart_meters
             (user_id, zone_id, meter_serial_number, meter_type, installation_date, firmware_version)
             VALUES (%s,%s,%s,%s,%s,%s)"""
    data, err = query(sql, (
        b["user_id"], b["zone_id"], b["meter_serial_number"],
        b["meter_type"], b["installation_date"], b.get("firmware_version")
    ), fetch="none")
    if err: return error(err)
    return success({"meter_id": data["lastrowid"]}, "Meter registered", 201)

# ── Energy Production Logs ──────────────────────────────
# GET /api/meters/<id>/production?limit=50
@meters_bp.route("/<int:mid>/production", methods=["GET"])
def get_production(mid):
    limit = int(request.args.get("limit", 50))
    sql = """SELECT epl.*, ts.slot_name, rs.source_name
             FROM energy_production_logs epl
             LEFT JOIN time_slots ts ON ts.slot_id = epl.slot_id
             LEFT JOIN energy_sources es ON es.energy_source_id = epl.energy_source_id
             LEFT JOIN renewable_sources rs ON rs.source_id = es.source_id
             WHERE epl.meter_id=%s
             ORDER BY epl.log_timestamp DESC LIMIT %s"""
    data, err = query(sql, (mid, limit))
    if err: return error(err)
    return success(data)

# POST /api/meters/<id>/production
@meters_bp.route("/<int:mid>/production", methods=["POST"])
def log_production(mid):
    b = request.get_json()
    sql = """INSERT INTO energy_production_logs
             (meter_id, energy_source_id, slot_id, units_produced_kwh, log_timestamp)
             VALUES (%s,%s,%s,%s,%s)"""
    data, err = query(sql, (
        mid, b["energy_source_id"], b.get("slot_id"),
        b["units_produced_kwh"], b.get("log_timestamp", __import__("datetime").datetime.now())
    ), fetch="none")
    if err: return error(err)
    return success({"log_id": data["lastrowid"]}, "Production logged", 201)

# ── Energy Consumption Logs ─────────────────────────────
# GET /api/meters/<id>/consumption?limit=50
@meters_bp.route("/<int:mid>/consumption", methods=["GET"])
def get_consumption(mid):
    limit = int(request.args.get("limit", 50))
    sql = """SELECT ecl.*, ts.slot_name
             FROM energy_consumption_logs ecl
             LEFT JOIN time_slots ts ON ts.slot_id = ecl.slot_id
             WHERE ecl.meter_id=%s
             ORDER BY ecl.log_timestamp DESC LIMIT %s"""
    data, err = query(sql, (mid, limit))
    if err: return error(err)
    return success(data)

# POST /api/meters/<id>/consumption
@meters_bp.route("/<int:mid>/consumption", methods=["POST"])
def log_consumption(mid):
    b = request.get_json()
    sql = """INSERT INTO energy_consumption_logs
             (meter_id, slot_id, units_consumed_kwh, log_timestamp)
             VALUES (%s,%s,%s,%s)"""
    data, err = query(sql, (
        mid, b.get("slot_id"),
        b["units_consumed_kwh"],
        b.get("log_timestamp", __import__("datetime").datetime.now())
    ), fetch="none")
    if err: return error(err)
    return success({"log_id": data["lastrowid"]}, "Consumption logged", 201)
