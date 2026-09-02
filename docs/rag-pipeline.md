# RAG Pipeline: Text Processing, Chunking, Embeddings & Semantic Search (Phase 4)

The **AI Customer & Commerce Assistant** RAG (Retrieval-Augmented Generation) subsystem transforms raw crawled web pages into semantically searchable vector chunks stored in PostgreSQL (`pgvector`), empowering the chatbot to answer customer queries with accurate, domain-specific context.

---

## 1. End-to-End RAG Architecture

```
[ Knowledge Documents ] (Raw HTML / Articles from Crawler)
          │
          ▼
   [ Text Cleaner ] ──── (Normalizes unicode, strips markdown noise, cleans whitespace)
          │
          ▼
[ Document Chunker ] ─── (Sliding-window splitting: 800 chars, 150 overlap along boundaries)
          │
          ▼
[ Embedding Service ] ── (Local Ollama nomic-embed-text: 768 dimensions)
          │
          ▼
[ pgvector Storage ] ─── (PostgreSQL document_chunks table with HNSW Cosine Index)
          │
          ▼
[ Semantic Search ] ──── (Tenant-isolated Cosine Similarity: 1 - (embedding <=> query_vec))
```

---

## 2. Text Cleaning (`TextCleaner`)

- **Unicode Normalization**: Canonical NFKC normalization, strips zero-width and non-breaking space characters.
- **Markdown Stripping**: Removes markdown link targets (`[Text](url)` -> `Text`), image artifacts, and raw header symbols while preserving text structure.
- **Whitespace Sanitation**: Collapses multiple blank lines and repetitive whitespace into clean paragraph breaks.

---

## 3. Semantic Chunking (`DocumentChunker`)

- **Parameters**: `chunk_size` = 800 characters (~200 tokens), `chunk_overlap` = 150 characters (~40 tokens).
- **Boundary Splitting**:
  1. Paragraph boundaries (`\n\n`) first.
  2. Sentence boundaries (`(?<=[.!?])\s+`) for paragraphs exceeding `chunk_size`.
  3. Word boundaries (`\s+`) for long unbroken sentences.
- **Token Estimation**: Approximately `len(words) * 1.33`.

---

## 4. Local Embedding Generation (`EmbeddingService`)

- **Default Model**: `nomic-embed-text` (768 dimensions) via local Ollama (`http://localhost:11434/api/embeddings`).
- **Normalized Vectors**: L2-normalized float arrays (`sqrt(sum(v_i^2)) == 1.0`).
- **Offline / Test Deterministic Fallback**: Includes deterministic harmonic pseudo-embedding generator ensuring automated unit tests run completely offline and in-memory with reliable cosine similarity rankings.

---

## 5. Vector Storage & `pgvector` Schema

### `document_chunks` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `VARCHAR(36)` (PK) | Unique chunk UUID |
| `document_id` | `VARCHAR(36)` (FK) | Reference to `knowledge_documents.id` (CASCADE) |
| `website_id` | `VARCHAR(36)` (FK) | Reference to `websites.id` (CASCADE) |
| `organization_id` | `VARCHAR(36)` (FK) | Reference to `organizations.id` (CASCADE) |
| `chunk_index` | `INTEGER` | Sequential chunk index within the document |
| `content` | `TEXT` | Sanitized chunk text |
| `token_count` | `INTEGER` | Estimated LLM token count |
| `embedding` | `vector(768)` | pgvector 768-dimensional float embedding |
| `metadata_json` | `TEXT` | JSON metadata storing URL, title, and section headers |

### HNSW Cosine Index
```sql
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_cosine 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops);
```

---

## 6. Semantic Search & Similarity Ranking

### PostgreSQL `pgvector` Query
```sql
SELECT document_chunks.*, knowledge_documents.url, knowledge_documents.title,
       (1 - (document_chunks.embedding <=> :query_vector)) AS similarity
FROM document_chunks
JOIN knowledge_documents ON document_chunks.document_id = knowledge_documents.id
WHERE document_chunks.organization_id = :org_id
  AND (:website_id IS NULL OR document_chunks.website_id = :website_id)
ORDER BY document_chunks.embedding <=> :query_vector ASC
LIMIT :top_k;
```

---

## 7. REST API Reference (`/api/v1/knowledge`)

| Method | Endpoint | Description | Min Role |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/knowledge/websites/{id}/process-embeddings` | Chunk and embed all documents for a website | `ADMIN` |
| `POST` | `/api/v1/knowledge/documents/{id}/chunk-and-embed` | Chunk and embed a single document | `ADMIN` |
| `POST` | `/api/v1/knowledge/search` | Execute natural language semantic search | `VIEWER` |
| `GET` | `/api/v1/knowledge/websites/{id}/chunks` | List all vector chunks for a website | `VIEWER` |
| `GET` | `/api/v1/knowledge/stats` | Retrieve organization vector database stats | `VIEWER` |
