# Local LLM, RAG Grounding & Tool Selection Engine (Phase 5)

The **AI Customer & Commerce Assistant** conversation engine bridges local Large Language Models (running via Ollama) with the multi-tenant `pgvector` knowledge base and decoupled commerce provider tools.

---

## 1. Core Architecture Principles

### Principle 1: Retrieval Grounding (Anti-Hallucination)
> **The Local LLM is NOT responsible for knowing or memorizing the website.**
> The `pgvector` semantic retrieval system supplies verified factual context chunks. The LLM only synthesizes and formats conversational responses based on injected context.

### Principle 2: Tool Selection vs Commerce Execution
> **The Local LLM does NOT execute database writes or WooCommerce transactions directly.**
> The LLM acts as an intent classifier and tool selector (`ToolSelectionEngine`), dispatching parameters to a secure, sandboxed `CommerceProvider`.

---

## 2. Interaction & Execution Workflow

```
[ Visitor Query ]
       │
       ▼
[ Tool Selection Engine ]
       ├─▶ Intent: ESCALATE_HUMAN ─────▶ Generates WhatsApp Direct Action Button
       │
       ├─▶ Intent: SEARCH_PRODUCT ─────▶ CommerceProvider.search_products() ──▶ Returns Product Cards
       │
       ├─▶ Intent: ADD_TO_CART ────────▶ CommerceProvider.get_add_to_cart_url() ──▶ Returns Cart URL
       │
       └─▶ Intent: KNOWLEDGE_INQUIRY ──▶ VectorSearchService.search() (pgvector)
                                                 │
                                                 ▼
                                     [ Grounded System Prompt Assembly ]
                                                 │
                                                 ▼
                                     [ Local LLM (Ollama / llama3.2) ]
                                                 │
                                                 ▼
                                     [ ChatMessage + Source Citations ]
```

---

## 3. Grounded System Prompt Template

```text
You are the official AI Assistant for '{website.name}' ({website.domain}).
Your duty is to answer customer questions politely, accurately, and truthfully using ONLY the provided website context below.

STRICT RULES:
1. Answer ONLY based on the facts provided in the Context below.
2. If the context does not contain enough information to answer the question, politely say you do not have that verified information and offer to connect with human support.
3. Never hallucinate policies, pricing, dates, or specifications.
4. Keep your answer concise, polite, and helpful.

Store Specific Guidelines:
{website.settings.custom_instructions}

=== VERIFIED WEBSITE CONTEXT ===
{retrieved_chunks}
================================
```

---

## 4. Tool & Intent Classification Matrix

| Tool Intent | Trigger Pattern | Action Taken |
| :--- | :--- | :--- |
| `KNOWLEDGE_INQUIRY` | General questions, shipping, returns, store hours, policies | Cosine vector search on `document_chunks` + grounded LLM response with source links |
| `SEARCH_PRODUCT` | "Show me keyboards", "Do you sell headphones?" | Queries `CommerceProvider` catalog and returns interactive `product_card` widgets |
| `ADD_TO_CART` | "Add this to my cart", "Buy now" | Generates direct checkout / add-to-cart action link |
| `ESCALATE_HUMAN` | "Speak to agent", "WhatsApp", "Human support" | Attaches direct WhatsApp chat button (`https://wa.me/{number}`) |

---

## 5. REST API Endpoints (`/api/v1/chat`)

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/chat/sessions` | Initialize a visitor chat session (generates `session_token`) | Public / Internal |
| `POST` | `/api/v1/chat/message` | Send message, run RAG + Tool selection + LLM, return reply with sources & actions | Public (`session_token`) |
| `GET` | `/api/v1/chat/sessions/{session_id}/messages` | Retrieve conversation history | Public / Internal |
| `POST` | `/api/v1/chat/test-rag` | Dashboard RAG test tool showing debug chunks, system prompt, and tool classifier | Authenticated (`ADMIN`+) |
