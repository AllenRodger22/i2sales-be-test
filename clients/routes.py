# clients/routes.py
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import uuid
import csv
import io

from extensions import db
from models.client import Client
from models.interaction import Interaction
from utils.rbac import ensure_client_access_or_403, require_roles

# Blueprint sem prefixo interno; app.py define /api/v1/clients
bp = Blueprint("clients", __name__)

# Conjuntos de valores aceitos (UTF-8)
VALID_STATUS = {
    "Primeiro Atendimento",
    "Em Tratativa",
    "Proposta",
    "Fechado",
    "Ativo",
    "Atrasado",
    "Concluído",
    "Cancelado",
    "Perdido",
}
VALID_FU = {"Sem Follow Up", "Ativo", "Atrasado", "Concluído", "Cancelado", "Perdido"}


def _now():
    return datetime.now(timezone.utc)


def _to_decimal(val):
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _camel_interaction(i: Interaction) -> dict:
    return {
        "id": str(i.id),
        "type": i.type,
        "observation": i.observation,
        "fromStatus": i.from_status,
        "toStatus": i.to_status,
        "createdAt": i.created_at.isoformat() if i.created_at else None,
    }


def _camel_client(c: Client, with_interactions=False) -> dict:
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
        interactions = (
            Interaction.query.filter_by(client_id=c.id)
            .order_by(Interaction.created_at.desc())
            .all()
        )
        base["interactions"] = [_camel_interaction(i) for i in interactions]
    return base


@bp.post("")
@jwt_required()
def create_client():
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()

    status = payload.get("status") or "Primeiro Atendimento"
    follow_up = payload.get("followUpState") or "Sem Follow Up"

    if status not in VALID_STATUS:
        return jsonify({"error": f"status inválido: {status}"}), 400
    if follow_up not in VALID_FU:
        return jsonify({"error": f"followUpState inválido: {follow_up}"}), 400
    if not name or not phone:
        return jsonify({"error": "name e phone são obrigatórios"}), 400

    j = get_jwt()
    owner_uuid = j.get("sub")

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
        owner_id=owner_uuid,
        created_at=_now(),
        updated_at=_now(),
    )

    try:
        db.session.add(client)
        # registra interação de criação
        created_inter = Interaction(
            id=uuid.uuid4(),
            client_id=client.id,
            user_id=owner_uuid,
            type="CLIENT_CREATED",
            observation="Cliente criado",
            from_status=None,
            to_status=status,
        )
        db.session.add(created_inter)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Violação de integridade", "detail": str(e.orig)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    return jsonify(_camel_client(client)), 201


@bp.get("")
@jwt_required()
def list_clients():
    j = get_jwt()
    q = (request.args.get("q") or "").strip()
    qry = Client.query
    # RBAC: brokers só veem seus registros
    if j.get("role") == "BROKER":
        qry = qry.filter(Client.owner_id == j.get("sub"))
    if q:
        ilike = f"%{q}%"
        qry = qry.filter(
            (Client.name.ilike(ilike))
            | (Client.phone.ilike(ilike))
            | (Client.email.ilike(ilike))
            | (Client.source.ilike(ilike))
        )
    # ordem recente primeiro
    qry = qry.order_by(Client.updated_at.desc().nullslast(), Client.created_at.desc().nullslast())
    items = [_camel_client(c) for c in qry.limit(200).all()]
    return jsonify(items), 200


@bp.get("/<uuid:client_id>")
@jwt_required()
def get_client(client_id: uuid.UUID):
    c = Client.query.get(client_id)
    if not c:
        return jsonify({"error": "Not Found"}), 404
    r = ensure_client_access_or_403(c.owner_id)
    if r:
        return r
    return jsonify(_camel_client(c, with_interactions=True)), 200


@bp.put("/<uuid:client_id>")
@jwt_required()
def update_client(client_id: uuid.UUID):
    c = Client.query.get(client_id)
    if not c:
        return jsonify({"error": "Not Found"}), 404
    r = ensure_client_access_or_403(c.owner_id)
    if r:
        return r

    data = request.get_json(silent=True) or {}
    # campos permitidos
    if "name" in data: c.name = (data.get("name") or "").strip() or c.name
    if "phone" in data: c.phone = (data.get("phone") or "").strip() or c.phone
    if "email" in data: c.email = (data.get("email") or None)
    if "observations" in data: c.observations = data.get("observations")
    if "product" in data: c.product = data.get("product")
    if "propertyValue" in data: c.property_value = _to_decimal(data.get("propertyValue"))
    if "status" in data:
        new_status = data.get("status")
        if new_status not in VALID_STATUS:
            return jsonify({"error": f"status inválido: {new_status}"}), 400
        c.status = new_status
    if "followUpState" in data:
        new_fu = data.get("followUpState")
        if new_fu not in VALID_FU:
            return jsonify({"error": f"followUpState inválido: {new_fu}"}), 400
        c.follow_up_state = new_fu

    c.updated_at = _now()
    db.session.commit()
    return jsonify(_camel_client(c)), 200


@bp.delete("/<uuid:client_id>")
@jwt_required()
@require_roles("ADMIN")
def delete_client(client_id: uuid.UUID):
    c = Client.query.get(client_id)
    if not c:
        return jsonify({"error": "Not Found"}), 404
    db.session.delete(c)
    db.session.commit()
    return Response(status=204)


@bp.get("/export")
@jwt_required()
def export_clients():
    j = get_jwt()
    qry = Client.query
    if j.get("role") == "BROKER":
        qry = qry.filter(Client.owner_id == j.get("sub"))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "name",
        "phone",
        "email",
        "source",
        "status",
        "followUpState",
        "product",
        "propertyValue",
        "createdAt",
        "updatedAt",
    ])
    for c in qry.order_by(Client.created_at.desc().nullslast()).all():
        writer.writerow([
            str(c.id),
            c.name or "",
            c.phone or "",
            c.email or "",
            c.source or "",
            c.status or "",
            c.follow_up_state or "",
            c.product or "",
            f"{c.property_value}" if c.property_value is not None else "",
            c.created_at.isoformat() if c.created_at else "",
            c.updated_at.isoformat() if c.updated_at else "",
        ])
    csv_data = output.getvalue()
    return Response(csv_data, mimetype="text/csv; charset=utf-8"), 200

