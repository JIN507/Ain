"""Bootstrap initial admin user for Ain News Monitor.

Usage (from backend directory, inside venv):

    python bootstrap_admin.py

This will create or reactivate the admin user:
    name:  elite
    email: elite@local
    pass:  0000
"""

from models import get_db, User, init_db
from auth_utils import hash_password


def bootstrap_admin():
    init_db()
    db = get_db()
    try:
        admin = db.query(User).filter(User.email == "elite@local").first()
        if admin:
            admin.is_active = True
            if not admin.password_hash:
                admin.password_hash = hash_password("135813581234")
            if admin.role != "ADMIN":
                admin.role = "ADMIN"
            db.commit()
            print("Admin user already exists, ensured active and role=ADMIN.")
            return

        admin = User(
            name="عبدالله الكلثمي",
            email="elite@local",
            password_hash=hash_password("135813581234"),
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("✅ Admin user created: elite@local / 0000")
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_admin()
