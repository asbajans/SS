"""Email embedding service (TEI, self-hosted). Zero external calls."""
import httpx

from app.config import settings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if settings.llm_mock_mode or not settings.tei_url:
        return [[0.0] * settings.embed_dim for _ in texts]
    async with httpx.AsyncClient(timeout=120) as client:  # local TEI
        r = await client.post(
            f"{settings.tei_url}/v1/embed",
            json={"input": texts, "model": settings.embed_model},
        )
        r.raise_for_status()
        return [d["embedding"] for d in r.json()["data"]]  # TEI OpenAI-compatible route
