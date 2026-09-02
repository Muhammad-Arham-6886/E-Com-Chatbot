import json
import math
import re
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.crawling import KnowledgeDocument
from app.services.rag.embedding_service import EmbeddingService


class SearchResultItem:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        website_id: str,
        url: str,
        title: str,
        content: str,
        similarity_score: float,
        chunk_index: int,
        token_count: int,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.website_id = website_id
        self.url = url
        self.title = title
        self.content = content
        self.similarity_score = similarity_score
        self.chunk_index = chunk_index
        self.token_count = token_count

    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "website_id": self.website_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "similarity_score": round(self.similarity_score, 4),
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
        }


class VectorSearchService:
    def __init__(self, db: AsyncSession, embedding_service: Optional[EmbeddingService] = None):
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _is_boilerplate(content: str) -> bool:
        """Check if a chunk is navigation/boilerplate content."""
        content = content.strip()
        # Very short chunks are likely labels
        if len(content) < 20:
            return True
        # Single word
        words = content.split()
        if len(words) < 3:
            return True
        return False

    @staticmethod
    def _keyword_overlap_score(chunk: str, query: str) -> float:
        """Boost score based on keyword overlap between chunk and query."""
        stop_words = {
            "i", "me", "my", "we", "our", "you", "your", "it", "its",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "do", "does", "did", "have", "has", "had", "can", "could",
            "will", "would", "should", "may", "might", "shall",
            "what", "which", "who", "how", "when", "where", "why",
            "in", "on", "at", "to", "for", "of", "with", "by", "from",
        }
        query_words = {w.lower() for w in query.split() if len(w) > 2 and w.lower() not in stop_words}
        chunk_lower = chunk.lower()

        if not query_words:
            return 0.0

        matched = sum(1 for w in query_words if w in chunk_lower)
        return matched / len(query_words) if query_words else 0.0

    async def search(
        self,
        query: str,
        org_id: str,
        website_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> List[SearchResultItem]:
        if not query.strip():
            return []

        query_vector = await self.embedding_service.get_embedding(query)

        try:
            bind = self.db.get_bind()
            dialect_name = bind.dialect.name if bind else "postgresql"
        except Exception:
            dialect_name = "postgresql" if not getattr(self.db, "_is_async", False) else "sqlite"

        filters = [DocumentChunk.organization_id == org_id]
        if website_id:
            filters.append(DocumentChunk.website_id == website_id)

        if dialect_name == "postgresql":
            # Fetch more candidates for re-ranking
            fetch_k = top_k * 3
            stmt = (
                select(
                    DocumentChunk,
                    KnowledgeDocument.url,
                    KnowledgeDocument.title,
                    (1 - DocumentChunk.embedding.cosine_distance(query_vector)).label("similarity"),
                )
                .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
                .where(and_(*filters))
                .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
                .limit(fetch_k)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            # Re-rank: combine vector similarity with keyword overlap
            re_ranked = []
            for chunk, url, title, similarity in rows:
                vec_score = float(similarity) if similarity is not None else 0.0
                if vec_score < min_similarity:
                    continue
                if self._is_boilerplate(chunk.content):
                    continue

                kw_score = self._keyword_overlap_score(chunk.content, query)
                # Combined score: 30% vector similarity + 70% keyword match
                # (Keywords are more reliable than random deterministic embeddings)
                combined = (vec_score * 0.3) + (kw_score * 0.7)

                re_ranked.append((combined, SearchResultItem(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    website_id=chunk.website_id,
                    url=url,
                    title=title,
                    content=chunk.content,
                    similarity_score=vec_score,
                    chunk_index=chunk.chunk_index,
                    token_count=chunk.token_count,
                )))

            re_ranked.sort(key=lambda x: x[0], reverse=True)
            return [item for _, item in re_ranked[:top_k]]

        else:
            # SQLite / Test mode
            stmt = (
                select(
                    DocumentChunk,
                    KnowledgeDocument.url,
                    KnowledgeDocument.title,
                )
                .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
                .where(and_(*filters))
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            scored_items = []
            for chunk, url, title in rows:
                chunk_emb = chunk.embedding
                if isinstance(chunk_emb, str):
                    try:
                        chunk_emb = json.loads(chunk_emb)
                    except Exception:
                        chunk_emb = []

                vec_score = self._cosine_similarity(query_vector, chunk_emb) if chunk_emb else 0.0
                if vec_score < min_similarity:
                    continue
                if self._is_boilerplate(chunk.content):
                    continue

                kw_score = self._keyword_overlap_score(chunk.content, query)
                combined = (vec_score * 0.3) + (kw_score * 0.7)

                scored_items.append((combined, SearchResultItem(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    website_id=chunk.website_id,
                    url=url,
                    title=title,
                    content=chunk.content,
                    similarity_score=vec_score,
                    chunk_index=chunk.chunk_index,
                    token_count=chunk.token_count,
                )))

            scored_items.sort(key=lambda x: x[0], reverse=True)
            return [item for _, item in scored_items[:top_k]]
