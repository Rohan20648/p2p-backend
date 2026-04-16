from flask import Blueprint, request
from models.db import query, success, error
import hashlib

users_bp = Blueprint("users", __name__)

def sha256(s): return hashlib.sha256(s.encode()).hexdigest()

# POST /api/users/register
@users_bp.route("/register", methods=["POST"])
def register():
    b = request.get_json()
    required = ["full_name", "email", "password", "role_id"]
    for f in required:
        if not b.get(f): return error(f"{f} is required")

    # Check duplicate email
    exist, err = query("SELECT user_id FROM users WHERE email=%s", (b["email"],), fetch="one")
    if err: return error(err)
    if exist: return error("Email already registered", 409)

    sql = """INSERT INTO users (role_id, full_name, email, phone, password_hash)
             VALUES (%s, %s, %s, %s, %s)"""
    data, err = query(sql, (
        b["role_id"], b["full_name"], b["email"],
        b.get("phone"), sha256(b["password"])
    ), fetch="none")
    if err: return error(err)

    uid = data["lastrowid"]
    query("INSERT INTO user_profiles (user_id) VALUES (%s)", (uid,), fetch="none")
    return success({"user_id": uid}, "User registered", 201)

# POST /api/users/login
@users_bp.route("/login", methods=["POST"])
def login():
    b = request.get_json()
    if not b.get("email") or not b.get("password"):
        return error("email and password required")

    sql = """SELECT u.user_id, u.full_name, u.email, u.role_id, r.role_name,
                    w.balance AS wallet_balance
             FROM users u
             JOIN roles r ON r.role_id = u.role_id
             LEFT JOIN wallets w ON w.user_id = u.user_id
             WHERE u.email=%s AND u.password_hash=%s AND u.is_active=1"""
    user, err = query(sql, (b["email"], sha256(b["password"])), fetch="one")
    if err: return error(err)
    if not user: return error("Invalid credentials", 401)
    return success(user, "Login successful")

# GET /api/users/<id>
@users_bp.route("/<int:uid>", methods=["GET"])
def get_user(uid):
    sql = """SELECT u.*, r.role_name, up.kyc_verified, up.bio, up.profile_picture_url,
                    w.balance AS wallet_balance
             FROM users u
             JOIN roles r ON r.role_id = u.role_id
             LEFT JOIN user_profiles up ON up.user_id = u.user_id
             LEFT JOIN wallets w ON w.user_id = u.user_id
             WHERE u.user_id=%s"""
    data, err = query(sql, (uid,), fetch="one")
    if err: return error(err)
    if not data: return error("User not found", 404)
    data.pop("password_hash", None)
    return success(data)

# GET /api/users  (admin)
@users_bp.route("/", methods=["GET"])
def get_all():
    sql = """SELECT u.user_id, u.full_name, u.email, u.phone, u.is_active, u.created_at,
                    r.role_name, up.kyc_verified, w.balance AS wallet_balance
             FROM users u
             JOIN roles r ON r.role_id = u.role_id
             LEFT JOIN user_profiles up ON up.user_id = u.user_id
             LEFT JOIN wallets w ON w.user_id = u.user_id
             ORDER BY u.user_id DESC"""
    data, err = query(sql)
    if err: return error(err)
    return success(data)

# PUT /api/users/<id>
@users_bp.route("/<int:uid>", methods=["PUT"])
def update_user(uid):
    b = request.get_json()
    sql = "UPDATE users SET full_name=%s, phone=%s WHERE user_id=%s"
    data, err = query(sql, (b.get("full_name"), b.get("phone"), uid), fetch="none")
    if err: return error(err)
    return success(message="User updated")
