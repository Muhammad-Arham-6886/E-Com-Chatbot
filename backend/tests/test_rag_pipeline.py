import math
import pytest
from httpx import AsyncClient
from app.models.crawling import KnowledgeDocument
from app.models.chunk import DocumentChunk
from app.models.enums import DocumentStatusEnum
from app.services.rag.text_cleaner import TextCleaner
from app.services.rag.chunker import DocumentChunker
from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.vector_search import VectorSearchService


def test_text_cleaner_normalizes_and_strips_noise():
    raw_markdown = """
    # Welcome to Store Concierge

    We offer **fast shipping** and *reliable service* across North America.
    Check our [Return Policy](https://store.com/returns) for details.
    ![Store Banner](https://store.com/banner.jpg)

    ### Payment Methods
    We accept all major credit cards and Apple Pay.
    """

    cleaned = TextCleaner.clean(raw_markdown)
    assert "#" not in cleaned
    assert "**" not in cleaned
    assert "https://store.com/returns" not in cleaned
    assert "Return Policy" in cleaned
    assert "banner.jpg" not in cleaned
    assert "We offer fast shipping" in cleaned
    assert "Payment Methods" in cleaned


def test_document_chunker_sliding_window_and_boundaries():
    sample_text = """
    Section 1: Our Return Policy allows returns within 30 calendar days of receipt.
    Items must be in original condition with tags attached.
    Refunds are processed to the original payment method within 5-7 business days.

    Section 2: Shipping and Delivery takes 2-4 business days for standard ground shipping.
    Expedited overnight shipping is available at checkout for an additional fee.
    Tracking numbers are emailed once the package leaves our warehouse.

    Section 3: Warranty Information covers all hardware products against defects for 1 year.
    Accidental damage is not covered under the standard warranty.
    """

    chunker = DocumentChunker(chunk_size=200, chunk_overlap=40)
    chunks = chunker.chunk_document(sample_text)

    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk.content) > 0
        assert chunk.token_count > 0
        assert chunk.chunk_index >= 0


def test_embedding_service_dimensions_and_deterministic_fallback():
    emb_service = EmbeddingService(dimensions=768)

    text_a = "Return and refund policy for damaged merchandise"
    text_b = "How to return an item and get a full refund"
    text_c = "Aerospace jet turbine engineering specifications"

    vec_a = EmbeddingService.generate_deterministic_embedding(text_a, dimensions=768)
    vec_b = EmbeddingService.generate_deterministic_embedding(text_b, dimensions=768)
    vec_c = EmbeddingService.generate_deterministic_embedding(text_c, dimensions=768)

    assert len(vec_a) == 768
    assert len(vec_b) == 768
    assert len(vec_c) == 768

    # Verify L2 normalization: norm ≈ 1.0
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    assert abs(norm_a - 1.0) < 1e-4

    # Calculate cosine similarities
    def cosine(u, v):
        return sum(x * y for x, y in zip(u, v))

    sim_related = cosine(vec_a, vec_b)
    sim_unrelated = cosine(vec_a, vec_c)

    # text_a and text_b share terms ("return", "refund") and should score significantly higher than unrelated text_c
    assert sim_related > sim_unrelated


@pytest.mark.asyncio
async def test_vector_search_cosine_ranking(client: AsyncClient, create_test_user, create_test_org, db_session):
    user, token = await create_test_user("rag_user@example.com")
    org = await create_test_org("RAG Org", user)

    # 1. Create website
    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "RAG Store", "url": "https://ragstore.com"},
    )
    website_id = site_res.json()["id"]

    # 2. Insert Knowledge Documents
    doc1 = KnowledgeDocument(
        website_id=website_id,
        organization_id=org.id,
        url="https://ragstore.com/returns",
        title="Return & Refund Policy",
        raw_content="All returns must be made within 30 days of purchase with original receipt for a full refund.",
        content_hash="hash_returns_123",
        token_count=25,
        status=DocumentStatusEnum.RAW,
    )
    doc2 = KnowledgeDocument(
        website_id=website_id,
        organization_id=org.id,
        url="https://ragstore.com/shipping",
        title="Shipping Rates & Times",
        raw_content="Standard ground shipping takes 3-5 business days. Free shipping on orders over $50.",
        content_hash="hash_shipping_123",
        token_count=20,
        status=DocumentStatusEnum.RAW,
    )
    db_session.add_all([doc1, doc2])
    await db_session.commit()
    await db_session.refresh(doc1)
    await db_session.refresh(doc2)

    # 3. Trigger /process-embeddings API endpoint
    process_res = await client.post(
        f"/api/v1/knowledge/websites/{website_id}/process-embeddings?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"chunk_size": 500, "chunk_overlap": 50, "re_embed_all": True},
    )
    assert process_res.status_code == 200
    data = process_res.json()
    assert data["documents_processed"] == 2
    assert data["chunks_created"] >= 2

    # 4. Perform Semantic Search for "return policy refund"
    search_res = await client.post(
        f"/api/v1/knowledge/search?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "How do I get a refund or return an item?", "top_k": 3},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["results_count"] >= 1
    top_hit = search_data["results"][0]
    assert "Return & Refund Policy" in top_hit["title"]
    assert top_hit["similarity_score"] > 0.0


@pytest.mark.asyncio
async def test_multi_tenant_vector_isolation(client: AsyncClient, create_test_user, create_test_org, db_session):
    # Org A
    user_a, token_a = await create_test_user("user_org_a@example.com")
    org_a = await create_test_org("Organization A", user_a)

    # Org B
    user_b, token_b = await create_test_user("user_org_b@example.com")
    org_b = await create_test_org("Organization B", user_b)

    # Create website for Org A with confidential text
    site_a = await client.post(
        f"/api/v1/websites?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Secret Org A Site", "url": "https://secret-a.com"},
    )
    site_a_id = site_a.json()["id"]

    doc_a = KnowledgeDocument(
        website_id=site_a_id,
        organization_id=org_a.id,
        url="https://secret-a.com/classified",
        title="Top Secret Strategy",
        raw_content="Project Blue Sky confidential roadmap and internal revenue figures for 2026.",
        content_hash="hash_secret_a",
        token_count=30,
        status=DocumentStatusEnum.RAW,
    )
    db_session.add(doc_a)
    await db_session.commit()

    # Process embeddings for Org A
    await client.post(
        f"/api/v1/knowledge/websites/{site_a_id}/process-embeddings?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"re_embed_all": True},
    )

    # Org B searches for Org A's confidential topic
    search_b = await client.post(
        f"/api/v1/knowledge/search?org_id={org_b.id}",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"query": "Project Blue Sky confidential roadmap"},
    )
    assert search_b.status_code == 200
    b_data = search_b.json()
    # Org B must get ZERO results because chunks belong to Org A
    assert b_data["results_count"] == 0

    # Cross-tenant direct stats access check
    stats_b = await client.get(
        f"/api/v1/knowledge/stats?org_id={org_b.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert stats_b.status_code == 200
    assert stats_b.json()["total_chunks"] == 0
