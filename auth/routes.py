# auth/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import NoResultFound
from extensions import db, bcrypt
from models.user import User

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email e senha são obrigatórios."}), 400

    try:
        user = db.session.query(User).filter(User.email == email).one()
    except NoResultFound:
        return jsonify({"error": "Credenciais inválidas."}), 401
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    if not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Credenciais inválidas."}), 401

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"token": token}), 200


@bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    uid = get_jwt_identity()
    try:
        user = db.session.query(User).filter_by(id=uid).one()
    except Exception:
        return jsonify({"error": "Usuário não encontrado."}), 404

    return jsonify({
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role
    }), 200
