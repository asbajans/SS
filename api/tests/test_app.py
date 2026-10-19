"""App factory smoke tests - catches router wiring errors without services."""
from app.main import app


def test_app_builds_and_exposes_routes():
    paths = {getattr(r, "path", "") for r in app.routes}
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
    assert any(getattr(r, "path", "") == "/health" for r in app.routes)
