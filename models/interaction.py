# models/interaction.py
import uuid
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from extensions import db

class Interaction(db.Model):
    __tablename__ = "interactions"
    __table_args__ = {"schema": "public"}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    client_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("public.clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Campos exatamente como no DDL
    type = db.Column(db.String(255), nullable=False)
    observation = db.Column(db.Text)
    from_status = db.Column(db.String(255))
    to_status = db.Column(db.String(255))

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Interaction id={self.id} type={self.type} client_id={self.client_id}>"
