from flask import Blueprint, request
from models.db import query, success, error

zones_bp = Blueprint("zones", __name__)

# ── Grid Zones ──────────────────────────────────────────
@zones_bp.route("/", methods=["GET"])
def get_zones():
    sql = """SELECT gz.*, r.region_name, r.state, r.country
             FROM grid_zones gz JOIN regions r ON r.region_id = gz.region_id"""
    data, err = query(sql)
    if err: return error(err)
    return success(data)

@zones_bp.route("/<int:zid>", methods=["GET"])
def get_zone(zid):
    sql = """SELECT gz.*, r.region_name, r.state
             FROM grid_zones gz JOIN regions r ON r.region_id = gz.region_id
             WHERE gz.zone_id=%s"""
    data, err = query(sql, (zid,), fetch="one")
    if err: return error(err)
    if not data: return error("Zone not found", 404)
    return success(data)

# ── Regions ─────────────────────────────────────────────
@zones_bp.route("/regions", methods=["GET"])
def get_regions():
    data, err = query("SELECT * FROM regions")
    if err: return error(err)
    return success(data)

# ── Time Slots ───────────────────────────────────────────
@zones_bp.route("/slots", methods=["GET"])
def get_slots():
    data, err = query("SELECT * FROM time_slots ORDER BY start_time")
    if err: return error(err)
    return success(data)

# ── Renewable Sources ────────────────────────────────────
@zones_bp.route("/sources", methods=["GET"])
def get_sources():
    data, err = query("SELECT * FROM renewable_sources")
    if err: return error(err)
    return success(data)

# ── Roles ────────────────────────────────────────────────
@zones_bp.route("/roles", methods=["GET"])
def get_roles():
    data, err = query("SELECT * FROM roles")
    if err: return error(err)
    return success(data)
