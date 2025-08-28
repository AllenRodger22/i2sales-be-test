# app.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 1) Carregar o .env ANTES de importar qualquer coisa que dependa de variáveis
ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

from flask import Flask, jsonify
from config import Config
from extensions import db, jwt, init_cors, bcrypt

import os
from flask import Flask, jsonify
from config import Config
from extensions import db, jwt, init_cors, bcrypt
# app.py (topo MESMO)
from pathlib import Path
from dotenv import load_dotenv
ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

from config import Config  

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    init_cors(app)

    # Blueprints
    from auth.routes import bp as auth_bp
    from analytics.routes import bp as analytics_bp  # já deve existir
    from clients.routes import bp as clients_bp      # já deve existir
    from interactions.routes import bp as inter_bp   # já deve existir
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")
    app.register_blueprint(clients_bp, url_prefix="/api/v1/clients")
    app.register_blueprint(inter_bp, url_prefix="/api/v1/interactions")

    # Health
    @app.get("/api/v1/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # seed opcional (somente em DEV/TEST)
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
        db.create_all()
        # seed admin automático em dev/test
        try:
            from scripts.seed_admin import run as seed_admin_run
            seed_admin_run()
        except Exception as e:
            print("Seed admin skip:", e)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
