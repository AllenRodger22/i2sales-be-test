# interactions/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import uuid

from extensions import db
from models.client import Client
from models.interaction import Interaction

# Blueprint sem prefixo interno; app.py registra em /api/v1/interactions
bp = Blueprint("interactions", __name__)

def _parse_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(str(value))

def _error(msg, code=400):
    return jsonify({"error": msg}), code

@bp.post("")
@jwt_required()
def create_interaction():
    j = get_jwt()
    data = request.get_json(silent=True) or {}

    client_id = data.get("clientId")
    type_ = data.get("type")
    observation = data.get("observation")
    explicit_next = data.get("explicitNext")

    if not client_id:
        return _error("Dados inválidos.", 400)

    # Se vier só observação sem type, trata como NOTE
    if not type_ and observation:
        type_ = "NOTE"
    if type_ == "OBSERVATION":
        type_ = "NOTE"
    if not type_:
        return _error("Dados inválidos.", 400)

    c = Client.query.get(client_id)
    if not c:
        return _error("Not Found", 404)

    # sub do JWT deve ser UUID (seed já emite assim)
    try:
        user_uuid = _parse_uuid(j.get("sub"))
    except Exception:
        return _error("Token inválido.", 401)

    current_status = c.status or "Primeiro Atendimento"
    target_status = explicit_next if (type_ == "STATUS_CHANGE" and explicit_next) else current_status

    try:
        # Não setamos created_at aqui (modelo já tem default=datetime.utcnow)
        i = Interaction(
            id=uuid.uuid4(),
            client_id=c.id,
            user_id=user_uuid,
            type=type_,
            observation=observation,
            from_status=current_status,
            to_status=target_status,
        )
        db.session.add(i)

        # Efeitos colaterais por tipo
        if type_ == "STATUS_CHANGE" and explicit_next:
            c.status = explicit_next
        elif type_ == "FOLLOW_UP_SCHEDULED":
            c.follow_up_state = "Ativo"
        elif type_ in {
            "FOLLOW_UP_DONE",
            "FOLLOW_UP_CANCELED",
            "FOLLOW_UP_CANCELLED",
            "FOLLOW_UP_LOST",
            "FOLLOW_UP_CLOSED",
        }:
            c.follow_up_state = "Sem Follow Up"
        # NOTE -> sem efeito no cliente

        db.session.commit()
        return jsonify({"message": "Interação criada com sucesso."}), 201

    except Exception:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return _error("Internal Server Error", 500)
