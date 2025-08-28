# models/client.py
import uuid
from sqlalchemy import CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
from extensions import db

class Client(db.Model):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint(
            "follow_up_state IN ('Ativo','Concluido','Cancelado','Atrasado','Sem Follow Up')",
            name="clients_follow_up_state_check",
        ),
        {"schema": "public"},
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)
    email = db.Column(db.String)
    source = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)

    # DDL NÃO cria FK para owner_id; manter igual ao DDL (sem ForeignKey)
    owner_id = db.Column(UUID(as_uuid=True), nullable=True)

    observations = db.Column(db.Text)

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    product = db.Column(db.String(255))
    property_value = db.Column(NUMERIC(15, 2))
    follow_up_state = db.Column(db.String(20), server_default="Sem Follow Up", nullable=True)

    # relacionamento com interactions (FK está no model Interaction)
    interactions = db.relationship(
        "Interaction",
        backref="client",
        lazy="dynamic",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.name}>"
