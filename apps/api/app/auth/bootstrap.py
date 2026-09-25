import argparse
import asyncio
import re
import sys

from sqlalchemy import select

from app.auth.security import (
    hash_password,
    normalize_username,
)
from app.database.session import (
    AsyncSessionLocal,
)
from app.models.enums import UserRole
from app.models.user import User


USERNAME_RE = re.compile(
    r"^[a-z0-9._-]{3,64}$"
)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--username",
        required=True,
    )

    parser.add_argument(
        "--role",
        choices=[
            role.value
            for role in UserRole
        ],
        default=UserRole.ADMIN.value,
    )

    parser.add_argument(
        "--password-stdin",
        action="store_true",
    )

    return parser.parse_args()


async def bootstrap(
    *,
    username: str,
    password: str,
    role: UserRole,
) -> None:
    username = normalize_username(
        username
    )

    if not USERNAME_RE.fullmatch(
        username
    ):
        raise SystemExit(
            "Username must be 3-64 characters: "
            "a-z, 0-9, dot, underscore or hyphen"
        )

    if len(password) < 12:
        raise SystemExit(
            "Password must contain at least "
            "12 characters"
        )

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(User).where(
                User.username == username
            )
        )

        if existing is not None:
            raise SystemExit(
                f"User already exists: {username}"
            )

        user = User(
            username=username,
            password_hash=hash_password(
                password
            ),
            role=role,
            is_active=True,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        print(
            "USER_CREATED",
            user.id,
            user.username,
            user.role.value,
        )


def main() -> None:
    args = parse_args()

    if not args.password_stdin:
        raise SystemExit(
            "Use --password-stdin"
        )

    password = sys.stdin.readline().rstrip(
        "\r\n"
    )

    asyncio.run(
        bootstrap(
            username=args.username,
            password=password,
            role=UserRole(args.role),
        )
    )


if __name__ == "__main__":
    main()
