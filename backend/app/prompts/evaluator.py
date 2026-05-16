"""Evaluation harness for prompt templates.

Usage:
    python -m app.prompts.evaluator --template phase4_module_detail --dataset eval/datasets/login_scenarios.json
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.prompts.manager import get_prompt_manager
from app.services.llm_client import build_llm_client

logger = logging.getLogger(__name__)


@dataclass
class EvalMetrics:
    coverage: float = 0.0
    priority_distribution: dict[str, float] = field(default_factory=dict)
    dedup_score: float = 0.0
    actionability: float = 0.0
    stability: float = 0.0


def compute_coverage(cases: list[dict], must_cover: list[str]) -> float:
    """Check what fraction of must_cover scenarios are present in case titles/steps."""
    if not must_cover:
        return 1.0
    covered = 0
    case_texts = [
        json.dumps(c, ensure_ascii=False).lower() for c in cases
    ]
    for scenario in must_cover:
        scenario_lower = scenario.lower()
        if any(scenario_lower in ct for ct in case_texts):
            covered += 1
    return covered / len(must_cover)


def compute_priority_distribution(cases: list[dict]) -> dict[str, float]:
    """Return priority distribution as fractions."""
    total = len(cases)
    if total == 0:
        return {}
    counts: dict[str, int] = {}
    for c in cases:
        p = c.get("priority", "P2")
        counts[p] = counts.get(p, 0) + 1
    return {k: v / total for k, v in counts.items()}


def compute_dedup_score(cases: list[dict]) -> float:
    """Check how many cases are near-duplicates by title similarity.

    Returns fraction of unique cases (higher is better).
    """
    titles = [c.get("title", "") for c in cases]
    if len(titles) <= 1:
        return 1.0
    duplicates = 0
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            if _jaccard_similarity(titles[i], titles[j]) > 0.7:
                duplicates += 1
                break
    return 1.0 - (duplicates / len(titles))


def compute_actionability(cases: list[dict]) -> float:
    """Check what fraction of cases have actionable steps and verifiable results."""
    if not cases:
        return 0.0
    actionable = 0
    for c in cases:
        steps = c.get("steps", [])
        expected = c.get("expected_result", "")
        if isinstance(steps, list) and len(steps) >= 1 and expected:
            actionable += 1
    return actionable / len(cases)


def _jaccard_similarity(a: str, b: str) -> float:
    a_set = set(a)
    b_set = set(b)
    if not a_set or not b_set:
        return 0.0
    intersection = len(a_set & b_set)
    union = len(a_set | b_set)
    return intersection / union if union > 0 else 0.0


def evaluate(
    template_name: str,
    dataset_path: str,
    model_key: str | None = None,
    stability_runs: int = 3,
) -> dict[str, Any]:
    """Run evaluation for a template against a dataset.

    Returns a dict with metrics and per-scenario results.
    """
    dataset = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        dataset = [dataset]

    client = build_llm_client(model_key)
    pm = get_prompt_manager()
    all_metrics: list[dict] = []

    for scenario in dataset:
        scenario_id = scenario.get("id", "unknown")
        must_cover = scenario.get("must_cover", [])
        module = scenario.get("module", {})

        context = {
            "requirement_context": scenario.get("requirement", ""),
            "module_name": module.get("name", ""),
            "module_id": module.get("id", "M01"),
            "business_rules": "\n".join(f"- {r}" for r in scenario.get("rules", [])),
            "data_constraints": json.dumps(scenario.get("constraints", []), ensure_ascii=False),
        }

        sys_prompt, user_prompt = pm.render(template_name, context)

        # Stability: run N times and compare
        all_cases: list[list[dict]] = []
        for run_idx in range(stability_runs):
            try:
                response = client.create_chat_completion(
                    system_prompt=sys_prompt,
                    user_content=user_prompt,
                    response_format={"type": "json_object"},
                )
                parsed = _parse_cases(response.content)
                all_cases.append(parsed)
            except Exception as exc:
                logger.warning("[eval] run %d failed: %s", run_idx, exc)
                all_cases.append([])

        # Use first run for single-run metrics
        first_run_cases = all_cases[0] if all_cases else []

        metrics = EvalMetrics(
            coverage=compute_coverage(first_run_cases, must_cover),
            priority_distribution=compute_priority_distribution(first_run_cases),
            dedup_score=compute_dedup_score(first_run_cases),
            actionability=compute_actionability(first_run_cases),
            stability=_compute_stability(all_cases),
        )

        all_metrics.append({
            "scenario_id": scenario_id,
            "case_count": len(first_run_cases),
            "coverage": metrics.coverage,
            "priority_distribution": metrics.priority_distribution,
            "dedup_score": metrics.dedup_score,
            "actionability": metrics.actionability,
            "stability": metrics.stability,
        })

        logger.info(
            "[eval] %s: cases=%d cov=%.2f action=%.2f stab=%.2f",
            scenario_id, len(first_run_cases),
            metrics.coverage, metrics.actionability, metrics.stability,
        )

    # Aggregate
    n = len(all_metrics)
    return {
        "template": template_name,
        "dataset": dataset_path,
        "scenarios": n,
        "aggregate": {
            "coverage": sum(m["coverage"] for m in all_metrics) / n if n else 0,
            "actionability": sum(m["actionability"] for m in all_metrics) / n if n else 0,
            "stability": sum(m["stability"] for m in all_metrics) / n if n else 0,
            "dedup_score": sum(m["dedup_score"] for m in all_metrics) / n if n else 0,
            "avg_cases": sum(m["case_count"] for m in all_metrics) / n if n else 0,
        },
        "details": all_metrics,
    }


def _parse_cases(content: str) -> list[dict]:
    """Parse test cases from LLM response content."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try stripping markdown fence
        stripped = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("cases", "smoke_cases", "module_cases", "review_cases", "supplement_cases"):
            if key in data and isinstance(data[key], list):
                return data[key]
        if "Cases" in data:
            return data.get("Cases", [])
    return []


def _compute_stability(all_cases: list[list[dict]]) -> float:
    """Compute average pairwise Jaccard similarity of case title sets across runs."""
    valid = [c for c in all_cases if c]
    if len(valid) < 2:
        return 0.0

    def title_set(cases: list[dict]) -> set[str]:
        return {c.get("title", "") for c in cases}

    similarities: list[float] = []
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            a = title_set(valid[i])
            b = title_set(valid[j])
            if not a or not b:
                continue
            sim = len(a & b) / len(a | b)
            similarities.append(sim)

    return sum(similarities) / len(similarities) if similarities else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a prompt template")
    parser.add_argument("--template", required=True, help="Template name (e.g. phase4_module_detail)")
    parser.add_argument("--dataset", required=True, help="Path to eval dataset JSON")
    parser.add_argument("--model", default=None, help="Model key override")
    parser.add_argument("--stability-runs", type=int, default=3, help="Number of runs for stability check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    result = evaluate(
        template_name=args.template,
        dataset_path=args.dataset,
        model_key=args.model,
        stability_runs=args.stability_runs,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        agg = result["aggregate"]
        print(f"\nTemplate: {result['template']}")
        print(f"Dataset:  {result['dataset']}")
        print(f"Scenarios: {result['scenarios']}")
        print(f"\nAggregate Metrics:")
        print(f"  Coverage:      {agg['coverage']:.2%}")
        print(f"  Actionability: {agg['actionability']:.2%}")
        print(f"  Stability:     {agg['stability']:.2%}")
        print(f"  Dedup Score:   {agg['dedup_score']:.2%}")
        print(f"  Avg Cases:     {agg['avg_cases']:.1f}")


if __name__ == "__main__":
    main()
