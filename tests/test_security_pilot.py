from uuid import UUID

from fastapi.testclient import TestClient

from diddi_support.core.auth import BackofficePrincipal, require_support_agent
from diddi_support.domain.messages import AttachmentPurpose
from diddi_support.main import app
from diddi_support.presentation import internal_router


def test_attachment_owner_boundary_is_enforced() -> None:
    owner = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    other_user = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        reporter_user_id=owner,
        category="safety",
        subject="BOLA test",
        idempotency_key="sprint10-bola-case",
    )

    def agent() -> BackofficePrincipal:
        return BackofficePrincipal(
            subject="agent-security",
            permissions=frozenset({"diddi-support:reply"}),
        )

    app.dependency_overrides[require_support_agent] = agent
    try:
        response = TestClient(app).post(
            f"/support/v1/backoffice/cases/{case.id}/attachments",
            json={
                "file_id": str(UUID("abababab-abab-abab-abab-abababababab")),
                "owner_user_id": str(other_user),
                "purpose": AttachmentPurpose.PHOTO,
                "mime_type": "image/jpeg",
                "size_bytes": 10,
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "ATTACHMENT_OWNER_MISMATCH"
    finally:
        app.dependency_overrides.pop(require_support_agent, None)
