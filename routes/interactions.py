from __future__ import annotations

from flask import Blueprint, request, jsonify, g
import uuid

from extensions import db
from models.client import Client
from models.interaction import Interaction
from utils.supabase_jwt import auth_required
from utils.responses import bad_request, not_found, ok, forbidden


bp = Blueprint("interactions_v2", __name__)


def _ensure_owner(client: Client, user_id: str):
    if str(client.owner_id) != str(user_id):
        return forbidden("Access denied: client does not belong to user")
    return None


@bp.get("/interactions")
@auth_required
def list_interactions():
    client_id = request.args.get("client_id")
    if not client_id:
        return bad_request("client_id é obrigatório")
    try:
        cid = uuid.UUID(str(client_id))
    except Exception:
        return bad_request("client_id inválido")

    c = db.session.get(Client, cid)
    if not c:
        return not_found("Client")
    r = _ensure_owner(c, g.user_id)
    if r:
        return r

    items = (
        db.session.query(Interaction)
        .filter(Interaction.client_id == cid)
        .order_by(Interaction.created_at.desc())
        .all()
    )
    data = [
        {
            "id": str(i.id),
            "type": i.type,
            "observation": i.observation,
            "fromStatus": i.from_status,
            "toStatus": i.to_status,
            "createdAt": i.created_at.isoformat() if i.created_at else None,
        }
        for i in items
    ]
    return ok({"items": data})

