import uuid
from extensions import db, bcrypt
from models.user import User

PASSWORD = "1234567890"  # mesma senha para todos os seeds

USERS = [
    {"name": "Admin",   "email": "admin@x.com",   "role": "ADMIN"},
    {"name": "Manager", "email": "manager@x.com", "role": "MANAGER"},
    {"name": "Broker",  "email": "broker@x.com",  "role": "BROKER"},
]


def _upsert_user(name: str, email: str, role: str):
    user = User.query.filter_by(email=email).first()
    pwd_hash = bcrypt.generate_password_hash(PASSWORD).decode("utf-8")
    if user:
        user.name = name
        user.password_hash = pwd_hash
        user.role = role
    else:
        user = User(
            id=uuid.uuid4(),
            name=name,
            email=email,
            password_hash=pwd_hash,
            role=role,
        )
        db.session.add(user)
    return user


def run():
    created = []
    for u in USERS:
        _upsert_user(u["name"], u["email"], u["role"])
        created.append(f"{u['email']} ({u['role']})")
    db.session.commit()
    print("Seeded users:")
    for entry in created:
        print(f" - {entry} / {PASSWORD}")
