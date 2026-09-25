import unittest

from app.queue.service import (
    ANALYSIS_DEAD_QUEUE,
    ANALYSIS_QUEUE,
    ANALYSIS_RETRY_DELAY_SECONDS,
    MAX_ANALYSIS_ATTEMPTS,
)


class QueueRetryPolicyTests(unittest.TestCase):
    def test_analysis_queue_name(self):
        self.assertEqual(
            ANALYSIS_QUEUE,
            "boneqc:analysis:jobs",
        )

    def test_dead_letter_queue_name(self):
        self.assertEqual(
            ANALYSIS_DEAD_QUEUE,
            "boneqc:analysis:dead",
        )

    def test_max_attempts(self):
        self.assertEqual(
            MAX_ANALYSIS_ATTEMPTS,
            3,
        )

    def test_retry_delay(self):
        self.assertGreater(
            ANALYSIS_RETRY_DELAY_SECONDS,
            0,
        )


if __name__ == "__main__":
    unittest.main()
