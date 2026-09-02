# Production Deployment & Docker Orchestration Guide (Phase 14)

This guide details the complete production architecture, container topology, environment configuration, SSL termination, and maintenance procedures for the **AI Commerce Assistant SaaS Platform**.

---

## 1. Multi-Container Production Architecture

```
                                  [ Internet / Visitors ]
                                             │
                                             ▼
                        ┌────────────────────────────────────────┐
                        │      Nginx Reverse Proxy (Port 80/443) │
                        └────────────────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
      [ /api/*, /static/* ]                                     [ /* ]
  ┌───────────────────────────────┐               ┌───────────────────────────────┐
  │  FastAPI Backend (Port 8000)  │               │   Next.js 14 Standalone (3000)│
  │  Multi-Worker (Gunicorn/Uvic) │               │   Optimized Production Image  │
  └──────────────┬────────────────┘               └───────────────────────────────┘
                 │
                 ├──▶ [ PostgreSQL 16 + pgvector (768-d Vectors) ]
                 ├──▶ [ Redis 7 (Cache, Session Store & Broker) ]
                 └──▶ [ Local Ollama Engine (Qwen2.5 / Nomic-Embed) ]
```

---

## 2. Container Inventory & Specifications

| Container Service | Image | Role | Memory Limit |
| :--- | :--- | :--- | :--- |
| `postgres` | `pgvector/pgvector:pg16` | Relational multi-tenant database & 768-d vector store | 2 GB |
| `redis` | `redis:7-alpine` | High-speed cache, rate limiter, and message broker | 1 GB |
| `ollama` | `ollama/ollama:latest` | Local LLM inference (`qwen2.5:1.5b`) & embeddings (`nomic-embed-text`) | GPU / 4 GB |
| `backend` | `Dockerfile` (Python 3.12 slim) | REST API, RAG Engine, SSRF Crawler, Auth & Billing | 2 GB |
| `frontend` | `Dockerfile` (Node.js 20 Alpine) | Next.js 14 Dashboard & Analytics UI | 1 GB |
| `nginx` | `Dockerfile` (Alpine) | Reverse proxy, static caching, CORS & SSL termination | 512 MB |

---

## 3. One-Click Production Deployment

### Step 1: Clone Repository & Configure Environment
```bash
cp .env.example .env
nano .env  # Configure POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY, and DOMAIN
```

### Step 2: Execute Automated Deployer
- **On Linux / macOS**:
  ```bash
  chmod +x scripts/deploy.sh
  ./scripts/deploy.sh
  ```
- **On Windows PowerShell**:
  ```powershell
  .\scripts\deploy.ps1
  ```

---

## 4. Health Check & Diagnostics

Check overall cluster readiness:
```bash
curl -f http://localhost:8000/api/v1/ready
```
**Response**:
```json
{
  "status": "ready",
  "components": {
    "database": "connected",
    "pgvector_extension": "installed_and_active",
    "ollama_service": "connected"
  }
}
```
