# utils/errors.py
from flask import jsonify
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    """Registra handlers globais de erro para retornar JSON padronizado."""

    @app.errorhandler(400)
    def bad_request(_):
        return jsonify({"error": "Dados inválidos."}), 400

    @app.errorhandler(401)
    def unauthorized(_):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(_):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(409)
    def conflict(_):
        return jsonify({"error": "Conflict"}), 409

    @app.errorhandler(422)
    def unprocessable(_):
        return jsonify({"error": "Unprocessable Entity"}), 422

    @app.errorhandler(500)
    def internal(_):
        return jsonify({"error": "Internal Server Error"}), 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        # se for HTTPException (ex.: abort(404)), deixa cair no handler já definido
        if isinstance(e, HTTPException):
            return jsonify({"error": e.description}), e.code

        # loga no console para debug (não expõe stack trace no cliente)
        app.logger.exception("Unhandled Exception: %s", e)

        return jsonify({"error": "Internal Server Error"}), 500
