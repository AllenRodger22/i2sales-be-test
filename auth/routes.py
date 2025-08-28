# auth/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import NoResultFound, IntegrityError
from extensions import db, bcrypt
from models.user import User
from .supabase_auth import verify_supabase_jwt, SupabaseAuthError

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


@bp.route("/supabase/login", methods=["POST"])
def supabase_login():
    """Exchanges a Supabase access token for this API's JWT and syncs the local user.

    Frontend should call with Authorization: Bearer <supabase_access_token>
    or send {"access_token": "..."} in the JSON body.
    """
    data = request.get_json(silent=True) or {}
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    token = token or data.get("access_token") or data.get("token") or ""
    if not token:
        return jsonify({"error": "Supabase access token não informado."}), 400

    try:
        claims = verify_supabase_jwt(token)
    except SupabaseAuthError as e:
        return jsonify({"error": "Token inválido.", "detail": str(e)}), 401

    email = (claims.get("email") or
             (claims.get("user_metadata") or {}).get("email") or
             (claims.get("app_metadata") or {}).get("email") or
             "").strip().lower()
    if not email:
        return jsonify({"error": "Token sem email válido."}), 400

    # Name best-effort from token metadata
    name = (
        (claims.get("user_metadata") or {}).get("name") or
        (claims.get("user_metadata") or {}).get("full_name") or
        claims.get("name") or
        email.split("@")[0]
    )

    try:
        user = db.session.query(User).filter(User.email == email).one_or_none()
        if not user:
            # Create local user with a dummy password hash since Supabase manages credentials
            dummy_pw_hash = bcrypt.generate_password_hash("supabase-external").decode("utf-8")
            user = User(name=name, email=email, password_hash=dummy_pw_hash, role="BROKER")
            db.session.add(user)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    api_token = create_access_token(identity=str(user.id), additional_claims={
        "role": user.role,
        # Optional: include supabase subject for traceability
        "supabase_sub": claims.get("sub"),
    })

    return jsonify({
        "token": api_token,
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    }), 200
