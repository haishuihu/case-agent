from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class TestCaseType(str, Enum):
    API = "api"
    UI = "ui"
    UNIT = "unit"
    INTEGRATION = "integration"


class TestCaseStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class TestSuite(Base):
    """测试套件"""
    __tablename__ = "test_suites"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="套件名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="套件描述")
    project_id: Mapped[Optional[str]] = mapped_column(String(100), comment="项目ID")
    created_by: Mapped[Optional[str]] = mapped_column(String(100), comment="创建人")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="suite", cascade="all, delete-orphan"
    )
    test_plans: Mapped[list["TestPlan"]] = relationship(
        back_populates="suite", cascade="all, delete-orphan"
    )


class TestCaseTag(Base):
    """测试用例标签"""
    __tablename__ = "test_case_tags"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="标签名称")
    color: Mapped[str] = mapped_column(String(20), default="#0071e3", comment="标签颜色")
    description: Mapped[Optional[str]] = mapped_column(String(200), comment="标签描述")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TestCase(Base):
    """测试用例"""
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    suite_id: Mapped[str] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="用例标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="用例描述")

    case_type: Mapped[str] = mapped_column(
        String(20), default=TestCaseType.API.value,
        comment="用例类型: api/ui/unit/integration"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=TestCaseStatus.ACTIVE.value,
        comment="状态: draft/active/deprecated/archived"
    )
    priority: Mapped[int] = mapped_column(default=3, comment="优先级 1-5")

    # API 测试专用字段
    method: Mapped[Optional[str]] = mapped_column(String(10), comment="HTTP方法")
    endpoint: Mapped[Optional[str]] = mapped_column(String(500), comment="API端点")
    headers: Mapped[Optional[str]] = mapped_column(Text, comment="请求头 JSON")
    request_body: Mapped[Optional[str]] = mapped_column(Text, comment="请求体 JSON")
    expected_status: Mapped[Optional[int]] = mapped_column(default=200, comment="预期状态码")
    expected_response: Mapped[Optional[str]] = mapped_column(Text, comment="预期响应 JSON")
    validation_rules: Mapped[Optional[str]] = mapped_column(Text, comment="验证规则 JSON")

    # UI 测试字段 (JSON)
    ui_selector: Mapped[Optional[str]] = mapped_column(String(500), comment="UI选择器")
    ui_action: Mapped[Optional[str]] = mapped_column(String(50), comment="UI动作")
    ui_expected: Mapped[Optional[str]] = mapped_column(Text, comment="UI预期")

    # 元数据
    test_data: Mapped[Optional[str]] = mapped_column(Text, comment="测试数据 JSON")
    extra_metadata: Mapped[Optional[str]] = mapped_column(Text, comment="扩展元数据 JSON")
    tags: Mapped[Optional[str]] = mapped_column(Text, comment="标签JSON数组")

    # 版本信息
    current_version: Mapped[int] = mapped_column(default=1, comment="当前版本号")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    suite: Mapped["TestSuite"] = relationship(back_populates="test_cases")
    versions: Mapped[list["TestCaseVersion"]] = relationship(
        back_populates="test_case", cascade="all, delete-orphan"
    )
    results: Mapped[list["TestResult"]] = relationship(
        back_populates="test_case", cascade="all, delete-orphan"
    )


class TestCaseVersion(Base):
    """测试用例版本"""
    __tablename__ = "test_case_versions"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False, comment="版本号")

    content: Mapped[Optional[str]] = mapped_column(Text, comment="版本内容 JSON")
    change_summary: Mapped[Optional[str]] = mapped_column(String(500), comment="变更说明")
    changed_by: Mapped[Optional[str]] = mapped_column(String(100), comment="变更人")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    test_case: Mapped["TestCase"] = relationship(back_populates="versions")
