from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from apps.api.action_routes import router as action_router
from apps.api.knowledge_routes import router as knowledge_router
from apps.api.model_routes import router as model_router
from apps.api.puter_routes import router as puter_router

router = APIRouter(prefix="/v1", tags=["cognition"])
bearer = HTTPBearer(auto_error=False)
bearer_dependency = Depends(bearer)
router.include_router(action_router)
router.include_router(model_router)
router.include_router(puter_router)
router.include_router(knowledge_router)
