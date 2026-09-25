import asyncio
import unittest
from uuid import uuid4

from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.api.v1.analysis import (
    router as analysis_router,
)
from app.api.v1.results import (
    router as results_router,
)
from app.models.enums import UserRole
from app.models.user import User


def make_user(
    role: UserRole,
) -> User:
    return User(
        id=uuid4(),
        username=(
            f"{role.value.lower()}.result.test"
        ),
        password_hash="unused",
        role=role,
        is_active=True,
    )


def find_get_route(
    router,
    path: str,
) -> APIRoute:
    for route in router.routes:
        if not isinstance(
            route,
            APIRoute,
        ):
            continue

        if route.path != path:
            continue

        if "GET" not in route.methods:
            continue

        return route

    raise AssertionError(
        f"GET route not found: {path}"
    )


def result_role_dependency(
    route: APIRoute,
):
    candidates = []

    for depends in route.dependencies:
        dependency = getattr(
            depends,
            "dependency",
            None,
        )

        if dependency is None:
            continue

        if (
            getattr(
                dependency,
                "__name__",
                "",
            )
            == "dependency"
        ):
            candidates.append(
                dependency
            )

    if len(candidates) != 1:
        raise AssertionError(
            "Expected exactly one "
            "result RBAC dependency, "
            f"found {len(candidates)} "
            f"for {route.path}"
        )

    return candidates[0]


class ResultRBACTests(
    unittest.TestCase,
):
    def assert_result_policy(
        self,
        *,
        router,
        path: str,
    ) -> None:
        route = find_get_route(
            router,
            path,
        )

        dependency = (
            result_role_dependency(
                route
            )
        )

        for role in (
            UserRole.ADMIN,
            UserRole.OPERATOR,
        ):
            with self.subTest(
                path=path,
                role=role,
            ):
                user = make_user(
                    role
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

        doctor = make_user(
            UserRole.DOCTOR
        )

        with self.assertRaises(
            HTTPException
        ) as context:
            asyncio.run(
                dependency(
                    current_user=doctor
                )
            )

        self.assertEqual(
            context.exception.status_code,
            403,
        )

        self.assertEqual(
            context.exception.detail,
            {
                "code":
                    "INSUFFICIENT_PERMISSIONS"
            },
        )

    def test_study_result_is_blind_to_doctor(
        self,
    ):
        self.assert_result_policy(
            router=results_router,
            path=(
                "/studies/"
                "{study_id}/result"
            ),
        )

    def test_job_result_is_blind_to_doctor(
        self,
    ):
        self.assert_result_policy(
            router=analysis_router,
            path=(
                "/jobs/"
                "{job_id}/result"
            ),
        )


if __name__ == "__main__":
    unittest.main()
