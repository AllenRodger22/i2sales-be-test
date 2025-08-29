from __future__ import annotations

from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_
import uuid

from extensions import db
from models.client import Client
from utils.supabase_jwt import auth_required
from utils.responses import bad_request, ok


bp = Blueprint("clients_v2", __name__)


def _camel_client(c: Client) -> dict:
    return {
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


@bp.get("/clients")
@auth_required
def list_clients():
    owner_id = g.user_id
    if not owner_id:
        return bad_request("Invalid token: missing sub")

    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = min(100, max(1, int(request.args.get("pageSize", 20))))
    except Exception:
        page, page_size = 1, 20

    qry = Client.query.filter(Client.owner_id == uuid.UUID(str(owner_id)))
    if q:
        ilike = f"%{q}%"
        qry = qry.filter(
            or_(
                Client.name.ilike(ilike),
                Client.phone.ilike(ilike),
                Client.email.ilike(ilike),
                Client.source.ilike(ilike),
            )
        )
    if status:
        qry = qry.filter(Client.status == status)

    qry = qry.order_by(Client.updated_at.desc().nullslast(), Client.created_at.desc().nullslast())
    items = [
        _camel_client(c)
        for c in qry.offset((page - 1) * page_size).limit(page_size).all()
    ]
    return ok({"items": items, "page": page, "pageSize": page_size})


@bp.post("/clients")
@auth_required
def create_client():
    owner_id = g.user_id
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name or not phone:
        return bad_request("name e phone são obrigatórios")

    c = Client(
        id=uuid.uuid4(),
        name=name,
        phone=phone,
        email=(data.get("email") or None),
        source=(data.get("source") or "manual"),
        status=(data.get("status") or "Primeiro Atendimento"),
        observations=(data.get("observations") or None),
        product=(data.get("product") or None),
        property_value=(data.get("propertyValue") or None),
        follow_up_state=(data.get("followUpState") or "Sem Follow Up"),
        owner_id=uuid.UUID(str(owner_id)),
    )

    db.session.add(c)
    db.session.commit()
    return jsonify(_camel_client(c)), 201

