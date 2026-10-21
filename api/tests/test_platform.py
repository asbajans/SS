"""Blog seed integrity + webhook outbound URL guards (offline)."""
import pytest

from app.startup import BLOG_POSTS
from app.webhooks import assert_public_host, validate_webhook_url


def test_blog_posts_bilingual_and_unique():
    slugs = [post["slug"] for post in BLOG_POSTS]
    assert len(slugs) == len(set(slugs))
    for post in BLOG_POSTS:
        for key in ("title_tr", "title_en", "excerpt_tr", "excerpt_en", "body_tr", "body_en"):
            assert post[key].strip(), f"{post['slug']} missing {key}"
        assert "## " in post["body_tr"]
        assert "## " in post["body_en"]


def test_webhook_url_validation():
    assert validate_webhook_url("https://example.com/hooks/ss") == "https://example.com/hooks/ss"
    for url in (
        "http://example.com/hook",
        "https://localhost/hook",
        "https://127.0.0.1/hook",
        "https://user:pass@example.com/hook",
        "not-a-url",
    ):
        with pytest.raises(ValueError):
            validate_webhook_url(url)


def test_private_hosts_blocked():
    for host in ("localhost", "127.0.0.1", "::1"):
        with pytest.raises(ValueError):
            assert_public_host(host)
