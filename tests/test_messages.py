from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from diddi_support.core.auth import (
    BackofficePrincipal,
    ServicePrincipal,
    require_support_agent,
    require_support_service,
)
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


def _diddicomms_principal() -> ServicePrincipal:
    return ServicePrincipal(
        subject="service:diddicomms",
        client_id="diddicomms-support",
        scopes=frozenset(
            {
                "diddi-support:messages:write",
                "diddi-support:cases:read",
            }
        ),
    )


def test_diddicomms_can_create_idempotent_user_message_and_read_visible_messages() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=UUID("77777777-7777-7777-7777-777777777777"),
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="DiddiComms conversation",
        idempotency_key="sprint3-diddicomms-message-case",
    )
    app.dependency_overrides[require_support_service] = _diddicomms_principal
    app.dependency_overrides[require_support_agent] = _agent_permissions
    try:
        client = TestClient(app)
        headers = {"Idempotency-Key": "sprint3-diddicomms-message-1"}
        first = client.post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers=headers,
            json={"reporter_user_id": str(CASE_USER_ID), "body": "Ma course est bloquée."},
        )
        replay = client.post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers=headers,
            json={"reporter_user_id": str(CASE_USER_ID), "body": "Ma course est bloquée."},
        )
        conflict = client.post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers=headers,
            json={"reporter_user_id": str(CASE_USER_ID), "body": "Autre contenu."},
        )
        client.post(
            f"/support/v1/backoffice/cases/{case.id}/messages",
            json={"body": "Réponse agent visible.", "visibility": "user_visible"},
        )
        client.post(
            f"/support/v1/backoffice/cases/{case.id}/messages",
            json={"body": "Note interne.", "visibility": "internal_note"},
        )
        visible = client.get(f"/support/v1/internal/cases/{case.id}/messages")

        assert first.status_code == 201
        assert replay.status_code == 201
        assert replay.json()["id"] == first.json()["id"]
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"
        assert visible.status_code == 200
        assert [item["visibility"] for item in visible.json()] == [
            "user_visible",
            "user_visible",
        ]
        assert visible.json()[0]["author_type"] == "user"
    finally:
        app.dependency_overrides.pop(require_support_service, None)
        app.dependency_overrides.pop(require_support_agent, None)


def test_diddicomms_can_create_idempotent_ai_message_without_copying_user() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="AI conversation",
        idempotency_key="ai-message-case-1",
    )
    app.dependency_overrides[require_support_service] = _diddicomms_principal
    try:
        client = TestClient(app)
        headers = {"Idempotency-Key": "ai-reply-source-message-1"}
        payload = {
            "author_type": "ai",
            "author_id": "service:diddicomms",
            "body": "Réponse générée par l’assistant IA",
        }
        first = client.post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers=headers,
            json=payload,
        )
        replay = client.post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers=headers,
            json=payload,
        )
        conflict = client.post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers=headers,
            json={**payload, "body": "Réponse différente"},
        )
        visible = client.get(f"/support/v1/internal/cases/{case.id}/messages")

        assert first.status_code == 201
        assert replay.status_code == 201
        assert first.json()["message_id"] == first.json()["id"]
        assert replay.json()["message_id"] == first.json()["message_id"]
        assert first.json()["author_type"] == "ai"
        assert first.json()["author_id"] == "service:diddicomms"
        assert first.json()["visibility"] == "user_visible"
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"
        assert visible.status_code == 200
        assert len(visible.json()) == 1
        assert visible.json()[0]["author_type"] == "ai"
        assert visible.json()[0]["author_id"] == "service:diddicomms"
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_diddicomms_rejects_untrusted_ai_author_id() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="AI attribution check",
        idempotency_key="ai-message-case-2",
    )
    app.dependency_overrides[require_support_service] = _diddicomms_principal
    try:
        response = TestClient(app).post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers={"Idempotency-Key": "ai-reply-invalid-author"},
            json={
                "author_type": "ai",
                "author_id": "user:spoofed",
                "body": "Message non autorisé",
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "AI_MESSAGE_AUTHOR_FORBIDDEN"
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_diddicomms_user_message_must_match_case_reporter() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=UUID("88888888-8888-8888-8888-888888888888"),
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="Ownership check",
        idempotency_key="sprint3-diddicomms-message-case-2",
    )
    app.dependency_overrides[require_support_service] = _diddicomms_principal
    try:
        response = TestClient(app).post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers={"Idempotency-Key": "sprint3-diddicomms-message-2"},
            json={
                "reporter_user_id": "33333333-3333-3333-3333-333333333333",
                "body": "Tentative non autorisée.",
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "MESSAGE_AUTHOR_FORBIDDEN"
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_resolved_case_rejects_user_and_agent_messages() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=UUID("99999999-9999-9999-9999-999999999999"),
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="Resolved conversation",
        idempotency_key="sprint2-resolved-case",
    )
    case.transition_to("in_progress")
    case.transition_to("resolved")
    app.dependency_overrides[require_support_service] = _diddicomms_principal
    app.dependency_overrides[require_support_agent] = _agent_permissions
    try:
        client = TestClient(app)
        user_response = client.post(
            f"/support/v1/internal/cases/{case.id}/messages",
            headers={"Idempotency-Key": "sprint2-resolved-user-message"},
            json={"reporter_user_id": str(CASE_USER_ID), "body": "Encore un message."},
        )
        agent_response = client.post(
            f"/support/v1/backoffice/cases/{case.id}/messages",
            json={"body": "Réponse après résolution.", "visibility": "user_visible"},
        )

        assert user_response.status_code == 409
        assert user_response.json()["detail"]["code"] == "CASE_NOT_MODIFIABLE"
        assert agent_response.status_code == 409
        assert agent_response.json()["detail"]["code"] == "CASE_NOT_MODIFIABLE"
    finally:
        app.dependency_overrides.pop(require_support_service, None)
        app.dependency_overrides.pop(require_support_agent, None)
