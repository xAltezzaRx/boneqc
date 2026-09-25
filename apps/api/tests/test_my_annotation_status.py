import unittest

from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.annotations import (
    get_my_annotation_status,
)
from app.schemas.annotation import (
    MyAnnotationStatusResponse,
)


class FakeSession:
    def __init__(
        self,
        *,
        reviewed: bool,
    ) -> None:
        self.reviewed = reviewed

    async def get(
        self,
        model,
        object_id,
    ):
        return object()

    async def scalar(
        self,
        statement,
    ):
        if self.reviewed:
            return uuid4()

        return None


class MyAnnotationStatusTests(
    unittest.IsolatedAsyncioTestCase
):
    async def test_not_reviewed(
        self,
    ) -> None:
        result = (
            await get_my_annotation_status(
                study_id=uuid4(),
                current_user=(
                    SimpleNamespace(
                        id=uuid4()
                    )
                ),
                session=FakeSession(
                    reviewed=False
                ),
            )
        )

        self.assertIsInstance(
            result,
            MyAnnotationStatusResponse,
        )

        self.assertEqual(
            result.model_dump(),
            {
                "reviewed": False,
            },
        )

    async def test_reviewed(
        self,
    ) -> None:
        result = (
            await get_my_annotation_status(
                study_id=uuid4(),
                current_user=(
                    SimpleNamespace(
                        id=uuid4()
                    )
                ),
                session=FakeSession(
                    reviewed=True
                ),
            )
        )

        self.assertEqual(
            result.model_dump(),
            {
                "reviewed": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
