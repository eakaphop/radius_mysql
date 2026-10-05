"""CLI to bootstrap the first admin account, or reset an existing one's password.

There is no self-registration or "forgot password" flow in this app (admins
are managed by admins) — this is the only way to recover a lost admin
password. Run after `alembic upgrade head`:

    python -m app.cli.create_admin --username admin --role admin
    python -m app.cli.create_admin --username admin --reset-password
"""

import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models.admin_user import AdminRole, AppAdminUser
from app.db.session import async_session_factory


async def create_admin(username: str, password: str, role: AdminRole) -> None:
    async with async_session_factory() as db, db.begin():
        existing = await db.execute(select(AppAdminUser).where(AppAdminUser.username == username))
        if existing.scalar_one_or_none() is not None:
            raise SystemExit(
                f"Admin user '{username}' already exists — use --reset-password to change it"
            )

        db.add(
            AppAdminUser(
                username=username,
                password_hash=hash_password(password),
                role=role,
                is_active=True,
            )
        )
    print(f"Created {role.value} user '{username}'")


async def reset_password(username: str, password: str) -> None:
    async with async_session_factory() as db, db.begin():
        result = await db.execute(select(AppAdminUser).where(AppAdminUser.username == username))
        admin = result.scalar_one_or_none()
        if admin is None:
            raise SystemExit(f"Admin user '{username}' does not exist — omit --reset-password to create it")

        admin.password_hash = hash_password(password)
        admin.is_active = True
    print(f"Password reset for '{username}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a web app admin user, or reset its password")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", choices=["admin", "viewer"], default="admin")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset the password of an existing admin instead of creating a new one",
    )
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")

    if args.reset_password:
        asyncio.run(reset_password(args.username, password))
    else:
        asyncio.run(create_admin(args.username, password, AdminRole(args.role)))


if __name__ == "__main__":
    main()
