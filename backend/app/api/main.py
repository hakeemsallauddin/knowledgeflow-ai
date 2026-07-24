from fastapi import APIRouter

from app.api.routes import qa, login, documents
from app.api.routes import register
api_router = APIRouter()

api_router.include_router(
    login.router,
    tags=["login"],
)

api_router.include_router(
    qa.router,
    prefix="/qa",
    tags=["qa"],
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"],
)
api_router.include_router(
    register.router,
    tags=["Authentication"],
)