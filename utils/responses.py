from __future__ import annotations

from flask import jsonify


def ok(data, status: int = 200):
    return jsonify(data), status


def bad_request(msg: str, detail: str | None = None):
    payload = {"error": msg}
    if detail:
        payload["detail"] = detail
    return jsonify(payload), 400


def unauthorized(detail: str | None = None):
    payload = {"error": "Unauthorized"}
    if detail:
        payload["detail"] = detail
    return jsonify(payload), 401


def forbidden(detail: str | None = None):
    payload = {"error": "Forbidden"}
    if detail:
        payload["detail"] = detail
    return jsonify(payload), 403


def not_found(resource: str = "Resource"):
    return jsonify({"error": f"{resource} not found"}), 404


def server_error(detail: str | None = None):
    payload = {"error": "Internal Server Error"}
    if detail:
        payload["detail"] = detail
    return jsonify(payload), 500

