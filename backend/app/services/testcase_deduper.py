from __future__ import annotations

import re

from app.schemas.testcase import TestCaseItem

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _normalize_text(value: str) -> str:
    compact = re.sub(r"\s+", "", value or "")
    return compact.casefold()


def _dedupe_key(case: TestCaseItem) -> str:
    return _normalize_text(case.summary)


def dedupe_and_renumber(cases: list[TestCaseItem]) -> list[TestCaseItem]:
    seen: set[str] = set()
    deduped: list[TestCaseItem] = []

    for case in cases:
        key = _dedupe_key(case)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(case)

    deduped.sort(
        key=lambda c: (
            PRIORITY_ORDER.get(c.priority, 9),
            c.module or "",
            c.category,
        )
    )

    return deduped
