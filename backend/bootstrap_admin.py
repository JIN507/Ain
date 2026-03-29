"""Bootstrap initial admin user for Ain News Monitor.

Usage (from backend directory, inside venv):

    python bootstrap_admin.py

Set ADMIN_INIT_PASSWORD env var to choose a password, otherwise a random one is generated.
"""

import os
import secrets
from models import get_db, User, init_db
from auth_utils import hash_password


def bootstrap_admin():
    init_db()
    # C1 FIX: Read password from env var or generate random
    password = os.environ.get('ADMIN_INIT_PASSWORD', '').strip()
    pw_generated = False
    if not password:
        password = secrets.token_urlsafe(16)
        pw_generated = True

    db = get_db()
    try:
        admin = db.query(User).filter(User.email == "elite@local").first()
        if admin:
            admin.is_active = True
            if not admin.password_hash:
                admin.password_hash = hash_password(password)
                if pw_generated:
                    print(f"Password set to: {password}")
            if admin.role != "ADMIN":
                admin.role = "ADMIN"
            db.commit()
            print("Admin user already exists, ensured active and role=ADMIN.")
            return

        admin = User(
            name="عبدالله الكلثمي",
            email="elite@local",
            password_hash=hash_password(password),
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin user created: elite@local")
        if pw_generated:
            print(f"   Generated password: {password}")
            print("   Set ADMIN_INIT_PASSWORD env var to use a fixed password.")
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_admin()
