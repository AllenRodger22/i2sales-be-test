# app.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env antes de importar config/extensões
ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

from flask import Flask, jsonify, request
from sqlalchemy import text

# Suporte a execução como script (python app.py) e como módulo (flask --app app)
try:
    from config import Config
    from extensions import db, init_cors, bcrypt
except ModuleNotFoundError:
    from .config import Config  # type: ignore
    from .extensions import db, init_cors, bcrypt  # type: ignore


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    init_cors(app)

    # Garantir resposta ao preflight (OPTIONS) globalmente
    @app.before_request
    def _handle_cors_preflight():
        if request.method == "OPTIONS":
            return "", 204

    # Blueprints
    from auth.routes import bp as auth_bp
    from analytics.routes import bp as analytics_bp
    from clients.routes import bp as clients_bp
    from interactions.routes import bp as inter_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")
    app.register_blueprint(clients_bp, url_prefix="/api/v1/clients")
    app.register_blueprint(inter_bp, url_prefix="/api/v1/interactions")

    # Health
    @app.get("/api/v1/health")
    def health():
        # Verifica conectividade com o banco
        try:
            db.session.execute(text("SELECT 1"))
            db_ok = True
            detail = None
        except Exception as e:
            db_ok = False
            detail = str(e)

        payload = {
            "status": "ok" if db_ok else "error",
            "db": "ok" if db_ok else "error",
        }
        if detail and not db_ok:
            payload["detail"] = detail

        return jsonify(payload), (200 if db_ok else 500)

    # seed opcional (DEV/TEST)
    @app.cli.command("seed_admin")
    def seed_admin_cmd():
        with app.app_context():
            from scripts.seed_admin import run as seed_admin_run
            seed_admin_run()

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        # opcional: criar tabelas se não usa alembic
        try:
            db.create_all()
        except Exception as e:
            print("DB create_all skipped or failed:", e)
        # seed admin automático em dev/test
        try:
            from scripts.seed_admin import run as seed_admin_run
            seed_admin_run()
        except Exception as e:
            print("Seed admin skip:", e)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
