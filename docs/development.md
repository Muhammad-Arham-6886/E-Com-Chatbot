# Development Guide

## Prerequisites
- Python 3.11+ (Python 3.13 supported)
- Node.js 18+ (Node.js 22 LTS supported)
- Docker & Docker Compose (for PostgreSQL + pgvector and Redis)

## Local Backend Setup
1. Navigate to `backend`:
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   pip install -r requirements.txt
   ```
2. Run database migrations:
   ```bash
   alembic upgrade head
   ```
3. Run backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
4. Run tests:
   ```bash
   pytest tests/ -v
   ```

## Local Frontend Setup
1. Navigate to `frontend`:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Open `http://localhost:3000`
