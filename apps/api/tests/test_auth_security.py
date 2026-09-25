import unittest
from uuid import uuid4

from jwt.exceptions import InvalidTokenError

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    normalize_username,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User


class AuthSecurityTests(unittest.TestCase):
    def test_password_hash_roundtrip(self):
        password = (
            "correct-horse-battery-staple"
        )

        encoded = hash_password(
            password
        )

        self.assertNotEqual(
            encoded,
            password,
        )

        self.assertTrue(
            verify_password(
                password,
                encoded,
            )
        )

        self.assertFalse(
            verify_password(
                "wrong-password",
                encoded,
            )
        )

    def test_argon2_hash_is_used(self):
        encoded = hash_password(
            "this-is-a-long-test-password"
        )

        self.assertTrue(
            encoded.startswith("$argon2")
        )

    def test_normalize_username(self):
        self.assertEqual(
            normalize_username(
                "  Doctor.ONE  "
            ),
            "doctor.one",
        )

    def test_access_token_roundtrip(self):
        user = User(
            id=uuid4(),
            username="doctor.one",
            password_hash="not-used",
            role=UserRole.DOCTOR,
            is_active=True,
        )

        token = create_access_token(
            user
        )

        claims = decode_access_token(
            token
        )

        self.assertEqual(
            claims["sub"],
            str(user.id),
        )

        self.assertEqual(
            claims["username"],
            "doctor.one",
        )

        self.assertEqual(
            claims["role"],
            "DOCTOR",
        )

        self.assertEqual(
            claims["type"],
            "access",
        )

    def test_invalid_token_rejected(self):
        with self.assertRaises(
            InvalidTokenError
        ):
            decode_access_token(
                "not-a-valid-jwt"
            )


if __name__ == "__main__":
    unittest.main()
