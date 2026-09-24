"""Stage 5 entry-point contract: the standard invoke payload reaches SUCCESS through server.py.

Every node declares required_trust_level = INTERNAL (config/agent.yaml root matches), so the
standalone adapter must promote the STG-only runner token to INTERNAL, while the ordinary
external token stays VERIFIED_EXTERNAL and is refused by the S-1 trust gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("INVOKE_AUTH_TOKEN", "test-external-token")
    monkeypatch.setenv("STG_INTERNAL_RUNNER_TOKEN", "test-internal-runner-token")
    monkeypatch.chdir(_ROOT)  # the payload's source_path is repo-relative, as in the deploy-stg job
    from src.api.server import app

    return TestClient(app)


def _payload() -> dict[str, Any]:
    return json.loads((_ROOT / "deploy" / "invoke_payload.json").read_text(encoding="utf-8"))


def test_standard_payload_succeeds_with_internal_runner_token(client: TestClient) -> None:
    res = client.post(
        "/invoke", json=_payload(), headers={"Authorization": "Bearer test-internal-runner-token"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["output"]["report"]


def test_external_token_is_refused_by_internal_trust_gate(client: TestClient) -> None:
    res = client.post("/invoke", json=_payload(), headers={"Authorization": "Bearer test-external-token"})
    assert res.status_code == 200
    assert res.json()["status"] != "success"


def test_wrong_token_is_rejected(client: TestClient) -> None:
    res = client.post("/invoke", json=_payload(), headers={"Authorization": "Bearer nope"})
    assert res.status_code == 401
