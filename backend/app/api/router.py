from fastapi import APIRouter

from app.api.routes.case_review import router as case_review_router
from app.api.routes.defect import router as defect_router
from app.api.routes.generate import router as generate_router
from app.api.routes.impact import router as impact_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.llm_config import config_router, embedding_router, llm_router
from app.api.routes.quick_generate_history import router as quick_history_router
from app.api.routes.regression import router as regression_router
from app.api.routes.regression_execution import router as regression_execution_router
from app.api.routes.submission import router as submission_router

api_router = APIRouter()
api_router.include_router(generate_router)
api_router.include_router(case_review_router)
api_router.include_router(defect_router)
api_router.include_router(embedding_router)
api_router.include_router(impact_router)
api_router.include_router(knowledge_router)
api_router.include_router(llm_router)
api_router.include_router(quick_history_router)
api_router.include_router(regression_router)
api_router.include_router(regression_execution_router)
api_router.include_router(submission_router)
api_router.include_router(config_router)
