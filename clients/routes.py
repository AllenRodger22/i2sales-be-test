# clients/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import uuid

from extensions import db
from models.client import Client

bp = Blueprint("clients", __name__, url_prefix="/clients")

VALID_STATUS = {
    "Primeiro Atendimento",
    "Ativo",
    "Atrasado",
    "Concluído",
    "Cancelado",
    "Perdido",  # trocou 'Ignorado' por 'Perdido', conforme sua regra
}
VALID_FU = {"Sem Follow Up", "Ativo", "Atrasado", "Concluído", "Cancelado", "Perdido"}

def _now():
    return datetime.now(timezone.utc)

def _to_decimal(val):
    if val is None:
        return None
    # SEMPRE converter a partir de string pra evitar binário de float
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None

def _camel_client(c: Client, with_interactions=False):
    base = {
        "id": str(c.id),
        "name": c.name,
        "phone": c.phone,
        "source": c.source,
        "status": c.status,
        "email": c.email,
        "observations": c.observations,
        "product": c.product,
        "propertyValue": float(c.property_value) if c.property_value is not None else None,
        "followUpState": c.follow_up_state,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
        "updatedAt": c.updated_at.isoformat() if c.updated_at else None,
    }
    if with_interactions:
        base["interactions"] = [
            {
                "id": str(i.id),
                "type": i.type,
                "note": i.note,
                "statusChange": i.status_change,
                "createdAt": i.created_at.isoformat() if i.created_at else None,
            }
            for i in c.interactions
        ]
    return base

@bp.route("", methods=["POST"])
@jwt_required()
def create_client():
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()

    # Padrões do teste
    status = payload.get("status") or "Primeiro Atendimento"
    follow_up = payload.get("followUpState") or "Sem Follow Up"

    if status not in VALID_STATUS:
        return jsonify({"error": f"status inválido: {status}"}), 400
    if follow_up not in VALID_FU:
        return jsonify({"error": f"followUpState inválido: {follow_up}"}), 400
    if not name or not phone:
        return jsonify({"error": "name e phone são obrigatórios"}), 400

    client = Client(
        id=uuid.uuid4(),
        name=name,
        phone=phone,
        source=payload.get("source"),
        status=status,
        email=payload.get("email"),
        observations=payload.get("observations"),
        product=payload.get("product"),
        property_value=_to_decimal(payload.get("propertyValue")),
        follow_up_state=follow_up,
        created_at=_now(),
        updated_at=_now(),
    )

    try:
        db.session.add(client)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Violação de integridade", "detail": str(e.orig)}), 400
    except Exception as e:
        db.session.rollback()
        # durante os testes, é melhor retornar a causa:
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    return jsonify(_camel_client(client)), 201
