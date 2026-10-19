"""Auth flow test with SQLite-free skip (DB required - marked integration)."""
import pytest

pytestmark = pytest.mark.integration


def test_register_login_offline_skip():
    pytest.skip("offline CI - API tests run with Postgres via docker compose in integration job")
