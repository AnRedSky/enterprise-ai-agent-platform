from __future__ import annotations

from app.api.v1.runtime.diagnostics import router


def test_runtime_diagnostics_exposes_worker_and_scheduler_read_routes() -> None:
    paths = {route.path for route in router.routes}

    assert "/diagnostics/worker" in paths
    assert "/diagnostics/scheduler" in paths


def test_runtime_diagnostics_routes_are_get_only() -> None:
    methods_by_path = {route.path: route.methods for route in router.routes}

    assert methods_by_path["/diagnostics/worker"] == {"GET"}
    assert methods_by_path["/diagnostics/scheduler"] == {"GET"}
