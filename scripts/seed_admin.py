# scripts/seed_admin.py
import uuid
from extensions import db, bcrypt
from models.user import User

ADMIN_NAME = "Admin"
ADMIN_EMAIL = "admin@x.com"       # igual ao teste
ADMIN_PASSWORD = "1234567890"     # igual ao teste
ADMIN_ROLE = "ADMIN"

def run():
    user = User.query.filter_by(email=ADMIN_EMAIL).first()
    pwd_hash = bcrypt.generate_password_hash(ADMIN_PASSWORD).decode("utf-8")
    if user:
        user.name = ADMIN_NAME
        user.password_hash = pwd_hash
        user.role = ADMIN_ROLE
    else:
        user = User(
            id=uuid.uuid4(),
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            password_hash=pwd_hash,
            role=ADMIN_ROLE
        )
        db.session.add(user)
    db.session.commit()
    print(f"Seeded: {ADMIN_EMAIL} / {ADMIN_PASSWORD} ({ADMIN_ROLE})")
