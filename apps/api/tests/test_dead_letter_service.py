import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from app.queue.service import (
    ANALYSIS_DEAD_QUEUE,
    ANALYSIS_QUEUE,
    count_dead_letters,
    list_dead_letters,
    requeue_analysis_job,
)


JOB_ID = UUID(
    "11111111-2222-3333-4444-555555555555"
)

STUDY_ID = UUID(
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
)


class DeadLetterServiceTests(
    unittest.IsolatedAsyncioTestCase
):
    @patch("app.queue.service.redis_client")
    async def test_count_dead_letters(
        self,
        redis,
    ):
        redis.llen = AsyncMock(return_value=3)

        result = await count_dead_letters()

        self.assertEqual(result, 3)

        redis.llen.assert_awaited_once_with(
            ANALYSIS_DEAD_QUEUE
        )

    @patch("app.queue.service.redis_client")
    async def test_list_dead_letters(
        self,
        redis,
    ):
        payload = {
            "job_id": str(JOB_ID),
            "study_id": str(STUDY_ID),
            "attempts": 3,
            "error_message": "failure",
            "failure_type": "retry_exhausted",
        }

        redis.lrange = AsyncMock(
            return_value=[json.dumps(payload)]
        )

        result = await list_dead_letters(
            offset=0,
            limit=10,
        )

        self.assertEqual(
            result,
            [payload],
        )

    @patch("app.queue.service.redis_client")
    async def test_list_skips_invalid_json(
        self,
        redis,
    ):
        redis.lrange = AsyncMock(
            return_value=["not-json"]
        )

        result = await list_dead_letters()

        self.assertEqual(result, [])

    @patch("app.queue.service.redis_client")
    async def test_requeue_removes_matching_dlq(
        self,
        redis,
    ):
        matching = json.dumps(
            {
                "job_id": str(JOB_ID),
                "study_id": str(STUDY_ID),
                "attempts": 3,
                "error_message": "failure",
                "failure_type": "retry_exhausted",
            }
        )

        other = json.dumps(
            {
                "job_id": (
                    "99999999-9999-9999-9999-999999999999"
                ),
                "study_id": str(STUDY_ID),
                "attempts": 3,
                "error_message": "other",
                "failure_type": "retry_exhausted",
            }
        )

        redis.lrange = AsyncMock(
            return_value=[
                matching,
                other,
            ]
        )

        pipeline = MagicMock()
        pipeline.rpush.return_value = pipeline
        pipeline.lrem.return_value = pipeline
        pipeline.execute = AsyncMock(
            return_value=[1, 1]
        )

        redis.pipeline = MagicMock(
            return_value=pipeline
        )

        removed = await requeue_analysis_job(
            job_id=JOB_ID,
            study_id=STUDY_ID,
        )

        self.assertEqual(removed, 1)

        pipeline.rpush.assert_called_once()

        pipeline.lrem.assert_called_once_with(
            ANALYSIS_DEAD_QUEUE,
            0,
            matching,
        )

        args = pipeline.rpush.call_args.args

        self.assertEqual(
            args[0],
            ANALYSIS_QUEUE,
        )

    @patch("app.queue.service.redis_client")
    async def test_requeue_without_dlq_entry(
        self,
        redis,
    ):
        redis.lrange = AsyncMock(
            return_value=[]
        )

        pipeline = MagicMock()
        pipeline.rpush.return_value = pipeline
        pipeline.execute = AsyncMock(
            return_value=[1]
        )

        redis.pipeline = MagicMock(
            return_value=pipeline
        )

        removed = await requeue_analysis_job(
            job_id=JOB_ID,
            study_id=STUDY_ID,
        )

        self.assertEqual(removed, 0)

        pipeline.lrem.assert_not_called()


if __name__ == "__main__":
    unittest.main()
