from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from dataclasses import replace
from pathlib import Path
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select, text

from app.core.config import settings
from app.dependencies.db import SessionLocal
from app.models.model_provider import ModelProfile, ModelProvider
from app.models.organization import Organization, OrganizationMembership
from app.services.embedding_provider import EmbeddingProviderError, OpenAICompatibleEmbeddingProvider
from app.services.ollama_embedding_provider import OllamaEmbeddingProvider
from app.services.retrieval_evaluation import RetrievalEvaluationObservation, aggregate_observations
from app.services.retrieval_evaluation_baseline import build_baseline, build_regression_report, compare_baseline, write_baseline
from app.services.retrieval_evaluation_config import RetrievalEvaluationConfig, config_from_settings, resolve_api_key, validate_config
from app.services.retrieval_evaluation_dataset import load_retrieval_evaluation_dataset
from app.services.retrieval_evaluation_trace import RetrievalEvaluationTraceService
from app.services.vector_knowledge_retrieval import VectorKnowledgeRetrievalService
from app.services.vector_retrieval_provider import PgVectorRetrievalProvider, VectorRecord
from scripts.evaluation.knowledge.run_knowledge_retrieval_evaluation import KB_ID, VERSION_ID, actual_chunk_id, cleanup_fixture, load_jsonl, prepare_fixture

BASELINE = BACKEND_ROOT / "evaluation" / "knowledge_retrieval_real_baseline.json"


def _dataset_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_real_provider(config: RetrievalEvaluationConfig) -> None:
    validate_config(config)
    if settings.vector_provider != "pgvector":
        raise SystemExit("Real Provider Quality Gate requires VECTOR_PROVIDER=pgvector")


def _build_embedding_provider(config: RetrievalEvaluationConfig):
    common = {
        "model": config.embedding_model,
        "timeout_seconds": config.embedding_timeout_seconds,
        "expected_dimension": config.embedding_dimension,
    }
    if config.embedding_provider == "ollama":
        return OllamaEmbeddingProvider(base_url=config.embedding_base_url, **common)
    return OpenAICompatibleEmbeddingProvider(
        base_url=config.embedding_base_url,
        api_key=config.embedding_api_key or "",
        dimensions=config.embedding_dimension if config.embedding_dimensions_parameter_enabled else None,
        **common,
    )


async def _resolve_governed_embedding_profile(db, profile_id: UUID, user_id: UUID) -> tuple[ModelProfile, ModelProvider]:
    result = await db.execute(
        select(ModelProfile, ModelProvider)
        .join(ModelProvider, ModelProvider.id == ModelProfile.provider_id)
        .join(Organization, Organization.id == ModelProvider.organization_id)
        .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
        .where(
            ModelProfile.id == profile_id,
            ModelProfile.model_type == "embedding",
            ModelProfile.enabled.is_(True),
            ModelProvider.enabled.is_(True),
            Organization.status == "active",
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == "active",
        )
    )
    row = result.first()
    if row is None:
        raise SystemExit("selected embedding Model Profile does not exist, is disabled, or is unavailable to the evaluation actor")
    profile, provider = row
    if profile.dimension is None:
        raise SystemExit("selected embedding Model Profile must declare dimension")
    if not provider.endpoint:
        raise SystemExit("selected Model Provider must declare an endpoint")
    if provider.provider_type not in {"ollama", "openai-compatible"}:
        raise SystemExit(f"unsupported governed embedding provider_type: {provider.provider_type}")
    return profile, provider


def _config_from_profile(config: RetrievalEvaluationConfig, profile: ModelProfile, provider: ModelProvider) -> RetrievalEvaluationConfig:
    parameters = profile.parameters or {}
    credential = resolve_api_key(provider.credential_ref)
    dimensions_parameter_enabled = bool(
        parameters.get("dimensions_parameter_enabled", config.embedding_dimensions_parameter_enabled)
    )
    timeout_seconds = float(parameters.get("timeout_seconds", config.embedding_timeout_seconds))
    return replace(
        config,
        embedding_provider=provider.provider_type,
        embedding_base_url=provider.endpoint,
        embedding_api_key=credential,
        embedding_model=profile.model_name,
        embedding_timeout_seconds=timeout_seconds,
        embedding_dimension=profile.dimension or 0,
        embedding_dimensions_parameter_enabled=dimensions_parameter_enabled,
    )


def _configured_threshold_failures(config: RetrievalEvaluationConfig, metrics: dict[str, float | int]) -> list[str]:
    failures: list[str] = []
    for metric, minimum in (
        ("recall_at_k", config.min_recall_at_k),
        ("precision_at_k", config.min_precision_at_k),
        ("mrr", config.min_mrr),
        ("citation_correctness", config.min_citation_correctness),
    ):
        if minimum is not None and float(metrics[metric]) < minimum:
            failures.append(f"{metric} below configured minimum: {metrics[metric]} < {minimum}")
    if float(metrics["error_rate"]) > config.max_error_rate:
        failures.append(f"provider error rate above configured maximum: {metrics['error_rate']} > {config.max_error_rate}")
    return failures


async def run(config: RetrievalEvaluationConfig, freeze_baseline: bool) -> int:
    if settings.vector_provider != "pgvector":
        raise SystemExit("Real Provider Quality Gate requires VECTOR_PROVIDER=pgvector")
    dataset = load_retrieval_evaluation_dataset(config.dataset_path)
    fixtures = load_jsonl(config.fixture_path)
    fixture_by_id = {row["chunk_id"]: row for row in fixtures}
    missing = sorted({chunk_id for case in dataset.cases for chunk_id in case.relevant_chunk_ids if chunk_id not in fixture_by_id})
    if missing:
        raise SystemExit(f"evaluation fixture missing relevant chunks: {missing}")

    evaluation_run_id = str(uuid.uuid4())
    async with SessionLocal() as db:
        owner_row = (await db.execute(text("SELECT id, tenant_id FROM users ORDER BY id LIMIT 1"))).first()
        if owner_row is None:
            raise SystemExit("evaluation runner requires at least one user in the database")
        owner = uuid.UUID(str(owner_row[0]))
        tenant_id = uuid.UUID(str(owner_row[1])) if owner_row[1] else None

        profile = None
        model_provider = None
        effective_config = config
        if config.model_profile_id is not None:
            profile, model_provider = await _resolve_governed_embedding_profile(db, config.model_profile_id, owner)
            effective_config = _config_from_profile(config, profile, model_provider)
        _require_real_provider(effective_config)
        provider = _build_embedding_provider(effective_config)

        evaluation_parameters = {
            "top_k": effective_config.top_k,
            "min_score": effective_config.min_score,
            "min_recall_at_k": effective_config.min_recall_at_k,
            "min_precision_at_k": effective_config.min_precision_at_k,
            "min_mrr": effective_config.min_mrr,
            "min_citation_correctness": effective_config.min_citation_correctness,
            "max_error_rate": effective_config.max_error_rate,
            "embedding_dimensions_parameter_enabled": effective_config.embedding_dimensions_parameter_enabled,
        }
        metadata = {
            "evaluation_run_id": evaluation_run_id,
            "provider": effective_config.embedding_provider,
            "model": effective_config.embedding_model,
            "embedding_dimension": effective_config.embedding_dimension,
            "dataset_version": dataset.schema_version,
            "dataset_sha256": _dataset_sha256(config.dataset_path),
            "retrieval_mode": "real-provider-pgvector",
            "retrieval_execution_path": "runtime-service",
            "top_k": effective_config.top_k,
            "citation_source": "runtime-retrieval-result",
            "evaluation_parameters": evaluation_parameters,
        }
        if profile is not None and model_provider is not None:
            metadata.update({
                "model_profile_id": str(profile.id),
                "provider_id": str(model_provider.id),
                "provider_name": model_provider.provider_name,
                "provider_type": model_provider.provider_type,
                "model_profile_name": profile.name,
            })

        await prepare_fixture(db, fixtures, owner)
        try:
            observations: list[RetrievalEvaluationObservation] = []
            case_reports: list[dict[str, object]] = []
            vector_provider = PgVectorRetrievalProvider(db, effective_config.embedding_dimension)
            started = time.perf_counter()
            try:
                fixture_embeddings = await provider.embed([row["content"] for row in fixtures])
            except EmbeddingProviderError as exc:
                error = f"{type(exc).__name__}: {exc}"
                latency_ms = round((time.perf_counter() - started) * 1000, 3)
                observations = [RetrievalEvaluationObservation((), latency_ms, error, ()) for _ in dataset.cases]
                case_reports = [{"query": case.query, "relevant_chunk_ids": sorted(case.relevant_chunk_ids), "expected_citation_targets": sorted(case.expected_citation_targets), "retrieved_chunk_ids": [], "cited_chunk_ids": [], "citations": [], "latency_ms": latency_ms, "error": error} for case in dataset.cases]
            else:
                records = [VectorRecord(chunk_id=str(actual_chunk_id(row["chunk_id"])), embedding=tuple(embedding), metadata={"knowledge_base_id": str(KB_ID), "document_version_id": str(VERSION_ID), "evaluation_chunk_id": row["chunk_id"]}) for row, embedding in zip(fixtures, fixture_embeddings, strict=True)]
                await vector_provider.upsert(records)
                await db.execute(text("UPDATE knowledge_document_versions SET vector_index_status = 'ready' WHERE id = :version"), {"version": str(VERSION_ID)})
                await db.commit()
                evaluation_service = VectorKnowledgeRetrievalService(db, embedding_provider=provider, embedding_dimension=effective_config.embedding_dimension)
                actual_to_evaluation = {str(actual_chunk_id(row["chunk_id"])): row["chunk_id"] for row in fixtures}
                for case in dataset.cases:
                    started = time.perf_counter()
                    error = None
                    ranking: list[str] = []
                    cited_chunk_ids: list[str] = []
                    citations: list[dict[str, object]] = []
                    try:
                        results = await evaluation_service.retrieve(query=case.query, top_k=effective_config.top_k, owner_id=owner, is_admin=False, knowledge_base_id=KB_ID, min_score=effective_config.min_score)
                        for result in results:
                            evaluation_chunk_id = actual_to_evaluation.get(str(result["chunk_id"]))
                            if evaluation_chunk_id is None:
                                continue
                            ranking.append(evaluation_chunk_id)
                            cited_chunk_ids.append(evaluation_chunk_id)
                            citations.append({"chunk_id": evaluation_chunk_id, "citation": result["citation"], "source_document": result["source_document"], "source_uri": result["source_uri"], "relevance_score": result["relevance_score"]})
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                    latency_ms = round((time.perf_counter() - started) * 1000, 3)
                    observations.append(RetrievalEvaluationObservation(tuple(ranking), latency_ms, error, tuple(cited_chunk_ids)))
                    case_reports.append({"query": case.query, "relevant_chunk_ids": sorted(case.relevant_chunk_ids), "expected_citation_targets": sorted(case.expected_citation_targets), "retrieved_chunk_ids": ranking, "cited_chunk_ids": cited_chunk_ids, "citations": citations, "latency_ms": latency_ms, "error": error})

            metrics = aggregate_observations(dataset.cases, observations, k=effective_config.top_k)
            baseline_status = "not_checked"
            failures = _configured_threshold_failures(effective_config, metrics)
            regression = None
            if freeze_baseline:
                if metrics["error_rate"] > 0:
                    failures.append(f"cannot freeze baseline with provider error rate {metrics['error_rate']}")
                elif effective_config.baseline_path.exists():
                    failures.append(f"baseline already exists: {effective_config.baseline_path}; review the existing baseline before replacing it")
                else:
                    write_baseline(effective_config.baseline_path, build_baseline(metadata, metrics))
                    baseline_status = "created"
            elif not effective_config.baseline_path.exists():
                baseline_status = "missing"
                failures.append(f"real provider baseline is missing: {effective_config.baseline_path}")
            else:
                baseline = json.loads(effective_config.baseline_path.read_text(encoding="utf-8"))
                regression = build_regression_report(metadata, metrics, baseline)
                failures.extend(compare_baseline(metadata, metrics, baseline))
                baseline_status = "checked"

            quality_gate = "passed" if baseline_status == "checked" and not failures else ("baseline_created" if baseline_status == "created" and not failures else "failed")
            report = {"dataset": {"path": str(dataset.source), "schema_version": dataset.schema_version, "sha256": metadata["dataset_sha256"]}, **metadata, "source": "postgresql/pgvector", "fallback_count": 0, "fallback_used": False, "baseline": {"path": str(effective_config.baseline_path), "status": baseline_status}, "regression": regression, **metrics, "cases_detail": case_reports, "quality_gate": quality_gate, "failures": failures}
            await RetrievalEvaluationTraceService(db).record_run(evaluation_run_id=evaluation_run_id, owner_id=owner, tenant_id=tenant_id, metadata=metadata, case_reports=case_reports, metrics=metrics, regression=regression, quality_gate=quality_gate, failures=failures)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1 if failures else 0
        finally:
            await cleanup_fixture(db)


def _build_config(args: argparse.Namespace) -> RetrievalEvaluationConfig:
    defaults = config_from_settings(backend_root=BACKEND_ROOT, settings=settings)
    return RetrievalEvaluationConfig(
        embedding_provider=args.embedding_provider or defaults.embedding_provider,
        embedding_base_url=args.embedding_base_url or defaults.embedding_base_url,
        embedding_api_key=resolve_api_key(args.embedding_api_key_env) if args.embedding_api_key_env else defaults.embedding_api_key,
        embedding_model=args.embedding_model or defaults.embedding_model,
        embedding_timeout_seconds=args.embedding_timeout_seconds if args.embedding_timeout_seconds is not None else defaults.embedding_timeout_seconds,
        embedding_dimension=args.embedding_dimension if args.embedding_dimension is not None else defaults.embedding_dimension,
        embedding_dimensions_parameter_enabled=args.embedding_dimensions_parameter_enabled if args.embedding_dimensions_parameter_enabled is not None else defaults.embedding_dimensions_parameter_enabled,
        dataset_path=args.dataset or defaults.dataset_path,
        fixture_path=args.fixture or defaults.fixture_path,
        baseline_path=args.baseline,
        top_k=args.k,
        min_score=args.min_score,
        model_profile_id=UUID(args.model_profile_id) if args.model_profile_id else None,
        min_recall_at_k=args.min_recall_at_k,
        min_precision_at_k=args.min_precision_at_k,
        min_mrr=args.min_mrr,
        min_citation_correctness=args.min_citation_correctness,
        max_error_rate=args.max_error_rate,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Retrieval Quality Gate with a configurable real embedding provider and PostgreSQL/pgvector")
    parser.add_argument("--model-profile-id", help="Organization-governed embedding Model Profile UUID; when supplied, provider/model/dimension/endpoint are resolved from the database")
    parser.add_argument("--embedding-provider", choices=["ollama", "openai-compatible"])
    parser.add_argument("--embedding-base-url")
    parser.add_argument("--embedding-api-key-env", help="Environment variable containing the provider API key; the key itself is never persisted in the report")
    parser.add_argument("--embedding-model")
    parser.add_argument("--embedding-timeout-seconds", type=float)
    parser.add_argument("--embedding-dimension", type=int)
    parser.add_argument("--embedding-dimensions-parameter-enabled", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--min-recall-at-k", type=float)
    parser.add_argument("--min-precision-at-k", type=float)
    parser.add_argument("--min-mrr", type=float)
    parser.add_argument("--min-citation-correctness", type=float)
    parser.add_argument("--max-error-rate", type=float, default=0.0)
    parser.add_argument("--freeze-baseline", action="store_true")
    args = parser.parse_args()
    config = _build_config(args)
    validate_config(config)
    return asyncio.run(run(config, args.freeze_baseline))


if __name__ == "__main__":
    raise SystemExit(main())
