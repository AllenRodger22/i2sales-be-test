import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from extensions import db


class Profile(db.Model):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "public"}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 1:1 users -> profiles
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("public.users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    phone_number = db.Column(db.String)
    address = db.Column(db.String)
    avatar_url = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    # Prefer JSONB in Postgres; fall back to JSON if not available
    # Use a non-reserved attribute name; keep DB column name as 'metadata'
    try:
        from sqlalchemy.dialects.postgresql import JSONB  # type: ignore
        metadata_json = db.Column("metadata", JSONB)
    except Exception:  # pragma: no cover - fallback for non-PG test envs
        metadata_json = db.Column("metadata", db.JSON)

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    def __repr__(self) -> str:
        return f"<Profile id={self.id} user_id={self.user_id} active={self.is_active}>"
