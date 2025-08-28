"""
Migration script: align local users.id to Supabase sub (UUID) and rewire references.

Usage:
  python -m scripts.migrate_users_to_supabase_sub --csv scripts/users_migration_example.csv

CSV format (header required):
  email,supabase_sub,name,role
  - email (required)
  - supabase_sub (required, UUID from Supabase auth user id)
  - name (optional; fallback to existing user name)
  - role (optional; fallback to existing user role or default 'BROKER')

Behavior per row:
  - If a user with email does not exist → create with id=supabase_sub
  - If exists and id==supabase_sub → no-op
  - If exists and id!=supabase_sub →
      * Temporarily rename old user's email to free unique constraint
      * Insert new user with id=supabase_sub preserving email/name/role
      * Reassign interactions.user_id and clients.owner_id to supabase_sub
      * Delete old user

This avoids PK updates (FKs lack ON UPDATE CASCADE) and preserves referential integrity.
"""

from __future__ import annotations

import argparse
import csv
import uuid
from typing import Optional

from flask import current_app

from app import create_app  # type: ignore
from extensions import db, bcrypt
from models.user import User
from models.interaction import Interaction
from models.client import Client


def _parse_uuid(val: str) -> uuid.UUID:
    return uuid.UUID(str(val))


def migrate_row(email: str, sup_sub: uuid.UUID, name: Optional[str], role: Optional[str]) -> str:
    email = email.strip().lower()
    role = role or "BROKER"

    user = db.session.query(User).filter(User.email == email).one_or_none()
    if not user:
        # create fresh user with id=sup_sub
        dummy_pw_hash = bcrypt.generate_password_hash("supabase-external").decode("utf-8")
        new_user = User(id=sup_sub, name=name or email.split("@")[0], email=email, password_hash=dummy_pw_hash, role=role)
        db.session.add(new_user)
        db.session.flush()
        return f"created:{email}"

    # already aligned
    if str(user.id) == str(sup_sub):
        return f"noop:{email}"

    # rename old email to free unique index
    legacy_email = f"{email}.legacy-{str(user.id)[:8]}"
    user.email = legacy_email
    db.session.flush()

    # create new user with correct id
    new_user = User(id=sup_sub, name=(name or user.name), email=email, password_hash=user.password_hash, role=(role or user.role))
    db.session.add(new_user)
    db.session.flush()

    # rewire references
    db.session.query(Interaction).filter(Interaction.user_id == user.id).update({Interaction.user_id: sup_sub})
    db.session.query(Client).filter(Client.owner_id == user.id).update({Client.owner_id: sup_sub})
    db.session.flush()

    # delete old user
    db.session.delete(user)
    return f"migrated:{email}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV mapping file")
    args = parser.parse_args()

    results = {"created": 0, "migrated": 0, "noop": 0, "errors": 0}

    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"email", "supabase_sub"}
        if not required.issubset(set(h.strip().lower() for h in reader.fieldnames or [])):
            raise RuntimeError("CSV must include headers: email,supabase_sub[,name,role]")

        for row in reader:
            email = (row.get("email") or "").strip().lower()
            sup = (row.get("supabase_sub") or "").strip()
            name = (row.get("name") or None)
            role = (row.get("role") or None)
            if not email or not sup:
                print(f"skip: missing email/sub in row: {row}")
                continue

            try:
                sup_uuid = _parse_uuid(sup)
            except Exception:
                print(f"error: invalid UUID for {email}: {sup}")
                results["errors"] += 1
                continue

            try:
                with db.session.begin():
                    status = migrate_row(email, sup_uuid, name, role)
                tag = status.split(":", 1)[0]
                results[tag] += 1
                print(status)
            except Exception as e:
                db.session.rollback()
                results["errors"] += 1
                print(f"error:{email}:{e}")

    print("Summary:", results)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        main()
