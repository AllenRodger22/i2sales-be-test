# models/user.py
import uuid
from datetime import datetime
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from extensions import db

# Enum já existe no banco: public.user_role
UserRole = PgEnum(
    "BROKER", "MANAGER", "ADMIN",
    name="user_role",
    schema="public",
    native_enum=True,
    create_type=False,
)

class User(db.Model):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(UserRole, nullable=False, server_default="BROKER")

    # DDL só tem created_at (sem updated_at)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=True)

    # relacionamento reverso (não altera DDL)
    interactions = db.relationship(
        "Interaction",
        backref="user",
        lazy="dynamic",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
