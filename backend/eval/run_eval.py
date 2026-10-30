"""AI 测试用例生成评测脚本

干什么用的：
    用 backend/eval/datasets 里的内置场景跑一遍真实生成流程，统计
    「生成条数 / 重复率 / 必覆盖要点命中率 / 优先级分布 / 字段完整率 / 耗时」，
    把结果打到屏幕上，同时存成 JSON 报告。

怎么跑（在 case-agent 目录下）：
    python backend/eval/run_eval.py              # 跑全部场景
    python backend/eval/run_eval.py --limit 1    # 只跑第 1 个场景，先验证能不能通
    python backend/eval/run_eval.py --model deepseek   # 指定模型

跑出来的数字可以直接写进简历，因为它们是这台机器上真实跑出来的。
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent          # .../backend/eval
BACKEND = HERE.parent                                   # .../backend
ROOT = BACKEND.parent                                   # .../case-agent
DATASETS = HERE / "datasets"
REPORTS = HERE / "reports"


def load_env_file(path: pathlib.Path) -> None:
    """把 .env 里的键值对塞进环境变量。

    项目没装 python-dotenv，这里自己按行读，避免为此多装一个包。
    setdefault 保证命令行里已设置的变量优先。
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(ROOT / ".env")
os.chdir(ROOT)                      # 让项目里那些相对路径能找到东西
sys.path.insert(0, str(BACKEND))

from app.services.llm_client import build_llm_client          # noqa: E402
from app.services.testcase_generator import TestCaseGenerator  # noqa: E402
import app.services.testcase_generator as tg                  # noqa: E402

# ----------------------------------------------------------------------
# 探针：生成管线内部会在最后一步调用 dedupe_and_renumber 去重，
# 去重前的条数在外面拿不到。这里把它换成一个"先记账、再干活"的版本，
# 这样就能算出 LLM 到底多生成了多少条重复的。
# ----------------------------------------------------------------------
_original_dedupe = tg.dedupe_and_renumber
_raw_counts: list[int] = []


def _dedupe_probe(cases):
    _raw_counts.append(len(cases))
    return _original_dedupe(cases)


tg.dedupe_and_renumber = _dedupe_probe

JUDGE_SYSTEM = "你是资深测试专家。只输出 JSON，不要任何解释、不要 Markdown 代码块。"

JUDGE_TEMPLATE = """【需求描述】
{requirement}

【生成的测试用例】
{cases_text}

【必须覆盖的要点清单】
{must_cover}

任务：逐个判断上面每个要点是否被用例覆盖。只要有一条用例是冲着该要点去的就算覆盖，
不要求字面完全一致。

严格按下面的格式输出，不要输出其他任何内容：
{{"covered": ["已覆盖的要点原文"], "missing": ["未覆盖的要点原文"]}}
"""


def extract_json(text: str):
    """从模型回答里抠出 JSON。

    不同供应商的结构化输出能力不一样（有的支持 JSON 模式，有的不支持），
    所以这里不用 response_format，改成从文本里正则提取，三家模型都能用。
    """
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def pct(part: int, whole: int) -> str:
    if not whole:
        return "0%"
    return f"{part / whole * 100:.1f}%"


def evaluate_scenario(generator, llm, scenario: dict) -> dict:
    scenario_id = scenario.get("id", "unknown")
    module_name = (scenario.get("module") or {}).get("name", "")
    requirement = scenario["requirement"]
    must_cover = scenario.get("must_cover", [])
    expected_min = scenario.get("expected_min_cases", 0)

    print(f"\n=== 场景 {scenario_id}（{module_name}）===")
    print("  生成中，单场景通常 1~3 分钟，耐心等一下...", flush=True)

    _raw_counts.clear()
    started = time.monotonic()
    result = generator.generate(requirement, [], [])
    elapsed = time.monotonic() - started

    cases = result.cases
    raw_count = _raw_counts[0] if _raw_counts else len(cases)
    final_count = len(cases)
    duplicates = max(raw_count - final_count, 0)

    # 结构完整：摘要非空、优先级取值合法、模块有值
    complete = sum(
        1
        for c in cases
        if c.summary.strip() and c.priority in {"P0", "P1", "P2", "P3"} and c.module.strip()
    )

    priority_counts = result.metadata.priority_counts or {}
    category_counts = result.metadata.category_counts or {}

    # 用 LLM 当裁判，判定必覆盖要点有没有被覆盖
    covered, missing, judge_error = [], [], None
    if must_cover:
        cases_text = "\n".join(
            f"[{c.priority}] {c.module or '未分类'} | {c.summary}" for c in cases
        )
        prompt = JUDGE_TEMPLATE.format(
            requirement=requirement,
            cases_text=cases_text,
            must_cover="\n".join(f"- {item}" for item in must_cover),
        )
        try:
            raw = llm.create_chat_completion(
                system_prompt=JUDGE_SYSTEM,
                user_content=prompt,
                max_tokens=2000,
            ).content          # 返回的是 ChatCompletionResult 对象，取正文
            verdict = extract_json(raw) or {}
            covered = [x for x in verdict.get("covered", []) if x in must_cover]
            missing = [x for x in verdict.get("missing", []) if x in must_cover]
            missing += [x for x in must_cover if x not in covered and x not in missing]
        except Exception as exc:                      # 裁判挂了不影响主评测
            judge_error = f"{type(exc).__name__}: {exc}"
            missing = list(must_cover)

    hit = len(covered)
    total_points = len(must_cover)

    print(f"  生成条数    : {final_count}（期望下限 {expected_min}）"
          f"{' 达标' if final_count >= expected_min else ' 未达标'}")
    print(f"  去重前/后   : {raw_count} → {final_count}，剔除重复 {duplicates} 条"
          f"（{pct(duplicates, raw_count)}）")
    if total_points:
        print(f"  要点覆盖    : {hit}/{total_points}（{pct(hit, total_points)}）"
              + (f"，漏了：{'、'.join(missing)}" if missing else "，全覆盖"))
    dist = " ".join(f"{k}:{v}" for k, v in sorted(priority_counts.items())) or "无"
    print(f"  优先级分布  : {dist}")
    cats = " ".join(f"{k}:{v}" for k, v in sorted(category_counts.items())) or "无"
    print(f"  类别分布    : {cats}")
    print(f"  字段完整率  : {complete}/{final_count}（{pct(complete, final_count)}）")
    print(f"  耗时        : {elapsed:.1f}s")
    if judge_error:
        print(f"  [裁判调用失败] {judge_error}")

    return {
        "scenario_id": scenario_id,
        "module": module_name,
        "raw_case_count": raw_count,
        "final_case_count": final_count,
        "duplicate_count": duplicates,
        "duplicate_rate": round(duplicates / raw_count, 4) if raw_count else 0.0,
        "expected_min_cases": expected_min,
        "meets_min": final_count >= expected_min,
        "must_cover_total": total_points,
        "must_cover_hit": hit,
        "must_cover_rate": round(hit / total_points, 4) if total_points else None,
        "missing_points": missing,
        "priority_counts": priority_counts,
        "category_counts": category_counts,
        "field_complete_count": complete,
        "field_complete_rate": round(complete / final_count, 4) if final_count else 0.0,
        "elapsed_seconds": round(elapsed, 1),
        "model": result.model_name,
        "warnings": list(result.metadata.warnings or []),
        "cases": [{"priority": c.priority, "module": c.module, "summary": c.summary}
                  for c in cases],
    }


def pick_llm_client(preferred: str | None):
    """逐个试可用供应商，第一个能用的就上。

    三个 Key 用户可能只配了一个，直接 build_llm_client(None) 在拿不到
    默认配置时会抛错，所以这里按优先级兜底。
    """
    candidates = [preferred] if preferred else ["deepseek", "minimax", "openai", None]
    errors = []
    for key in candidates:
        try:
            client = build_llm_client(key)
            if client is not None and getattr(client, "profile", None) is not None:
                return client, key or "项目默认"
        except Exception as exc:
            errors.append(f"{key or '默认'}: {type(exc).__name__}: {exc}")
    raise RuntimeError("没有可用的模型供应商，先检查 .env 里的 API Key。详情：" + " | ".join(errors))


def main() -> int:
    argv = sys.argv[1:]
    limit = None
    model_key = os.environ.get("EVAL_MODEL")

    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    if "--model" in argv:
        model_key = argv[argv.index("--model") + 1]

    files = sorted(DATASETS.glob("*.json"))
    if not files:
        print(f"没找到数据集：{DATASETS}")
        return 1

    scenarios = []
    for path in files:
        scenarios.extend(json.loads(path.read_text(encoding="utf-8")))
    if limit:
        scenarios = scenarios[:limit]

    print(f"共 {len(scenarios)} 个场景，模型：{model_key or '项目默认'}")
    print(f"数据文件：{', '.join(p.name for p in files)}")

    llm, used_key = pick_llm_client(model_key)
    print(f"使用供应商    : {used_key}（实际模型 {llm.profile.model_name}）")
    generator = TestCaseGenerator(llm)

    records = []
    for scenario in scenarios:
        try:
            records.append(evaluate_scenario(generator, llm, scenario))
        except Exception as exc:
            print(f"\n[场景 {scenario.get('id')} 跑挂了] {type(exc).__name__}: {exc}")

    if not records:
        print("一个场景都没跑成功，检查 API Key 和网络。")
        return 1

    n = len(records)
    total_raw = sum(r["raw_case_count"] for r in records)
    total_dup = sum(r["duplicate_count"] for r in records)
    total_points = sum(r["must_cover_total"] for r in records)
    total_hit = sum(r["must_cover_hit"] for r in records)
    total_fields = sum(r["field_complete_count"] for r in records)
    total_cases = sum(r["final_case_count"] for r in records)

    print("\n" + "=" * 46)
    print("汇总（这几个数字可以直接写简历）")
    print("=" * 46)
    print(f"场景数          : {n}")
    print(f"生成用例总数    : {total_cases}，平均 {total_cases / n:.1f} 条/场景")
    print(f"LLM 重复生成率  : {total_dup}/{total_raw} = {pct(total_dup, total_raw)}"
          f"（去重环节剔掉的）")
    if total_points:
        print(f"要点覆盖命中率  : {total_hit}/{total_points} = {pct(total_hit, total_points)}")
    print(f"字段完整率      : {total_fields}/{total_cases} = {pct(total_fields, total_cases)}")
    print(f"总耗时          : {sum(r['elapsed_seconds'] for r in records) / 60:.1f} 分钟")
    print(f"模型            : {records[0]['model']}")

    all_missing = [m for r in records for m in r["missing_points"]]
    if all_missing:
        print(f"\n漏掉的要点（这就是面试能讲的 Bad Case）：")
        for item in all_missing:
            print(f"  - {item}")

    REPORTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS / f"eval_{stamp}.json"
    report_path.write_text(
        json.dumps({"created_at": stamp, "model": model_key, "records": records},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n报告已保存：{report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
