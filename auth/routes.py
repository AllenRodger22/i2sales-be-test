# auth/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import NoResultFound, IntegrityError
from extensions import db, bcrypt
from models.user import User

# Blueprint sem prefixo interno; app.py registra em /api/v1/auth
bp = Blueprint("auth", __name__)

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
    # Frontend espera token e dados básicos do usuário
    return jsonify({
        "token": token,
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    }), 200


@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or data.get("passwordHash") or ""
    # Role opcional no payload, mas forçamos BROKER por segurança
    role = "BROKER"

    if not name or not email or not password:
        return jsonify({"error": "Dados inválidos."}), 400
    if "@" not in email:
        return jsonify({"error": "Email inválido."}), 400
    if len(password) < 8:
        return jsonify({"error": "Senha deve ter no mínimo 8 caracteres."}), 400

    try:
        pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        u = User(name=name, email=email, password_hash=pw_hash, role=role)
        db.session.add(u)
        db.session.commit()
        return jsonify({
            "id": str(u.id),
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "createdAt": u.created_at.isoformat() if u.created_at else None,
        }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email já registrado."}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500


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
