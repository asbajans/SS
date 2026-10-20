"""Document ingestion: extract -> chunk -> embed (TEI)."""
import asyncio
import io
import re

import structlog
from celery import shared_task
from pypdf import PdfReader
from sqlalchemy import delete

from app import storage
from app.db import AsyncSessionLocal
from app.embeddings import embed_texts
from app.models import Document, DocumentChunk

log = structlog.get_logger(__name__)

CHUNK_CHARS = 1200
OVERLAP = 150


def extract_text(filename: str, raw: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return raw.decode("utf-8", errors="replace")


def chunk_text(text: str) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - OVERLAP
    return chunks


@shared_task(name="ingest.document", max_retries=1)
def ingest_document(document_id: str) -> dict:
    return asyncio.run(_ingest(document_id))


async def _ingest(document_id: str) -> dict:
    async with AsyncSessionLocal() as s:
        doc = await s.get(Document, document_id)
        if doc is None:
            return {"status": "missing"}
        raw = await storage.get_bytes(doc.minio_key)
        text = extract_text(doc.filename, raw)
        chunks = chunk_text(text)
        if not chunks:
            log.warning("ingest_empty", document_id=document_id, filename=doc.filename)
            return {"status": "empty", "chunks": 0}
        vectors = await embed_texts(chunks)
        await s.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        for idx, (content, emb) in enumerate(zip(chunks, vectors, strict=False)):
            s.add(
                DocumentChunk(
                    document_id=doc.id,
                    project_id=doc.project_id,
                    chunk_idx=idx,
                    content=content,
                    embedding=emb,
                )
            )
        await s.commit()
        log.info("ingest_done", document_id=document_id, chunks=len(chunks))
        return {"status": "ok", "chunks": len(chunks)}
