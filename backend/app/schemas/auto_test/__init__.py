from app.schemas.auto_test.test_execution import (
    DashboardStats,
    ExecutionCreateRequest,
    ExecutionDetailResponse,
    ExecutionResponse,
    ExecutionTrend,
    ExecutionUpdateRequest,
    FailureDistribution,
    RecentExecution,
    TestResultCreate,
    TestResultResponse,
)
from app.schemas.auto_test.test_plan import (
    GitWebhookPayload,
    RegressionRecommendItem,
    RegressionRecommendRequest,
    RegressionRecommendResponse,
    TestPlanCreate,
    TestPlanResponse,
    TestPlanUpdate,
    TriggerConfigCreate,
    TriggerConfigResponse,
    TriggerConfigUpdate,
    WebhookPayload,
)
from app.schemas.auto_test.test_environment import (
    EnvironmentCreate,
    EnvironmentResponse,
    EnvironmentUpdate,
)
from app.schemas.auto_test.test_suite import (
    TestCaseCreate,
    TestCaseResponse,
    TestCaseTagCreate,
    TestCaseTagResponse,
    TestCaseUpdate,
    TestCaseVersionResponse,
    TestSuiteCreate,
    TestSuiteResponse,
    TestSuiteUpdate,
)

__all__ = [
    # TestSuite
    "TestSuiteCreate",
    "TestSuiteUpdate",
    "TestSuiteResponse",
    # TestCase
    "TestCaseCreate",
    "TestCaseUpdate",
    "TestCaseResponse",
    "TestCaseTagCreate",
    "TestCaseTagResponse",
    "TestCaseVersionResponse",
    # TestPlan
    "TestPlanCreate",
    "TestPlanUpdate",
    "TestPlanResponse",
    "TriggerConfigCreate",
    "TriggerConfigUpdate",
    "TriggerConfigResponse",
    "GitWebhookPayload",
    "WebhookPayload",
    "RegressionRecommendRequest",
    "RegressionRecommendItem",
    "RegressionRecommendResponse",
    # Execution
    "ExecutionCreateRequest",
    "ExecutionUpdateRequest",
    "ExecutionResponse",
    "ExecutionDetailResponse",
    "TestResultCreate",
    "TestResultResponse",
    # Dashboard
    "DashboardStats",
    "RecentExecution",
    "ExecutionTrend",
    "FailureDistribution",
    # Environment
    "EnvironmentCreate",
    "EnvironmentUpdate",
    "EnvironmentResponse",
]
