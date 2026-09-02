from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    website_id: str
    organization_id: str
    chunk_index: int
    content: str
    token_count: int
    created_at: datetime


class ProcessEmbeddingsRequest(BaseModel):
    chunk_size: int = Field(default=800, ge=100, le=4000, description="Max characters per chunk")
    chunk_overlap: int = Field(default=150, ge=0, le=1000, description="Overlapping characters between chunks")
    re_embed_all: bool = Field(default=False, description="Whether to re-chunk and re-embed already processed documents")


class ProcessEmbeddingsResponse(BaseModel):
    website_id: str
    documents_processed: int
    chunks_created: int
    total_tokens: int


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language search query")
    website_id: Optional[str] = Field(default=None, description="Optional website filter")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum cosine similarity score threshold")


class SearchResultItemResponse(BaseModel):
    chunk_id: str
    document_id: str
    website_id: str
    url: str
    title: str
    content: str
    similarity_score: float
    chunk_index: int
    token_count: int


class SemanticSearchResponse(BaseModel):
    query: str
    results_count: int
    results: List[SearchResultItemResponse]


class VectorStatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_tokens: int
    embedded_documents_count: int
