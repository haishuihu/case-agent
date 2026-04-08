from __future__ import annotations

import re

from app.schemas.testcase import TestCaseItem

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _normalize_text(value: str) -> str:
    compact = re.sub(r"\s+", "", value or "")
    return compact.casefold()


def _dedupe_key(case: TestCaseItem) -> str:
    return "|".join(
        [
            _normalize_text(case.title),
            _normalize_text(" ".join(case.steps)),
            _normalize_text(case.expected_result),
        ]
    )


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
            c.module_id or "",
            c.category,
            c.title,
        )
    )

    renumbered: list[TestCaseItem] = []
    for index, case in enumerate(deduped, start=1):
        renumbered.append(
            TestCaseItem(
                caseId=f"TC-{index:03d}",
                title=case.title,
                preconditions=case.preconditions,
                steps=case.steps,
                expectedResult=case.expected_result,
                category=case.category,
                priority=case.priority,
                module=case.module,
                moduleId=case.module_id,
                confirmationNote=case.confirmation_note,
                sourceBatch=case.source_batch,
            )
        )

    return renumbered
