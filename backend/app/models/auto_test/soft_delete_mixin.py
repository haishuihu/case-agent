from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column


class SoftDeleteMixin:
    """软删除 Mixin，提供 is_deleted 和 deleted_at 字段"""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已删除")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="删除时间")

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
