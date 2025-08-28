# utils/casing.py
"""
Helpers para conversão entre snake_case (Python/DB) e camelCase (JSON da API).
Uso típico:
 - dict_keys_to_camel(data)   -> resposta HTTP
 - dict_keys_to_snake(data)   -> payload recebido do cliente (se quiser normalizar)
"""

import re
from typing import Any, Dict, List, Union

JSONType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

_first_cap_re = re.compile(r"(.)([A-Z][a-z]+)")
_all_cap_re = re.compile(r"([a-z0-9])([A-Z])")

def snake_to_camel(s: str) -> str:
    if not s:
        return s
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() or "_" for p in parts[1:])

def camel_to_snake(s: str) -> str:
    if not s:
        return s
    s = _first_cap_re.sub(r"\1_\2", s)
    return _all_cap_re.sub(r"\1_\2", s).lower()

def dict_keys_to_camel(data: JSONType) -> JSONType:
    if isinstance(data, list):
        return [dict_keys_to_camel(i) for i in data]
    if isinstance(data, dict):
        return {snake_to_camel(k): dict_keys_to_camel(v) for k, v in data.items()}
    return data

def dict_keys_to_snake(data: JSONType) -> JSONType:
    if isinstance(data, list):
        return [dict_keys_to_snake(i) for i in data]
    if isinstance(data, dict):
        return {camel_to_snake(k): dict_keys_to_snake(v) for k, v in data.items()}
    return data

def sa_model_to_dict(instance, *, camel: bool = True, include=None, exclude=None) -> Dict[str, Any]:
    """
    Converte uma instância SQLAlchemy em dict simples (apenas colunas).
    - camel=True: converte chaves para camelCase.
    - include/exclude: coleções de nomes de colunas (snake_case) para filtrar.
    """
    if instance is None:
        return {}
    cols = getattr(instance, "__table__").columns
    raw = {}
    for c in cols:
        name = c.name
        if include and name not in include:
            continue
        if exclude and name in exclude:
            continue
        val = getattr(instance, name)
        # numerics do Postgres (Decimal) → float seguro p/ JSON (se não nulo)
        try:
            from decimal import Decimal
            if isinstance(val, Decimal):
                val = float(val)
        except Exception:
            pass
        raw[name] = val
    return dict_keys_to_camel(raw) if camel else raw
