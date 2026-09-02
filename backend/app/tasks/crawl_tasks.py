import asyncio
import json
import logging
import threading
from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.crawler.crawler_engine import CrawlerEngine
from app.models.crawling import KnowledgeDocument
from app.models.enums import DocumentStatusEnum
from sqlalchemy import select, and_

logger = logging.getLogger("ai_commerce_saas.crawler")


async def _auto_embed_documents(website_id: str, organization_id: str):
    """After crawl, automatically chunk and embed all RAW documents."""
    from app.services.rag.chunker import DocumentChunker
    from app.services.rag.embedding_service import EmbeddingService
    from app.models.chunk import DocumentChunk

    async with AsyncSessionLocal() as db:
        stmt = select(KnowledgeDocument).where(
            and_(
                KnowledgeDocument.website_id == website_id,
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.status == DocumentStatusEnum.RAW,
            )
        )
        documents = (await db.execute(stmt)).scalars().all()
        if not documents:
            return

        chunker = DocumentChunker(chunk_size=800, chunk_overlap=150)
        embedding_service = EmbeddingService()

        total_chunks = 0
        for doc in documents:
            chunk_items = chunker.chunk_document(doc.raw_content)
            if not chunk_items:
                continue

            chunk_texts = [ci.content for ci in chunk_items]
            embeddings = await embedding_service.get_batch_embeddings(chunk_texts)

            for ci, emb in zip(chunk_items, embeddings):
                metadata = {
                    "url": doc.url,
                    "title": doc.title,
                    "meta_description": doc.meta_description,
                }
                new_chunk = DocumentChunk(
                    document_id=doc.id,
                    website_id=website_id,
                    organization_id=organization_id,
                    chunk_index=ci.chunk_index,
                    content=ci.content,
                    token_count=ci.token_count,
                    embedding=emb,
                    metadata_json=json.dumps(metadata),
                )
                db.add(new_chunk)
                total_chunks += 1

            doc.status = DocumentStatusEnum.PROCESSED

        await db.commit()
        logger.info(
            f"Auto-embedded {total_chunks} chunks from {len(documents)} documents for website {website_id}"
        )


def _run_async_safely(coro):
    """Run an async coroutine safely, handling the case where an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're inside a running event loop (e.g. FastAPI handler with task_always_eager).
        # Run asyncio.run() in a separate thread with its own event loop.
        result = [None]
        exception = [None]

        def _target():
            try:
                result[0] = asyncio.run(coro)
            except Exception as e:
                exception[0] = e

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join(timeout=300)  # 5 min max
        if t.is_alive():
            raise TimeoutError("Async crawl execution timed out after 300 seconds")
        if exception[0] is not None:
            raise exception[0]
        return result[0]
    else:
        return asyncio.run(coro)


@celery_app.task(name="app.tasks.crawl_tasks.run_crawl_job")
def run_crawl_job(crawl_job_id: str):
    """Celery task entrypoint to execute a website crawling job asynchronously."""
    logger.info(f"Starting Celery background crawl task for job ID: {crawl_job_id}")

    async def _runner():
        async with AsyncSessionLocal() as session:
            engine = CrawlerEngine(session, crawl_job_id)
            job = await engine.execute()

            # Auto-embed after successful crawl
            if job.status.value == "COMPLETED":
                await _auto_embed_documents(job.website_id, job.organization_id)

    try:
        _run_async_safely(_runner())
        logger.info(f"Successfully finished background crawl task for job ID: {crawl_job_id}")
    except Exception as e:
        logger.error(f"Error during background crawl task for job ID {crawl_job_id}: {e}", exc_info=True)
        raise e
