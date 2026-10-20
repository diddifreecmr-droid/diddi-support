from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from diddi_support.core.auth import BackofficePrincipal, require_support_agent
from diddi_support.domain.messages import AttachmentPurpose
from diddi_support.infrastructure.files.client import TemporaryFileAccess
from diddi_support.main import app
from diddi_support.presentation import internal_router

CASE_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
RIDE_ID = UUID("55555555-5555-5555-5555-555555555555")
FILE_ID = UUID("66666666-6666-6666-6666-666666666666")


def _agent_permissions() -> BackofficePrincipal:
    return BackofficePrincipal(
        subject="agent-messages",
        permissions=frozenset(
            {
                "diddi-support:read",
                "diddi-support:reply",
                "diddi-support:write",
                "diddi-support:attachments-read",
            }
        ),
    )


def test_agent_messages_keep_user_reply_and_internal_note_distinct() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=RIDE_ID,
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="Messages test",
        idempotency_key="sprint4-messages-1",
    )
    app.dependency_overrides[require_support_agent] = _agent_permissions
    try:
        client = TestClient(app)
        reply = client.post(
            f"/support/v1/backoffice/cases/{case.id}/messages",
            json={"body": "Nous avons bien reçu votre demande.", "visibility": "user_visible"},
        )
        note = client.post(
            f"/support/v1/backoffice/cases/{case.id}/messages",
            json={"body": "Vérifier la chronologie côté DiddiGo.", "visibility": "internal_note"},
        )
        messages = client.get(f"/support/v1/backoffice/cases/{case.id}/messages")

        assert reply.status_code == 200
        assert note.status_code == 200
        assert messages.status_code == 200
        assert [item["visibility"] for item in messages.json()] == [
            "user_visible",
            "internal_note",
        ]
    finally:
        app.dependency_overrides.pop(require_support_agent, None)


def test_attachment_is_validated_and_temporary_access_never_exposes_public_url() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=RIDE_ID,
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="Attachments test",
        idempotency_key="sprint4-attachments-1",
    )

    class FakeFilesClient:
        async def temporary_access(self, **_: object) -> TemporaryFileAccess:
            return TemporaryFileAccess(
                temporary_url="https://files.example.test/temporary/file-1",
                expires_at=datetime.now(UTC),
            )

    original_client = internal_router.diddifiles_client
    internal_router.diddifiles_client = FakeFilesClient()
    app.dependency_overrides[require_support_agent] = _agent_permissions
    try:
        client = TestClient(app)
        attachment = client.post(
            f"/support/v1/backoffice/cases/{case.id}/attachments",
            json={
                "file_id": str(FILE_ID),
                "owner_user_id": str(CASE_USER_ID),
                "purpose": AttachmentPurpose.PHOTO,
                "mime_type": "image/jpeg",
                "size_bytes": 1024,
            },
        )
        access = client.post(
            f"/support/v1/backoffice/cases/{case.id}/attachments/{attachment.json()['id']}/temporary-access",
        )
        forbidden_mime = client.post(
            f"/support/v1/backoffice/cases/{case.id}/attachments",
            json={
                "file_id": str(FILE_ID),
                "owner_user_id": str(CASE_USER_ID),
                "purpose": AttachmentPurpose.PHOTO,
                "mime_type": "application/pdf",
                "size_bytes": 1024,
            },
        )

        assert attachment.status_code == 200
        assert access.status_code == 200
        assert "public_url" not in access.json()
        assert forbidden_mime.status_code == 415
    finally:
        internal_router.diddifiles_client = original_client
        app.dependency_overrides.pop(require_support_agent, None)
