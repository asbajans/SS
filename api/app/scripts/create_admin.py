"""CLI: create the bootstrap admin user (idempotent).
Run: python -m app.scripts.create_admin --email you@x.com --password '...'
"""
import argparse
import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import User
from app.security import hash_password


async def main(email: str, password: str) -> None:
    async with AsyncSessionLocal() as s:
        existing = (await s.scalars(select(User).where(User.email == email))).first()
        if existing:
            print("already exists", existing.email)
            return
        user = User(email=email, password_hash=hash_password(password), is_admin=True)
        s.add(user)
        await s.commit()
        print("created", email)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.email, args.password))
