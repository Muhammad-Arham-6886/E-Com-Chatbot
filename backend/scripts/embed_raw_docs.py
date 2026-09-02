"""One-time script: chunk and embed all RAW documents using deterministic fallback."""
import asyncio
import json
import uuid
import sys
sys.path.insert(0, ".")

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.crawling import KnowledgeDocument
from app.models.chunk import DocumentChunk
from app.models.enums import DocumentStatusEnum
from app.services.rag.chunker import DocumentChunker
from app.services.rag.embedding_service import EmbeddingService
from app.core.config import settings


async def main():
    embedding_service = EmbeddingService()
    dimensions = settings.EMBEDDING_DIMENSIONS

    async with AsyncSessionLocal() as db:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.status == DocumentStatusEnum.RAW
        )
        documents = (await db.execute(stmt)).scalars().all()
        print(f"Found {len(documents)} RAW documents to process")

        if not documents:
            print("Nothing to do.")
            return

        chunker = DocumentChunker(chunk_size=800, chunk_overlap=150)
        total_chunks = 0

        for i, doc in enumerate(documents):
            print(f"  [{i+1}/{len(documents)}] {doc.url[:80]} ({doc.token_count} tokens)")

            if not doc.raw_content or len(doc.raw_content.strip()) < 20:
                print(f"    -> Skipped (too short)")
                continue

            chunk_items = chunker.chunk_document(doc.raw_content)
            if not chunk_items:
                print(f"    -> Skipped (no chunks)")
                continue

            for ci in chunk_items:
                emb = embedding_service.generate_deterministic_embedding(ci.content, dimensions)
                metadata = {
                    "url": doc.url,
                    "title": doc.title,
                    "meta_description": doc.meta_description,
                }
                new_chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    website_id=doc.website_id,
                    organization_id=doc.organization_id,
                    chunk_index=ci.chunk_index,
                    content=ci.content,
                    token_count=ci.token_count,
                    embedding=emb,
                    metadata_json=json.dumps(metadata),
                )
                db.add(new_chunk)
                total_chunks += 1

            doc.status = DocumentStatusEnum.PROCESSED
            print(f"    -> {len(chunk_items)} chunks created")

        await db.commit()
        print(f"\nDone! Created {total_chunks} chunks from {len(documents)} documents.")

        count_stmt = select(DocumentChunk)
        all_chunks = (await db.execute(count_stmt)).scalars().all()
        print(f"Total chunks in DB: {len(all_chunks)}")


if __name__ == "__main__":
    asyncio.run(main())
