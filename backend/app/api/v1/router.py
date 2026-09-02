from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    health,
    organizations,
    websites,
    crawling,
    knowledge,
    chat,
    conversations,
    integrations,
    whatsapp,
    plugin,
    security,
    analytics,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(websites.router)
api_router.include_router(crawling.router)
api_router.include_router(knowledge.router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(integrations.router)
api_router.include_router(whatsapp.router)
api_router.include_router(plugin.router)
api_router.include_router(security.router)
api_router.include_router(analytics.router)
