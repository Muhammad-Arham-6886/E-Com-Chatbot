import httpx
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings

router = APIRouter(tags=["Health & Status"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness probe to check if the application process is alive."""
    return {
        "status": "ok",
        "service": "ai-customer-commerce-saas",
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive readiness probe checking database, pgvector, and local LLM connectivity."""
    components = {
        "database": "unknown",
        "pgvector_extension": "unknown",
        "ollama_service": "unknown",
    }
    all_ready = True

    # 1. Check Database Connectivity
    try:
        await db.execute(text("SELECT 1"))
        components["database"] = "connected"

        # Check pgvector extension if in postgres
        try:
            ext_res = await db.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            val = ext_res.scalar_one_or_none()
            components["pgvector_extension"] = "installed_and_active" if val else "not_found"
        except Exception:
            components["pgvector_extension"] = "test_environment_or_skipped"
    except Exception as e:
        components["database"] = f"error: {str(e)}"
        all_ready = False

    # 2. Check Ollama Connectivity (informational / non-blocking)
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                components["ollama_service"] = "connected"
            else:
                components["ollama_service"] = f"http_{resp.status_code}"
    except Exception:
        components["ollama_service"] = "unreachable_fallback_mode_active"

    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "degraded",
            "components": components,
        },
    )
