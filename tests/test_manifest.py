from pathlib import Path

from diddi_support.core.manifest import load_manifest


def test_support_manifest_is_valid() -> None:
    manifest = load_manifest(Path("manifests/diddi-support.v1.json"))

    assert manifest.module == "diddi-support"
    assert manifest.protocol == "diddi.module.v1"
    assert "diddi-support:cases:create" in manifest.required_scopes
    assert manifest.compatibility["contract_tests_required"] is True

