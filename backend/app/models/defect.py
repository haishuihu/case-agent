from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class Defect(Base):
    """
    缺陷记录。

    可通过执行失败的用例一键创建，也可以手动登记。
    """
    __tablename__ = "defects"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))

    # 关联信息
    submission_id: Mapped[Optional[str]] = mapped_column(
        String(100), comment="关联的提测申请ID"
    )
    recommendation_id: Mapped[Optional[str]] = mapped_column(
        String(100), comment="关联的回归推荐ID（执行失败来源）"
    )
    execution_id: Mapped[Optional[str]] = mapped_column(
        String(100), comment="关联的执行记录ID"
    )

    # 缺陷基本信息
    title: Mapped[str] = mapped_column(String(300), comment="缺陷标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="缺陷描述")
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
        comment="严重程度: critical/high/medium/low"
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
        comment="优先级: high/medium/low"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="open",
        comment="缺陷状态: open/in_progress/resolved/closed"
    )

    # 环境信息
    environment: Mapped[Optional[str]] = mapped_column(String(100), comment="环境")
    browser: Mapped[Optional[str]] = mapped_column(String(50), comment="浏览器/客户端")

    # 根因分析
    root_cause: Mapped[Optional[str]] = mapped_column(Text, comment="根因分析")

    # 附件（JSON 数组，存储截图/日志路径）
    attachments: Mapped[Optional[str]] = mapped_column(
        Text, comment="附件路径列表(JSON)"
    )

    # 创建人
    creator: Mapped[Optional[str]] = mapped_column(String(100), comment="创建人")
    assignee: Mapped[Optional[str]] = mapped_column(String(100), comment="指派给")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="解决时间"
    )
