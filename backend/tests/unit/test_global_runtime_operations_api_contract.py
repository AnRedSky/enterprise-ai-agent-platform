from app.api.v1.runtime.router import router


def test_global_runtime_operations_route_is_mounted() -> None:
    route = next(
        route for route in router.routes
        if getattr(route, "path", None) == "/api/v1/runtime/global"
    )

    assert route.methods == {"GET"}


def test_global_runtime_operations_route_is_read_only() -> None:
    paths = {
        (getattr(route, "path", None), frozenset(getattr(route, "methods", set())))
        for route in router.routes
        if getattr(route, "path", None) == "/api/v1/runtime/global"
    }

    assert ("/api/v1/runtime/global", frozenset({"GET"})) in paths
