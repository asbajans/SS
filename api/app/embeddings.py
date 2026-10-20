"""TEI embedding client (local, no external calls)."""
import httpx

from app.config import settings


async def embed_texts(texts: list[str], batch_size: int = 8) -> list[list[float]]:
    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=180) as client:
        for i in range(0, len(texts), batch_size):
            batch = [t[:8000] for t in texts[i : i + batch_size]]
            resp = await client.post(f"{settings.tei_url}/embed", json={"inputs": batch})
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                data = data.get("embeddings", data.get("data", []))
            vectors.extend(data)
    return vectors


async def embed_query(text: str) -> list[float]:
    vecs = await embed_texts([text], batch_size=1)
    return vecs[0] if vecs else []
