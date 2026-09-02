import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.chunk import DocumentChunk
from app.models.crawling import KnowledgeDocument
from app.models.enums import DocumentStatusEnum, RoleEnum
from app.models.user import User
from app.models.website import Website
from app.schemas.rag import (
    ChunkResponse,
    ProcessEmbeddingsRequest,
    ProcessEmbeddingsResponse,
    SemanticSearchRequest,
    SearchResultItemResponse,
    SemanticSearchResponse,
    VectorStatsResponse,
)
from app.services.org_service import OrganizationService
from app.services.rag.chunker import DocumentChunker
from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.vector_search import VectorSearchService
from app.services.website_service import WebsiteService

router = APIRouter(prefix="/knowledge", tags=["RAG & Semantic Search"])


async def verify_org_access(
    db: AsyncSession, org_id: str, user_id: str, min_role: RoleEnum = RoleEnum.VIEWER
):
    member = await OrganizationService.get_member(db, org_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization.",
        )
    if not member.role.has_permission(min_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action requires at least '{min_role.value}' role, but your role is '{member.role.value}'.",
        )
    return member


@router.post(
    "/websites/{website_id}/process-embeddings",
    response_model=ProcessEmbeddingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Chunk and generate vector embeddings for website knowledge documents",
)
async def process_website_embeddings(
    website_id: str,
    data: ProcessEmbeddingsRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.ADMIN)
    website = await WebsiteService.get_website(db, website_id, org_id)

    # 1. Fetch documents
    doc_filter = [
        KnowledgeDocument.website_id == website.id,
        KnowledgeDocument.organization_id == org_id,
    ]
    if not data.re_embed_all:
        doc_filter.append(KnowledgeDocument.status != DocumentStatusEnum.PROCESSED)

    doc_stmt = select(KnowledgeDocument).where(and_(*doc_filter))
    documents = (await db.execute(doc_stmt)).scalars().all()

    if not documents:
        # Check total existing chunks
        chunk_count_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.website_id == website.id)
        total_chunks = (await db.execute(chunk_count_stmt)).scalar() or 0
        return ProcessEmbeddingsResponse(
            website_id=website.id,
            documents_processed=0,
            chunks_created=total_chunks,
            total_tokens=0,
        )

    chunker = DocumentChunker(chunk_size=data.chunk_size, chunk_overlap=data.chunk_overlap)
    embedding_service = EmbeddingService()

    total_chunks_created = 0
    total_tokens_computed = 0

    for doc in documents:
        # If re-embedding, clear existing chunks for this doc
        if data.re_embed_all:
            del_stmt = delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            await db.execute(del_stmt)

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
                website_id=website.id,
                organization_id=org_id,
                chunk_index=ci.chunk_index,
                content=ci.content,
                token_count=ci.token_count,
                embedding=emb,
                metadata_json=json.dumps(metadata),
            )
            db.add(new_chunk)
            total_chunks_created += 1
            total_tokens_computed += ci.token_count

        doc.status = DocumentStatusEnum.PROCESSED

    await db.commit()

    return ProcessEmbeddingsResponse(
        website_id=website.id,
        documents_processed=len(documents),
        chunks_created=total_chunks_created,
        total_tokens=total_tokens_computed,
    )


@router.post(
    "/documents/{document_id}/chunk-and-embed",
    response_model=ProcessEmbeddingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Chunk and embed a single knowledge document",
)
async def process_single_document_embedding(
    document_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.ADMIN)

    doc_stmt = select(KnowledgeDocument).where(
        and_(KnowledgeDocument.id == document_id, KnowledgeDocument.organization_id == org_id)
    )
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Delete existing chunks for this document
    del_stmt = delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    await db.execute(del_stmt)

    chunker = DocumentChunker()
    embedding_service = EmbeddingService()
    chunk_items = chunker.chunk_document(doc.raw_content)

    total_tokens = 0
    if chunk_items:
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
                website_id=doc.website_id,
                organization_id=org_id,
                chunk_index=ci.chunk_index,
                content=ci.content,
                token_count=ci.token_count,
                embedding=emb,
                metadata_json=json.dumps(metadata),
            )
            db.add(new_chunk)
            total_tokens += ci.token_count

    doc.status = DocumentStatusEnum.PROCESSED
    await db.commit()

    return ProcessEmbeddingsResponse(
        website_id=doc.website_id,
        documents_processed=1,
        chunks_created=len(chunk_items),
        total_tokens=total_tokens,
    )


@router.post(
    "/search",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute semantic vector search with cosine similarity ranking",
)
async def semantic_search(
    data: SemanticSearchRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.VIEWER)

    search_engine = VectorSearchService(db)
    results = await search_engine.search(
        query=data.query,
        org_id=org_id,
        website_id=data.website_id,
        top_k=data.top_k,
        min_similarity=data.min_similarity,
    )

    items = [
        SearchResultItemResponse(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            website_id=r.website_id,
            url=r.url,
            title=r.title,
            content=r.content,
            similarity_score=r.similarity_score,
            chunk_index=r.chunk_index,
            token_count=r.token_count,
        )
        for r in results
    ]

    return SemanticSearchResponse(
        query=data.query,
        results_count=len(items),
        results=items,
    )


@router.get(
    "/websites/{website_id}/chunks",
    response_model=List[ChunkResponse],
    status_code=status.HTTP_200_OK,
    summary="List all generated chunks for a website",
)
async def list_website_chunks(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.VIEWER)

    stmt = (
        select(DocumentChunk)
        .where(and_(DocumentChunk.website_id == website_id, DocumentChunk.organization_id == org_id))
        .order_by(desc(DocumentChunk.created_at))
        .limit(200)
    )
    chunks = (await db.execute(stmt)).scalars().all()
    return list(chunks)


@router.get(
    "/stats",
    response_model=VectorStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get organization knowledge base and vector embedding statistics",
)
async def get_knowledge_stats(
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.VIEWER)

    doc_count_stmt = select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.organization_id == org_id)
    total_docs = (await db.execute(doc_count_stmt)).scalar() or 0

    chunk_count_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.organization_id == org_id)
    total_chunks = (await db.execute(chunk_count_stmt)).scalar() or 0

    token_sum_stmt = select(func.sum(DocumentChunk.token_count)).where(DocumentChunk.organization_id == org_id)
    total_tokens = (await db.execute(token_sum_stmt)).scalar() or 0

    embedded_docs_stmt = select(func.count(KnowledgeDocument.id)).where(
        and_(
            KnowledgeDocument.organization_id == org_id,
            KnowledgeDocument.status == DocumentStatusEnum.PROCESSED,
        )
    )
    embedded_docs = (await db.execute(embedded_docs_stmt)).scalar() or 0

    return VectorStatsResponse(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_tokens=int(total_tokens),
        embedded_documents_count=embedded_docs,
    )
