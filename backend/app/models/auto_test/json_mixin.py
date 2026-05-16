from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class JSONTextField(TypeDecorator):
    """SQLAlchemy TypeDecorator that automatically serializes/deserializes JSON to/from Text column."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: str | None, dialect) -> Any:
        if value is None:
            return None
        return json.loads(value)
