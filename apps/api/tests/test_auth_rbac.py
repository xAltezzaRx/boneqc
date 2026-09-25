import asyncio
import unittest
from uuid import uuid4

from fastapi import HTTPException

from app.auth.context import (
    get_current_actor,
    reset_current_actor,
    set_current_actor,
)
from app.auth.security import require_roles
from app.models.enums import UserRole
from app.models.user import User


def make_user(
    role: UserRole,
) -> User:
    return User(
        id=uuid4(),
        username=f"{role.value.lower()}.test",
        password_hash="unused",
        role=role,
        is_active=True,
    )


class AuthRBACTests(unittest.TestCase):
    def test_admin_role_allowed(self):
        dependency = require_roles(
            UserRole.ADMIN
        )

        user = make_user(
            UserRole.ADMIN
        )

        result = asyncio.run(
            dependency(
                current_user=user
            )
        )

        self.assertIs(
            result,
            user,
        )

    def test_doctor_cannot_use_admin_role(self):
        dependency = require_roles(
            UserRole.ADMIN
        )

        user = make_user(
            UserRole.DOCTOR
        )

        with self.assertRaises(
            HTTPException
        ) as context:
            asyncio.run(
                dependency(
                    current_user=user
                )
            )

        self.assertEqual(
            context.exception.status_code,
            403,
        )

    def test_actor_context_is_reset(self):
        self.assertIsNone(
            get_current_actor()
        )

        token = set_current_actor(
            "doctor.test"
        )

        self.assertEqual(
            get_current_actor(),
            "doctor.test",
        )

        reset_current_actor(token)

        self.assertIsNone(
            get_current_actor()
        )


if __name__ == "__main__":
    unittest.main()
