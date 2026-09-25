import unittest
from uuid import uuid4

from app.audit.service import create_audit_event
from app.database.session import AsyncSessionLocal
from app.models.audit_event import AuditEvent
from app.models.enums import AuditEventType, StudyStatus
from app.models.study import Study


class AuditServiceTests(
    unittest.IsolatedAsyncioTestCase
):

    async def test_create_audit_event(self) -> None:
        study_id = uuid4()

        async with AsyncSessionLocal() as session:

            study = Study(
                id=study_id,
                status=StudyStatus.READY,
                original_filename="test.dcm",
                source_object_key=f"studies/{study_id}/source.dcm",
                preview_object_key=f"studies/{study_id}/preview.png",
                dicom_metadata={
                    "test": True,
                },
            )

            session.add(study)

            await session.flush()


            event = await create_audit_event(
                session,
                event_type=AuditEventType.STUDY_CREATED,
                entity_type="STUDY",
                entity_id=study_id,
                study_id=study_id,
                payload={
                    "test": True,
                },
            )

            await session.commit()


            self.assertEqual(
                event.event_type,
                AuditEventType.STUDY_CREATED,
            )

            self.assertEqual(
                event.entity_type,
                "STUDY",
            )


        async with AsyncSessionLocal() as session:

            stored = await session.get(
                AuditEvent,
                event.id,
            )

            self.assertIsNotNone(stored)

            self.assertEqual(
                stored.payload["test"],
                True,
            )


if __name__ == "__main__":
    unittest.main()
