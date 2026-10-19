import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class ManifestIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience: str
    issuer: str
    required_service_claims: dict[str, str]
    required_headers: list[str]
    scopes: list[str]


class SupportManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    protocol: str
    module: str
    version: str
    status: str
    display_name: str
    identity: ManifestIdentity
    ownership: dict[str, list[str]]
    http: dict[str, Any]
    events: dict[str, Any]
    attachments: dict[str, Any]
    reliability: dict[str, Any]
    compatibility: dict[str, Any]

    @property
    def required_scopes(self) -> frozenset[str]:
        return frozenset(self.identity.scopes)


def load_manifest(path: str | Path) -> SupportManifest:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Support manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = SupportManifest.model_validate(payload)
    if manifest.protocol != "diddi.module.v1":
        raise ValueError("Unsupported Diddi module protocol")
    if manifest.module != "diddi-support":
        raise ValueError("Manifest module must be diddi-support")
    if manifest.status not in {"proposed", "active"}:
        raise ValueError("Manifest status must be proposed or active")
    return manifest
