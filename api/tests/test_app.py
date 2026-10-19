"""App factory smoke tests - catches router wiring errors without services."""
from app.main import app


def _paths() -> set[str]:
    return set(app.openapi().get("paths", {}))


def test_app_builds_and_exposes_routes():
    paths = _paths()
    expected = {
        "/health",
        "/api/projects",
        "/api/projects/{project_id}/runs",
        "/api/runs",
        "/api/runs/{run_id}",
    }
    missing = expected - paths
    assert not missing, f"missing routes: {sorted(missing)}"


def test_health_route_registered():
    assert "/health" in _paths()
