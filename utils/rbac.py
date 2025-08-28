# utils/rbac.py
"""
Helpers de RBAC para i2Sales.
Regras:
- BROKER: só enxerga/atua em registros com owner_id = sub.
- MANAGER/ADMIN: veem tudo.
- ADMIN: pode deletar globalmente.
"""

from typing import Optional
from flask import jsonify
from flask_jwt_extended import get_jwt
from functools import wraps

ROLES = {"BROKER", "MANAGER", "ADMIN"}

def current_sub_and_role():
    j = get_jwt()
    return j.get("sub"), j.get("role")

def is_broker(role: Optional[str]) -> bool:
    return role == "BROKER"

def is_manager(role: Optional[str]) -> bool:
    return role == "MANAGER"

def is_admin(role: Optional[str]) -> bool:
    return role == "ADMIN"

def can_view_record(role: str, owner_id: str, user_id: str) -> bool:
    """BROKER só pode ver o que ele é owner; MANAGER/ADMIN podem tudo."""
    if is_broker(role):
        return str(owner_id) == str(user_id)
    return True

def require_roles(*allowed_roles):
    """
    Decorator para bloquear rota se o papel do JWT não estiver em allowed_roles.
    Uso:
      @jwt_required()
      @require_roles("ADMIN")           # apenas admin
      def delete(...):
          ...
    """
    allowed = set(allowed_roles)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            _, role = current_sub_and_role()
            if role not in allowed:
                return jsonify({"error": "Forbidden"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def ensure_client_access_or_403(client_owner_id) -> Optional[tuple]:
    """
    Verifica RBAC para um recurso de cliente já carregado:
    - Se BROKER e não é owner -> 403
    - Caso contrário -> None (ok)
    Retorna um par (response, status) em caso de bloqueio; ou None se permitido.
    """
    sub, role = current_sub_and_role()
    if is_broker(role) and str(client_owner_id) != str(sub):
        return jsonify({"error": "Forbidden"}), 403
    return None
