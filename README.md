# AI Customer & Commerce Assistant SaaS Platform

An enterprise-grade, multi-tenant SaaS platform that empowers businesses to index their websites, build AI knowledge bases, and provide intelligent customer service and commerce assistance (WooCommerce & Shopify) via embeddable chat widgets.

## Features (Phase 1 Implemented)
- **Multi-Tenant Architecture**: Strict organization-scoped data isolation across all database queries and endpoints.
- **Authentication & RBAC**: JWT Bearer token authentication with password hashing (Bcrypt) and granular role-based access control (`OWNER`, `ADMIN`, `MANAGER`, `AGENT`, `VIEWER`).
- **Organization & Team Management**: Multi-tenant workspace switcher, member invites by email, role assignments, and member management.
- **SaaS Dashboard Shell**: Modern Next.js 14 App Router dashboard with responsive sidebar, top navbar, metrics overview, and settings.
- **Enterprise Tech Stack**: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16 (pgvector), Celery, Redis, Next.js, Tailwind CSS, TanStack Query.
- **Automated Testing Suite**: 100% passing tests for authentication, tenant isolation, and RBAC security boundaries.

---

## Quick Start with Docker

1. **Clone & Configure Environment**:
   ```bash
   cp .env.example .env
   ```

2. **Start Services**:
   ```bash
   docker compose up --build
   ```

3. **Access Services**:
   - Frontend Dashboard: `http://localhost:3000`
   - Backend API & Swagger Docs: `http://localhost:8000/docs`
   - Healthcheck: `http://localhost:8000/api/v1/health`

---

## Local Development

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Running Backend Tests
```bash
cd backend
pytest -v
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Documentation
- [System Architecture](file:///docs/architecture.md)
- [Database Schema](file:///docs/database.md)
- [API Reference](file:///docs/api.md)
- [Authentication & Sessions](file:///docs/authentication.md)
- [Multi-Tenancy & Isolation](file:///docs/multi-tenancy.md)
- [Security Architecture](file:///docs/security.md)
- [Development Guide](file:///docs/development.md)
