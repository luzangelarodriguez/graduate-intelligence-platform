from __future__ import annotations

import argparse
import os
import sys
from getpass import getpass

from api.auth import ensure_admin_user


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value not in {None, ""} else default


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap or update the initial admin user.")
    parser.add_argument("--email", default=_env("ADMIN_EMAIL"), help="Admin email address")
    parser.add_argument("--password", default="", help="Admin password; prompt if omitted")
    parser.add_argument("--full-name", default=_env("ADMIN_FULL_NAME"), help="Admin full name")
    parser.add_argument("--role", default=_env("ADMIN_ROLE", "admin"), help="Role name to assign")
    args = parser.parse_args()

    email = args.email.strip()
    full_name = args.full_name.strip() or "Platform Admin"
    password = args.password or os.getenv("ADMIN_PASSWORD") or ""
    if not password:
        password = getpass("Admin password: ")

    if not email:
        print("Missing --email or ADMIN_EMAIL", file=sys.stderr)
        return 2
    if len(password) < 8:
        print("Password must be at least 8 characters long", file=sys.stderr)
        return 2

    result = ensure_admin_user(email=email, password=password, full_name=full_name, role_name=args.role.strip() or "admin")
    print(f"Admin user ready: {result['email']} (role={result['role']}, user_id={result['user_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
