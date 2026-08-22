from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, select

from app.core.config import settings
from app.dependencies.db import SessionLocal
from app.models.model_provider import ModelProfile, ModelProvider
from app.models.organization import Organization, OrganizationMembership

RUNNER = BACKEND_ROOT / "scripts" / "evaluation" / "knowledge" / "run_knowledge_retrieval_real_provider.py"


def _ollama_json(base_url: str, path: str, payload: dict | None = None) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST" if payload is not None else "GET")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise SystemExit(f"Ollama provider is not reachable at {base_url}: {exc}") from exc


def _model_dimension(base_url: str, model: str) -> int:
    result = _ollama_json(base_url, "/api/embed", {"model": model, "input": "governed evaluation smoke test"})
    embeddings = result.get("embeddings")
    if not embeddings or not embeddings[0]:
        raise SystemExit(f"Ollama did not return an embedding for existing model {model}")
    return len(embeddings[0])


def _assert_model_exists(base_url: str, model: str) -> None:
    models = _ollama_json(base_url, "/api/tags").get("models", [])
    available = {item.get("name") for item in models}
    if model not in available:
        raise SystemExit(
            f"model {model!r} is not installed in Ollama. This smoke test never downloads models; "
            f"available models: {sorted(x for x in available if x)}"
        )


async def _create_fixture(model_a: str, model_b: str, endpoint: str) -> tuple[str, str, str]:
    async with SessionLocal() as db:
        owner_row = (await db.execute(select(OrganizationMembership).where(OrganizationMembership.status == "active").order_by(OrganizationMembership.user_id))).scalars().first()
        if owner_row is None:
            raise SystemExit("governed evaluation smoke test requires an active organization membership")
        organization = (await db.execute(select(Organization).where(Organization.id == owner_row.organization_id))).scalar_one_or_none()
        if organization is None or organization.status != "active":
            raise SystemExit("governed evaluation smoke test requires an active organization")

        provider = ModelProvider(
            organization_id=organization.id,
            name=f"governed-eval-smoke-{uuid4().hex[:10]}",
            provider_type="ollama",
            provider_name="local-ollama-smoke",
            endpoint=endpoint,
            credential_ref=None,
            enabled=True,
            metadata_json={"test_fixture": True},
        )
        db.add(provider)
        await db.flush()
        profile_a = ModelProfile(
            provider_id=provider.id,
            name=f"embedding-a-{uuid4().hex[:8]}",
            model_type="embedding",
            model_name=model_a,
            dimension=_model_dimension(endpoint, model_a),
            capabilities={},
            parameters={},
            enabled=True,
            is_default=False,
        )
        profile_b = ModelProfile(
            provider_id=provider.id,
            name=f"embedding-b-{uuid4().hex[:8]}",
            model_type="embedding",
            model_name=model_b,
            dimension=_model_dimension(endpoint, model_b),
            capabilities={},
            parameters={},
            enabled=True,
            is_default=False,
        )
        db.add_all([profile_a, profile_b])
        await db.commit()
        return str(provider.id), str(profile_a.id), str(profile_b.id)


async def _cleanup_fixture(provider_id: str) -> None:
    async with SessionLocal() as db:
        await db.execute(delete(ModelProvider).where(ModelProvider.id == provider_id))
        await db.commit()


def _run_runner(profile_id: str, baseline: Path, freeze: bool) -> tuple[int, dict]:
    command = [
        sys.executable,
        str(RUNNER),
        "--model-profile-id",
        profile_id,
        "--baseline",
        str(baseline),
        "--k",
        "3",
    ]
    if freeze:
        command.append("--freeze-baseline")
    result = subprocess.run(command, cwd=BACKEND_ROOT, capture_output=True, text=True, check=False, timeout=240)
    stdout = result.stdout.strip()
    if not stdout:
        raise SystemExit(result.stderr or "governed evaluation runner produced no JSON output")
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"governed evaluation runner output is not JSON:\n{stdout}\n{result.stderr}") from exc
    return result.returncode, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Real governed Embedding Profile evaluation smoke test; never downloads models")
    parser.add_argument("--profile-a-model", default=os.getenv("GOVERNED_EVAL_PROFILE_A_MODEL", "nomic-embed-text:latest"))
    parser.add_argument("--profile-b-model", default=os.getenv("GOVERNED_EVAL_PROFILE_B_MODEL", "bge-m3:latest"))
    parser.add_argument("--ollama-base-url", default=os.getenv("OLLAMA_BASE_URL") or settings.embedding_base_url or "http://localhost:11434")
    args = parser.parse_args()

    if args.profile_a_model == args.profile_b_model:
        raise SystemExit("Profile A and Profile B must use different installed embedding models")
    if settings.vector_provider != "pgvector":
        raise SystemExit("governed evaluation smoke test requires VECTOR_PROVIDER=pgvector")

    _assert_model_exists(args.ollama_base_url, args.profile_a_model)
    _assert_model_exists(args.ollama_base_url, args.profile_b_model)
    _model_dimension(args.ollama_base_url, args.profile_a_model)
    _model_dimension(args.ollama_base_url, args.profile_b_model)

    provider_id = profile_a = profile_b = None
    with tempfile.TemporaryDirectory(prefix="governed-eval-") as tmp:
        baseline = Path(tmp) / "profile-a-baseline.json"
        try:
            provider_id, profile_a, profile_b = asyncio.run(_create_fixture(args.profile_a_model, args.profile_b_model, args.ollama_base_url))
            code_a, report_a = _run_runner(profile_a, baseline, freeze=True)
            if code_a != 0 or report_a.get("quality_gate") != "baseline_created":
                raise SystemExit(f"Profile A baseline freeze failed:\n{json.dumps(report_a, ensure_ascii=False, indent=2)}")
            code_b, report_b = _run_runner(profile_b, baseline, freeze=False)
            if code_b == 0:
                raise SystemExit("Profile B unexpectedly passed against Profile A baseline; identity regression gate is broken")
            regression = report_b.get("regression") or {}
            if not regression.get("identity_changed"):
                raise SystemExit(f"Profile B failed without reporting governed identity change:\n{json.dumps(report_b, ensure_ascii=False, indent=2)}")
            if report_b.get("model_profile_id") != profile_b:
                raise SystemExit("evaluation report did not persist selected Profile B identity")
            if report_b.get("provider_id") != provider_id:
                raise SystemExit("evaluation report did not persist governed Provider identity")
            print(json.dumps({"status": "passed", "profile_a": report_a, "profile_b": report_b}, ensure_ascii=False, indent=2))
            return 0
        finally:
            if provider_id:
                asyncio.run(_cleanup_fixture(provider_id))


if __name__ == "__main__":
    raise SystemExit(main())
