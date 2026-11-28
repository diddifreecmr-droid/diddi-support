import json
from pathlib import Path


def test_openapi_documents_backoffice_dual_auth_headers_and_response_correlation() -> None:
    schema = json.loads(
        (Path(__file__).parents[1] / "docs" / "api" / "openapi.json").read_text(
            encoding="utf-8"
        )
    )
    operation = schema["paths"]["/support/v1/backoffice/cases"]["get"]
    header_names = {parameter["name"] for parameter in operation["parameters"]}

    assert {
        "Authorization",
        "X-Client-ID",
        "X-Backoffice-Actor",
        "X-Backoffice-Reason",
    } <= header_names
    for response in operation["responses"].values():
        assert "X-Request-ID" in response["headers"]
