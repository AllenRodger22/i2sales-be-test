# analytics/routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func
from extensions import db
from models.client import Client
from models.interaction import Interaction

bp = Blueprint("analytics", __name__)

def _error(msg, code): return jsonify({"error": msg}), code

@bp.get("/broker-kpis")
@jwt_required()
def broker_kpis():
    j = get_jwt()
    qry = Client.query
    if j.get("role") == "BROKER":
        qry = qry.filter(Client.owner_id == j.get("sub"))

    total = qry.count()
    primeiro = qry.filter(Client.status == "Primeiro Atendimento").count()
    em_tratativa = qry.filter(Client.status == "Em Tratativa").count()
    atrasado = qry.filter(Client.follow_up_state == "Atrasado").count()

    return jsonify({
        "followUpAtrasado": atrasado,
        "leadsEmTratativa": em_tratativa,
        "leadsPrimeiroAtendimento": primeiro,
        "totalLeads": total
    }), 200

@bp.get("/productivity")
@jwt_required()
def productivity():
    j = get_jwt()
    start = request.args.get("startDate")
    end = request.args.get("endDate")
    broker_id = request.args.get("brokerId")

    if not start or not end:
        return _error("Dados inválidos.", 400)
    if j.get("role") == "BROKER":
        broker_id = j.get("sub")

    q = db.session.query(
        func.date_trunc('day', Interaction.created_at).label("dia"),
        func.count(Interaction.id)
    ).group_by(func.date_trunc('day', Interaction.created_at))\
     .filter(Interaction.created_at >= start)\
     .filter(Interaction.created_at < f"{end} 23:59:59")

    if broker_id:
        q = q.filter(Interaction.user_id == broker_id)

    series = [{"date": r.dia.date().isoformat(), "count": r[1]} for r in q.order_by("dia").all()]
    return jsonify({"series": series}), 200

@bp.get("/funnel")
@jwt_required()
def funnel():
    j = get_jwt()
    start = request.args.get("startDate")
    end = request.args.get("endDate")
    broker_id = request.args.get("brokerId")

    if not start or not end:
        return _error("Dados inválidos.", 400)
    if j.get("role") == "BROKER":
        broker_id = j.get("sub")

    qry = Client.query.filter(Client.created_at >= start).filter(Client.created_at < f"{end} 23:59:59")
    if broker_id:
        qry = qry.filter(Client.owner_id == broker_id)

    stages = ["Primeiro Atendimento", "Em Tratativa", "Proposta", "Fechado"]
    counts = {s: qry.filter(Client.status == s).count() for s in stages}
    return jsonify({"stages": counts}), 200
