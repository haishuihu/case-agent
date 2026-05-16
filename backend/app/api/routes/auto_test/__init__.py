from app.api.routes.auto_test.environments import router as environments_router
from app.api.routes.auto_test.executions import router as executions_router
from app.api.routes.auto_test.plans import router as plans_router
from app.api.routes.auto_test.suites import router as suites_router

auto_test_router = suites_router
auto_test_router.include_router(plans_router)
auto_test_router.include_router(executions_router)
auto_test_router.include_router(environments_router)

__all__ = ["auto_test_router"]
