# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()

def init_cors(app):
    # Allowed origins from config or sane defaults
    allowed_origins = app.config.get(
        "CORS_ORIGINS",
        ["http://localhost:5173", "https://SEU-PROJETO.vercel.app"],
    )

    # Apply CORS globally before any auth/route middleware
    CORS(
        app,
        resources={r"/api/v1/*": {"origins": allowed_origins}},
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=False,
    )
