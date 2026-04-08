from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional, TypeVar

ProgressCallback = Optional[Callable[[dict[str, object]], None]]
CancelCheck = Optional[Callable[[], bool]]


class _PhaseTimeoutError(Exception):
    """Raised when a phase exceeds its time budget."""


_T = TypeVar("_T")


def _call_with_timeout(fn: Callable[[], _T], timeout_seconds: float) -> _T:
    """Run fn in a thread and raise _PhaseTimeoutError if it exceeds timeout_seconds."""
    result: dict[str, object] = {"value": None, "exc": None}
    done_event = threading.Event()

    def target() -> None:
        try:
            result["value"] = fn()
        except Exception as exc:  # noqa: PERF203
            result["exc"] = exc
        finally:
            done_event.set()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    if not done_event.wait(timeout=timeout_seconds):
        raise _PhaseTimeoutError(f"阶段执行超过 {timeout_seconds:.0f}s 超时限制")
    if result["exc"] is not None:
        raise result["exc"]  # type: ignore[misc]
    return result["value"]  # type: ignore[return-value]


from app.prompts.testcase_prompt import (
    SYSTEM_PROMPT,
    KnowledgeContextItem,
    build_batch_generation_prompt,
    build_high_coverage_markdown_prompt,
    build_knowledge_context,
    build_module_detail_markdown_prompt,
    build_module_detail_prompt,
    build_requirement_context,
    build_requirement_review_prompt,
    build_review_prompt,
    build_smoke_test_prompt,
)
from app.schemas.testcase import GenerationMetadata, ReviewQuestion, TestCaseItem
from app.services.file_parser import DocumentContext, ImageContext
from app.services.testcase_deduper import dedupe_and_renumber
from app.services.testcase_exporter import build_skill_template_markdown
from app.services.testcase_parser import (
    PlannedModule,
    ReviewResult,
    parse_batch_cases_response,
    parse_cases_response,
    parse_markdown_table,
    parse_review_response,
)

logger = logging.getLogger(__name__)


@dataclass
class StructuredGenerationResult:
    markdown: str
    prompt_snapshot: str
    raw_response: str
    model_name: str
    cases: list[TestCaseItem]
    metadata: GenerationMetadata


class TestCaseGenerator:
    def __init__(self, llm_client, db_session=None):
        self.llm_client = llm_client
        self.settings = llm_client.settings
        self.db_session = db_session

    def _check_cancel(self, cancel_check: CancelCheck) -> None:
        if cancel_check and cancel_check():
            raise RuntimeError("任务已取消")

    @staticmethod
    def _progress_ratio(phases: list[dict[str, object]]) -> float:
        if not phases:
            return 0.0
        n = len(phases)
        done = sum(
            1 for p in phases if p.get("status") in ("done", "skipped")
        )
        running = any(p.get("status") == "running" for p in phases)
        if running:
            return min(0.99, (done + 0.45) / n)
        return done / n if n else 0.0

    def _emit_progress(
        self,
        callback: ProgressCallback,
        phases: list[dict[str, object]],
        current_phase: str,
        phase_label: str,
    ) -> None:
        if not callback:
            return
        callback(
            {
                "currentPhase": current_phase,
                "phaseLabel": phase_label,
                "progress": self._progress_ratio(phases),
                "phases": [dict(p) for p in phases],
            }
        )

    def _build_phase_plan(self, review: ReviewResult) -> list[dict[str, object]]:
        n_mod = len(review.modules)
        phases: list[dict[str, object]] = [
            {
                "name": "phase1_review",
                "label": "需求评审与模块分解",
                "status": "pending",
                "elapsedSeconds": 0,
            },
            {
                "name": "phase3_smoke",
                "label": "冒烟测试生成 (P0/P1)",
                "status": "pending",
                "elapsedSeconds": 0,
            },
        ]
        for i, m in enumerate(review.modules, 1):
            phases.append(
                {
                    "name": f"phase4_{m.id}",
                    "label": f"模块详细生成 ({i}/{n_mod} {m.name})",
                    "status": "pending",
                    "elapsedSeconds": 0,
                }
            )
        phases.append(
            {
                "name": "phase5_review",
                "label": "多视角评审补充",
                "status": "pending",
                "elapsedSeconds": 0,
            }
        )
        return phases

    # ------------------------------------------------------------------
    # Phase 1: Requirements Review + Module Decomposition
    # ------------------------------------------------------------------

    def _retrieve_knowledge_context(
        self,
        requirement_text: str,
        module_names: Optional[list[str]] = None,
        max_chars: int = 3000,
    ) -> str:
        if not self.db_session:
            return ""
        try:
            from app.services.knowledge_service import retrieve_knowledge_for_generation

            results = retrieve_knowledge_for_generation(
                db=self.db_session,
                requirement_text=requirement_text,
                module_names=module_names,
            )
            if not results:
                return ""

            items = []
            for doc, _score, _source in results:
                tags = []
                if doc.module_tags:
                    try:
                        parsed = json.loads(doc.module_tags)
                        tags = parsed if isinstance(parsed, list) else []
                    except (json.JSONDecodeError, TypeError):
                        pass
                items.append(KnowledgeContextItem(
                    title=doc.title,
                    doc_type=doc.doc_type,
                    summary=doc.summary or doc.content[:300],
                    module_tags=tags,
                ))

            ctx = build_knowledge_context(items, max_chars=max_chars)
            if ctx:
                logger.info("[knowledge] injecting %d knowledge items into prompt", len(items))
            return ctx
        except Exception as exc:
            logger.warning("[knowledge] retrieval failed, proceeding without: %s", exc)
            return ""

    def _phase1_review(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
    ) -> ReviewResult:
        profile = self.llm_client.profile
        knowledge_ctx = self._retrieve_knowledge_context(requirement_text, max_chars=3000)
        prompt = build_requirement_review_prompt(requirement_text, document_contexts, knowledge_context=knowledge_ctx)
        planning_max = profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase1-review] start  max_tokens=%d", planning_max)

        response = self.llm_client.create_chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_content=prompt,
            max_tokens=planning_max,
            response_format={"type": "json_object"},
        )

        logger.info(
            "[phase1-review] done  elapsed=%.1fs  finish_reason=%s  content_len=%d",
            time.monotonic() - t0,
            response.finish_reason,
            len(response.content),
        )

        result = parse_review_response(response.content)
        logger.info(
            "[phase1-review] modules=%d  questions=%d  rules=%d  constraints=%d",
            len(result.modules),
            len(result.questions),
            len(result.business_rules),
            len(result.data_constraints),
        )

        if not result.modules:
            result.modules = [
                PlannedModule(id="M01", name="核心功能", description=requirement_text[:200])
            ]
            logger.info("[phase1-review] no modules parsed, using fallback single module")

        return result

    # ------------------------------------------------------------------
    # Phase 3: Smoke Tests (P0/P1)
    # ------------------------------------------------------------------

    def _phase3_smoke(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
        review: ReviewResult,
        warnings: list[str],
    ) -> list[TestCaseItem]:
        modules_json = json.dumps(
            [{"id": m.id, "name": m.name, "description": m.description, "sub_features": m.sub_features}
             for m in review.modules],
            ensure_ascii=False,
            indent=2,
        )
        business_rules = "\n".join(f"- {r}" for r in review.business_rules) if review.business_rules else "无明确业务规则。"

        prompt = build_smoke_test_prompt(
            requirement_text, document_contexts, modules_json, business_rules
        )
        profile = self.llm_client.profile
        smoke_max = profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase3-smoke] start  max_tokens=%d", smoke_max)

        def _do_smoke() -> object:
            return self.llm_client.create_chat_completion(
                system_prompt=SYSTEM_PROMPT,
                user_content=prompt,
                max_tokens=smoke_max,
                response_format={"type": "json_object"},
            )

        try:
            response = _call_with_timeout(_do_smoke, timeout_seconds=180)
        except _PhaseTimeoutError:
            warnings.append("冒烟测试阶段执行超时（180s），已跳过该阶段。")
            logger.warning("[phase3-smoke] timeout after 180s, skipping")
            return []
        except Exception:  # noqa: PERF203
            # Re-raise so outer handler deals with it
            raise

        logger.info(
            "[phase3-smoke] done  elapsed=%.1fs  finish_reason=%s  content_len=%d",
            time.monotonic() - t0,
            response.finish_reason,
            len(response.content),
        )

        try:
            cases = parse_cases_response(
                response.content,
                default_category="冒烟测试",
                default_priority="P0",
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            warnings.append(f"冒烟测试解析失败：{exc}")
            cases = []

        if response.finish_reason == "length":
            warnings.append("冒烟测试阶段达到输出长度上限，结果可能不完整。")

        logger.info("[phase3-smoke] parsed_count=%d", len(cases))
        return cases

    # ------------------------------------------------------------------
    # Phase 4: Per-module Detail Generation (P2/P3)
    # ------------------------------------------------------------------

    def _phase4_module_detail(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
        module: PlannedModule,
        review: ReviewResult,
        existing_titles: list[str],
        warnings: list[str],
        incomplete_categories: list[str],
    ) -> tuple[list[TestCaseItem], dict[str, object]]:
        business_rules = "\n".join(f"- {r}" for r in review.business_rules) if review.business_rules else "无"
        data_constraints = json.dumps(review.data_constraints, ensure_ascii=False) if review.data_constraints else "无"

        min_cases = max(15, len(module.sub_features) * 5)

        knowledge_ctx = self._retrieve_knowledge_context(
            requirement_text,
            module_names=[module.name],
            max_chars=2000,
        )

        prompt = build_module_detail_prompt(
            requirement_text=requirement_text,
            document_contexts=document_contexts,
            module_id=module.id,
            module_name=module.name,
            sub_features=module.sub_features,
            business_rules=business_rules,
            data_constraints=data_constraints,
            existing_case_titles=existing_titles,
            min_cases=min_cases,
            knowledge_context=knowledge_ctx,
        )
        batch_max = self.llm_client.profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase4-detail] module=%s(%s)  max_tokens=%d  start", module.id, module.name, batch_max)

        def _do_phase4() -> object:
            return self.llm_client.create_chat_completion(
                system_prompt=SYSTEM_PROMPT,
                user_content=prompt,
                max_tokens=batch_max,
                response_format={"type": "json_object"},
            )

        try:
            response = _call_with_timeout(_do_phase4, timeout_seconds=240)
        except _PhaseTimeoutError:
            warnings.append(f"模块 {module.name} 执行超时（240s），已跳过。")
            logger.warning("[phase4-detail] module=%s timeout after 240s", module.id)
            return [], {
                "module": module.name,
                "module_id": module.id,
                "finish_reason": "timeout",
                "raw_response": "",
                "fallback_finish_reason": None,
                "fallback_raw_response": None,
                "parsed_count": 0,
                "parser_mode": "timeout",
            }
        except Exception:  # noqa: PERF203
            raise

        elapsed = time.monotonic() - t0
        logger.info(
            "[phase4-detail] module=%s  elapsed=%.1fs  finish_reason=%s  content_len=%d",
            module.id, elapsed, response.finish_reason, len(response.content),
        )

        parsed_cases: list[TestCaseItem] = []
        parser_mode = "json"

        try:
            parsed_cases = parse_cases_response(
                response.content,
                default_category="正常流程",
                default_module=module.name,
                default_module_id=module.id,
                default_priority="P2",
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            warnings.append(f"模块 {module.name} JSON 解析失败：{exc}")

        fallback_response_raw: Optional[str] = None
        fallback_finish_reason: Optional[str] = None
        if not parsed_cases:
            parser_mode = "markdown-fallback"
            md_prompt = build_module_detail_markdown_prompt(
                requirement_text=requirement_text,
                document_contexts=document_contexts,
                module_id=module.id,
                module_name=module.name,
                sub_features=module.sub_features,
                min_cases=min_cases,
            )
            t1 = time.monotonic()
            logger.info("[phase4-fallback] module=%s  markdown fallback start", module.id)

            def _do_fallback() -> object:
                return self.llm_client.create_chat_completion(
                    system_prompt=SYSTEM_PROMPT,
                    user_content=md_prompt,
                    max_tokens=batch_max,
                )

            try:
                fallback_response = _call_with_timeout(_do_fallback, timeout_seconds=240)
            except _PhaseTimeoutError:
                warnings.append(f"模块 {module.name} Markdown 回退执行超时（240s）。")
                logger.warning("[phase4-fallback] module=%s timeout", module.id)
                return parsed_cases, {
                    "module": module.name,
                    "module_id": module.id,
                    "finish_reason": response.finish_reason,
                    "raw_response": response.raw_response,
                    "fallback_finish_reason": "timeout",
                    "fallback_raw_response": "",
                    "parsed_count": 0,
                    "parser_mode": "timeout-fallback",
                }
            except Exception:  # noqa: PERF203
                raise

            logger.info(
                "[phase4-fallback] module=%s  elapsed=%.1fs  finish_reason=%s",
                module.id, time.monotonic() - t1, fallback_response.finish_reason,
            )
            fallback_finish_reason = fallback_response.finish_reason
            fallback_response_raw = fallback_response.raw_response
            md_cases = parse_markdown_table(fallback_response.content)
            for c in md_cases:
                parsed_cases.append(
                    TestCaseItem(
                        caseId=c.case_id,
                        title=c.title,
                        preconditions=c.preconditions,
                        steps=c.steps,
                        expectedResult=c.expected_result,
                        category=c.category,
                        priority=c.priority or "P2",
                        module=module.name,
                        moduleId=module.id,
                        sourceBatch=module.name,
                    )
                )
            if parsed_cases:
                warnings.append(f"模块 {module.name} 已从 JSON 降级为 Markdown 解析。")

        effective_finish = fallback_finish_reason or response.finish_reason
        if effective_finish == "length":
            warnings.append(f"模块 {module.name} 达到输出上限，结果可能不完整。")
            incomplete_categories.append(module.name)
        if not parsed_cases:
            incomplete_categories.append(module.name)

        logger.info("[phase4-detail] module=%s  parsed_count=%d  mode=%s", module.id, len(parsed_cases), parser_mode)

        return parsed_cases, {
            "module": module.name,
            "module_id": module.id,
            "finish_reason": response.finish_reason,
            "raw_response": response.raw_response,
            "fallback_finish_reason": fallback_finish_reason,
            "fallback_raw_response": fallback_response_raw,
            "parsed_count": len(parsed_cases),
            "parser_mode": parser_mode,
        }

    # ------------------------------------------------------------------
    # Phase 5: Multi-Perspective Review
    # ------------------------------------------------------------------

    def _phase5_review(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
        existing_cases: list[TestCaseItem],
        warnings: list[str],
    ) -> list[TestCaseItem]:
        summary_lines = []
        for c in existing_cases[:100]:
            note = f" [{c.confirmation_note}]" if c.confirmation_note else ""
            summary_lines.append(f"- [{c.priority}] [{c.module or '-'}] {c.title} → {c.expected_result}{note}")
        summary = "\n".join(summary_lines)

        prompt = build_review_prompt(requirement_text, document_contexts, summary)
        profile = self.llm_client.profile
        review_max = profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase5-review] start  existing_cases=%d  max_tokens=%d", len(existing_cases), review_max)

        response = self.llm_client.create_chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_content=prompt,
            max_tokens=review_max,
            response_format={"type": "json_object"},
        )

        logger.info(
            "[phase5-review] done  elapsed=%.1fs  finish_reason=%s  content_len=%d",
            time.monotonic() - t0,
            response.finish_reason,
            len(response.content),
        )

        try:
            supplement = parse_cases_response(
                response.content,
                default_category="评审补充",
                default_priority="P2",
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            warnings.append(f"评审补充解析失败：{exc}")
            supplement = []

        if response.finish_reason == "length":
            warnings.append("评审阶段达到输出上限，补充结果可能不完整。")

        logger.info("[phase5-review] supplement_count=%d", len(supplement))
        return supplement

    # ------------------------------------------------------------------
    # Phase 2: Batch Generation (合并 Phase3/4/5 为单次调用)
    # ------------------------------------------------------------------

    def _phase2_batch(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
        review: ReviewResult,
        warnings: list[str],
    ) -> tuple[list[TestCaseItem], list[TestCaseItem], list[TestCaseItem]]:
        """合并的批量生成：冒烟测试 + 模块详情 + 评审补充，一次 LLM 调用完成。

        返回 (smoke_cases, module_cases, review_cases) 三元组。
        当解析失败时，smoke_cases/module_cases/review_cases 均为空列表。
        """
        business_rules = (
            "\n".join(f"- {r}" for r in review.business_rules)
            if review.business_rules
            else "无"
        )
        data_constraints = (
            json.dumps(review.data_constraints, ensure_ascii=False)
            if review.data_constraints
            else "无"
        )

        knowledge_ctx = self._retrieve_knowledge_context(requirement_text, max_chars=3000)

        prompt = build_batch_generation_prompt(
            requirement_text=requirement_text,
            document_contexts=document_contexts,
            modules=review.modules,
            business_rules=business_rules,
            data_constraints=data_constraints,
            knowledge_context=knowledge_ctx,
        )

        profile = self.llm_client.profile
        batch_max = profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase2-batch] start  modules=%d  max_tokens=%d", len(review.modules), batch_max)

        def _do_batch() -> object:
            return self.llm_client.create_chat_completion(
                system_prompt=SYSTEM_PROMPT,
                user_content=prompt,
                max_tokens=batch_max,
                response_format={"type": "json_object"},
            )

        try:
            response = _call_with_timeout(_do_batch, timeout_seconds=480)
        except _PhaseTimeoutError:
            warnings.append("批量生成阶段执行超时（480s），已回退到原有管道模式。")
            logger.warning("[phase2-batch] timeout after 480s, returning empty for fallback")
            return [], [], []

        except ValueError as exc:
            # API 认证失败、超限、连接失败等，透传具体原因
            warnings.append(f"批量生成 API 调用失败：{exc}，已回退到原有管道模式。")
            logger.warning("[phase2-batch] API error: %s", exc)
            return [], [], []

        except Exception as exc:
            warnings.append(f"批量生成阶段异常：{exc}，已回退到原有管道模式。")
            logger.warning("[phase2-batch] unexpected error: %s", exc)
            return [], [], []

        logger.info(
            "[phase2-batch] done  elapsed=%.1fs  finish_reason=%s  content_len=%d",
            time.monotonic() - t0,
            response.finish_reason,
            len(response.content),
        )

        try:
            smoke, module_detail, review_supplement = parse_batch_cases_response(response.content)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            warnings.append(f"批量生成响应解析失败：{exc}，已回退到原有管道模式。")
            logger.warning("[phase2-batch] parse failed: %s", exc)
            return [], [], []

        except Exception as exc:
            warnings.append(f"批量生成响应处理异常：{exc}，已回退到原有管道模式。")
            logger.warning("[phase2-batch] parse unexpected error: %s", exc)
            return [], [], []

        if response.finish_reason == "length":
            warnings.append("批量生成阶段达到输出长度上限，结果可能不完整。")

        logger.info(
            "[phase2-batch] parsed  smoke=%d  module=%d  review=%d",
            len(smoke), len(module_detail), len(review_supplement),
        )
        return smoke, module_detail, review_supplement

    def _generate_original_pipeline(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
        review: ReviewResult,
        warnings: list[str],
        incomplete_categories: list[str],
        progress_callback: ProgressCallback,
        phases_state: list[dict[str, object]],
        requirement_context: str,
        profile,
        cancel_check: CancelCheck,
    ) -> tuple[list[TestCaseItem], list[dict[str, object]]]:
        """原有 Phase3/4/5 管道的完整实现，用于 Phase2 失败时的回退。"""
        raw_batches: list[dict[str, object]] = []

        # 构建原有 phase plan
        phases_state = self._build_phase_plan(review)
        phases_state[0]["status"] = "done"
        self._emit_progress(
            progress_callback,
            phases_state,
            "phase3_smoke",
            "冒烟测试生成 (P0/P1)",
        )

        self._check_cancel(cancel_check)

        # --- Phase 3: Smoke Tests (P0/P1) ---
        t_phase3 = time.monotonic()
        self._check_cancel(cancel_check)
        smoke_cases = self._phase3_smoke(requirement_text, document_contexts, review, warnings)
        self._check_cancel(cancel_check)
        e3 = int(time.monotonic() - t_phase3)
        phases_state[1]["status"] = "done"
        phases_state[1]["elapsedSeconds"] = e3

        all_cases: list[TestCaseItem] = list(smoke_cases)

        # --- Phase 4: Per-module Detail Generation (P2/P3) - parallel ---
        phase4_start_idx = 2
        n_modules = len(review.modules)
        p5idx = phase4_start_idx + n_modules
        raw_batches_by_idx: dict[int, tuple[list[TestCaseItem], dict[str, object]]] = {}

        def _run_phase4_module(idx: int, module: PlannedModule) -> tuple[int, list[TestCaseItem], dict[str, object]]:
            existing_titles = [c.title for c in all_cases]
            parsed_cases, raw_batch = self._phase4_module_detail(
                requirement_text=requirement_text,
                document_contexts=document_contexts,
                module=module,
                review=review,
                existing_titles=existing_titles,
                warnings=warnings,
                incomplete_categories=incomplete_categories,
            )
            return idx, parsed_cases, raw_batch

        with ThreadPoolExecutor(max_workers=min(n_modules, 8)) as executor:
            futures = {
                executor.submit(_run_phase4_module, idx, module): (idx, module)
                for idx, module in enumerate(review.modules, 1)
            }

            for future in as_completed(futures):
                idx, module = futures[future]
                try:
                    result_idx, parsed_cases, raw_batch = future.result()
                    raw_batches_by_idx[result_idx] = (parsed_cases, raw_batch)
                except Exception as exc:
                    logger.error("[phase4] module %s failed: %s", module.name, exc)
                    warnings.append(f"模块 {module.name} 生成失败：{exc}")
                self._check_cancel(cancel_check)

        for idx in sorted(raw_batches_by_idx.keys()):
            parsed_cases, raw_batch = raw_batches_by_idx[idx]
            all_cases.extend(parsed_cases)
            raw_batches.append(raw_batch)
            module = review.modules[idx - 1]
            pidx = phase4_start_idx + idx - 1
            phases_state[pidx]["status"] = "done"
            phases_state[pidx]["elapsedSeconds"] = 0
            self._emit_progress(
                progress_callback,
                phases_state,
                str(phases_state[pidx]["name"]),
                str(phases_state[pidx]["label"]),
            )
            logger.info(
                "[generate] phase4 module %d/%d done  cumulative_cases=%d",
                idx, n_modules, len(all_cases),
            )
            self._check_cancel(cancel_check)

        # --- Phase 5: Multi-Perspective Review ---
        self._check_cancel(cancel_check)
        phases_state[p5idx]["status"] = "running"
        self._emit_progress(
            progress_callback,
            phases_state,
            "phase5_review",
            "多视角评审补充",
        )
        t5 = time.monotonic()
        try:
            supplement = self._phase5_review(requirement_text, document_contexts, all_cases, warnings)
        except Exception as exc:
            logger.error("[phase5] failed: %s", exc)
            warnings.append(f"评审补充失败：{exc}")
            supplement = []
        e5 = int(time.monotonic() - t5)
        phases_state[p5idx]["status"] = "done"
        phases_state[p5idx]["elapsedSeconds"] = e5
        self._emit_progress(
            progress_callback,
            phases_state,
            "phase5_review",
            "多视角评审补充",
        )

        if all_cases and supplement:
            all_cases.extend(supplement)

        return all_cases, raw_batches

    # ------------------------------------------------------------------
    # Main orchestrator: 5-phase pipeline
    # ------------------------------------------------------------------

    def generate(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
        image_contexts: list[ImageContext],
        progress_callback: ProgressCallback = None,
        cancel_check: CancelCheck = None,
    ) -> StructuredGenerationResult:
        if image_contexts and not self.llm_client.profile.supports_vision:
            raise ValueError(
                "当前模型配置未开启图片理解能力，请关闭图片上传或更换支持视觉的模型。"
            )

        total_start = time.monotonic()
        profile = self.llm_client.profile
        logger.info(
            "[generate] model=%s  max_output_tokens=%d  pipeline=skill-driven  start",
            profile.model_name,
            profile.max_output_tokens,
        )

        requirement_context = build_requirement_context(requirement_text, document_contexts)
        warnings: list[str] = []
        incomplete_categories: list[str] = []
        raw_batches: list[dict[str, object]] = []

        phases_state: list[dict[str, object]] = [
            {
                "name": "phase1_review",
                "label": "需求评审与模块分解",
                "status": "running",
                "elapsedSeconds": 0,
            }
        ]
        self._emit_progress(
            progress_callback,
            phases_state,
            "phase1_review",
            "需求评审与模块分解",
        )

        self._check_cancel(cancel_check)

        # --- Phase 1: Requirements Review + Module Decomposition ---
        t_phase1 = time.monotonic()
        review = self._phase1_review(requirement_text, document_contexts)
        e1 = int(time.monotonic() - t_phase1)
        phases_state[0]["status"] = "done"
        phases_state[0]["elapsedSeconds"] = e1

        # 构建 Phase2 批量生成的状态（两阶段模式）
        phases_state = [
            {
                "name": "phase1_review",
                "label": "需求评审与模块分解",
                "status": "done",
                "elapsedSeconds": e1,
            },
            {
                "name": "phase2_batch",
                "label": "批量生成测试用例",
                "status": "running",
                "elapsedSeconds": 0,
            },
        ]
        self._emit_progress(
            progress_callback,
            phases_state,
            "phase2_batch",
            "批量生成测试用例",
        )

        self._check_cancel(cancel_check)

        # --- Phase 2: Batch Generation (合并原 Phase3/4/5 为单次调用) ---
        t_phase2 = time.monotonic()
        try:
            smoke_cases, module_cases, review_cases = self._phase2_batch(
                requirement_text, document_contexts, review, warnings
            )
        except Exception as exc:
            # 未知异常，打印日志并更新 phases 状态后继续（让回退逻辑处理）
            logger.warning("[generate] phase2_batch unexpected exception: %s", exc)
            warnings.append(f"批量生成遇到异常：{exc}，已回退到原有管道模式。")
            phases_state[1]["status"] = "done"
            phases_state[1]["elapsedSeconds"] = 0
            self._emit_progress(
                progress_callback,
                phases_state,
                "phase2_batch",
                "批量生成测试用例",
            )
            smoke_cases, module_cases, review_cases = [], [], []
        e2 = int(time.monotonic() - t_phase2)
        phases_state[1]["status"] = "done"
        phases_state[1]["elapsedSeconds"] = e2

        # 如果 Phase2 解析失败（返回空列表），回退到原有的 Phase3/4/5 管道
        if not smoke_cases and not module_cases and not review_cases:
            logger.info("[generate] phase2 batch returned empty, falling back to original pipeline")
            warnings.append("批量生成解析失败，已回退到原有管道模式（分阶段生成）。")
            all_cases, raw_batches = self._generate_original_pipeline(
                requirement_text, document_contexts, review, warnings,
                incomplete_categories, progress_callback, phases_state,
                requirement_context, profile, cancel_check,
            )
        else:
            # Phase2 成功：合并结果
            all_cases: list[TestCaseItem] = list(smoke_cases)
            all_cases.extend(module_cases)
            if review_cases:
                all_cases.extend(review_cases)

            # 记录批量生成的 raw_response
            raw_batches = [
                {
                    "type": "batch",
                    "finish_reason": "batch_generation",
                    "smoke_count": len(smoke_cases),
                    "module_count": len(module_cases),
                    "review_count": len(review_cases),
                }
            ]
            self._emit_progress(
                progress_callback,
                phases_state,
                "done",
                "生成完成",
            )

        # --- Dedupe & Renumber ---
        cases = dedupe_and_renumber(all_cases)
        if not cases:
            raise ValueError("模型未生成有效测试用例，请调整需求描述或模型配置后重试。")

        total_elapsed = time.monotonic() - total_start
        logger.info(
            "[generate] done  total_cases=%d  deduped=%d  elapsed=%.1fs",
            len(all_cases), len(cases), total_elapsed,
        )

        # --- Build metadata ---
        category_counts: dict[str, int] = {}
        module_counts: dict[str, int] = {}
        priority_counts: dict[str, int] = {}
        for case in cases:
            category_counts[case.category] = category_counts.get(case.category, 0) + 1
            if case.module:
                module_counts[case.module] = module_counts.get(case.module, 0) + 1
            priority_counts[case.priority] = priority_counts.get(case.priority, 0) + 1

        review_questions = review.questions

        metadata = GenerationMetadata(
            caseCount=len(cases),
            categoryCounts=category_counts,
            moduleCounts=module_counts,
            priorityCounts=priority_counts,
            reviewQuestions=review_questions,
            warnings=warnings,
            truncated=bool(incomplete_categories),
            incompleteCategories=sorted(set(incomplete_categories)),
        )
        doc_titles = [d.filename for d in document_contexts]
        modules_overview = [(m.id, m.name, m.description) for m in review.modules]
        markdown = build_skill_template_markdown(
            cases,
            metadata,
            requirement_text.strip(),
            doc_titles,
            modules_overview,
        )
        raw_response = json.dumps(
            {
                "reviewResult": {
                    "modules": [
                        {"id": m.id, "name": m.name, "description": m.description, "sub_features": m.sub_features}
                        for m in review.modules
                    ],
                    "questions": [q.model_dump(by_alias=True) for q in review.questions],
                    "business_rules": review.business_rules,
                    "data_constraints": review.data_constraints,
                },
                "promptSnapshot": requirement_context,
                "batches": raw_batches,
                "cases": [case.model_dump(by_alias=True) for case in cases],
                "metadata": metadata.model_dump(by_alias=True),
            },
            ensure_ascii=False,
            indent=2,
        )

        return StructuredGenerationResult(
            markdown=markdown,
            prompt_snapshot=requirement_context,
            raw_response=raw_response,
            model_name=profile.model_name,
            cases=cases,
            metadata=metadata,
        )
