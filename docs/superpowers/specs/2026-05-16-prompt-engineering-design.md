# 提示词工程优化设计

> **状态**: ⚠️ 待审查
> **日期**: 2026-05-16
> **范围**: 核心测试用例生成链路（testcase_prompt.py）

---

## 1. 背景与动机

### 1.1 当前痛点

| 痛点 | 表现 |
|------|------|
| 生成质量不稳定 | 同一需求多次运行结果差异大，好的时候很好、差的时候需要大量删改 |
| 思考面太宽泛 | 模型在无关维度上发散，面面俱到但不深入，输出很多凑数用例 |
| 无法评估 prompt 优劣 | 改一行 prompt 不知道是变好还是变坏，缺少量化反馈 |

### 1.2 根因分析

- **单体 SYSTEM_PROMPT**：所有 Phase（需求评审、冒烟测试、模块详情、评审补充）共享同一个 System Prompt，一条 prompt 同时定义 4 重角色（产品架构师、测试工程师、开发工程师、产品设计师）和 10 个覆盖维度
- **无结构化思考引导**：模型直接从「任务描述」跳到「输出 JSON」，中间没有推理步骤约束
- **无 Few-Shot 锚定**：纯指令驱动，没有精选示例引导输出格式和质量标准
- **无版本管理**：prompt 嵌入 Python 字符串，改了就改了，无法追溯哪个版本产出了哪批结果

### 1.3 约束条件

- 支持多种模型：DeepSeek、MiniMax、OpenAI 兼容接口
- 先优化核心生成链路（testcase_prompt.py），其他 prompt 模块保持不变
- 向后兼容：现有的 `build_xxx_prompt()` 函数继续工作

---

## 2. 设计目标

1. **聚焦思考**：每个 Phase 有独立的 System Prompt，精准聚焦当前任务
2. **稳定质量**：通过 CoT 思维链 + Few-Shot 示例锚定输出质量
3. **可量化评估**：建立评估数据集和指标体系，每次 prompt 修改可对比效果

---

## 3. 架构设计

### 3.1 目录结构

```
backend/app/prompts/
├── templates/              ← YAML 模板（新增，人类可编辑）
│   ├── phase1_requirement_review.yaml
│   ├── phase2_batch_generation.yaml
│   ├── phase3_smoke.yaml
│   ├── phase4_module_detail.yaml
│   └── phase5_review.yaml
├── examples/               ← Few-Shot 示例库（新增）
│   ├── review_examples.json
│   ├── smoke_examples.json
│   └── detail_examples.json
├── schemas/                ← 输出 JSON Schema（新增）
│   ├── phase1_output.schema.json
│   ├── phase4_output.schema.json
│   └── ...
├── manager.py              ← PromptManager（新增）
├── evaluator.py            ← 评估套件（新增）
│
├── testcase_prompt.py      ← 保留，作为数据组装层
├── submission_prompt.py    ← 不改动
├── quick_prompt.py         ← 不改动
├── append_prompt.py        ← 不改动
├── impact_prompt.py        ← 不改动
└── requirement_translation_prompt.py ← 不改动
```

### 3.2 调用链

```
TestCaseGenerator._phase4_module_detail()
  → build_module_detail_prompt()         ← 组装上下文数据（现有逻辑）
  → PromptManager.render("phase4", ctx)  ← 从 YAML 加载模板 + 注入 context
  → llm_client.create_chat_completion()  ← 调用不变
```

### 3.3 YAML 模板结构

```yaml
# prompts/templates/phase4_module_detail.yaml
name: phase4_module_detail
version: "1.0.0"
description: "模块详细测试用例生成（P2/P3）"

system_prompt:
  default: |
    你是一个资深测试设计专家，专精于单个功能模块的穷尽式测试用例设计。
    核心能力：等价类划分、边界值分析、状态迁移测试、数据组合分析。
    设计原则：一个用例只验证一个测试点；步骤具体到操作级别；预期结果可观测可验证。

cot_template:
  steps:
    - name: 功能理解
      instruction: "理解模块功能：它做什么？用户如何交互？列出输入字段和操作入口。"
    - name: 维度映射
      instruction: "对10个覆盖维度逐一判断是否适用于本模块：正常流程/异常处理/边界值/数据组合/状态流转/权限控制/兼容性/性能并发/安全/用户体验。标注适用/不适用及原因。"
    - name: 测试点识别
      instruction: "基于适用维度，列出所有需测试的具体场景点。穷尽但不重复。"
    - name: 用例设计
      instruction: "为每个测试点设计用例。标题简洁描述意图，步骤可独立执行，预期结果可观测。不明确的用「待确认」标注。"
    - name: 自检
      instruction: "检查：覆盖了所有适用维度？无重复？达到最低数量？每条可独立执行？"

few_shot_examples:
  - id: "ex-001"
    scenario: "表单输入校验"
    tags: ["表单", "校验", "边界值"]

output_schema: phase4_output.schema.json

model_overrides:
  deepseek:
    system_prompt: |
      你现在必须扮演一个资深测试设计专家，专精于...
  minimax:
    system_prompt: |
      你是一个资深测试设计专家。重要：你必须只输出 JSON，不要输出任何解释。
```

---

## 4. 核心设计

### 4.1 Phase 独立 System Prompt

每个 Phase 的 System Prompt 只定义该 Phase 需要的角色和能力：

| Phase | 角色 | 聚焦范围 |
|-------|------|---------|
| Phase1 需求评审 | 需求分析师 | 模块识别 + 模糊点发现 + 业务规则提取 |
| Phase3 冒烟测试 | 冒烟测试专家 | 核心路径 + 关键异常，简洁验证 |
| Phase4 模块详情 | 测试设计专家 | 穷尽覆盖 + 边界挖掘 + 维度适用性判断 |
| Phase5 评审补充 | 质量审计专家 | 遗漏发现 + 多视角补充 + 不重复已有 |

### 4.2 CoT 思维链模板

每个 Phase 的 User Prompt 中嵌入 `<thinking>` XML 块，包含结构化的思考步骤。

设计原则：
- 用 `<thinking>` 标签包裹思考过程，输出只取标签外的 JSON
- 每一步有明确的检查目标，不是笼统的「请思考」
- 自检步骤放在最后，强制模型在输出前验证质量
- 维度适用性判断是关键创新——不让模型对不相关维度硬凑用例

### 4.3 Few-Shot 示例系统

**当前阶段：固定示例（策略 A）**
- 每个 Phase 选 2 条最通用、最具代表性的示例
- 覆盖最常见场景（正常流程 + 边界值/异常处理）
- 示例直接嵌入 YAML 模板，每次调用固定注入

**后续升级：标签匹配（策略 B）**
- 示例库积累到 10+ 条后启用
- 根据需求特征标签（如「表单」「权限」「支付」）匹配最相关示例
- 可扩展到 RAG 检索

### 4.4 PromptManager

```python
class PromptManager:
    def __init__(self, templates_dir: str, examples_dir: str):
        ...

    def render(
        self,
        template_name: str,
        context: dict,
        model_provider: str | None = None,
    ) -> tuple[str, str]:  # (system_prompt, user_prompt)
        """加载模板，渲染 system prompt 和 user prompt（含 CoT）。"""
        ...

    def get_version(self, template_name: str) -> str:
        ...

    def list_templates(self) -> list[dict]:
        ...
```

### 4.5 评估套件

**评估数据集格式**：
```json
{
  "id": "eval-001",
  "requirement": "用户登录功能...",
  "module": {"name": "登录", "sub_features": ["账号密码登录", "验证码登录"]},
  "expected_min_cases": 15,
  "must_cover": ["正常登录", "密码错误", "空输入", "账号不存在"],
  "quality_checks": ["priority_distribution", "no_duplicates", "actionable_steps"]
}
```

**5 个评估指标**：

| 指标 | 计算方式 | 目标 |
|------|---------|------|
| 覆盖率 | must_cover 场景被覆盖的比例 | ≥ 90% |
| 优先级分布 | P0/P1/P2/P3 占比 | P2 为主（40-60%），P0/P1 不超过 30% |
| 去重率 | 用例间 Jaccard 相似度低于阈值 | 相似度 < 0.7 |
| 可执行性 | 步骤数 ≥ 2 + 预期结果非空 | 100% |
| 稳定性 | 同一输入跑 3 次，用例集合 Jaccard 相似度 | ≥ 0.6 |

使用方式：
```bash
python -m app.prompts.evaluator \
  --template phase4_module_detail \
  --dataset eval/datasets/login_scenarios.json
```

---

## 5. 多模型适配

### 5.1 适配策略

| 差异点 | DeepSeek | MiniMax | OpenAI |
|--------|----------|---------|--------|
| System Prompt 敏感度 | 对角色扮演指令更敏感 | 对格式约束指令需更明确 | 标准 |
| JSON 输出策略 | 支持 structured output（部分模型） | 不支持，需 prompt 内强化 | 支持 structured output |
| Context Window | 128K | 128K | 128K |
| Token 预算调整 | 无特殊 | 无特殊 | 无特殊 |

### 5.2 实现方式

YAML 模板中通过 `model_overrides` 字段提供模型特定的 prompt 覆盖。PromptManager 根据传入的 `model_provider` 自动选择对应的 system_prompt。

---

## 6. 迁移计划

### 6.1 阶段一：基础设施（不改行为）

1. 创建 `prompts/templates/` 目录和 YAML 模板文件
2. 实现 `PromptManager` 类
3. 编写评估数据集（至少 3 个典型场景）
4. 实现 `evaluator.py`
5. **验证点**：PromptManager 渲染输出与现有 build 函数一致

### 6.2 阶段二：接入生成管线

1. 修改 `TestCaseGenerator`，在各 Phase 调用前通过 PromptManager 渲染 prompt
2. 保留现有 `build_xxx_prompt()` 作为数据组装层
3. 添加 `model_provider` 参数传递
4. **验证点**：现有功能不受影响，生成结果与优化前可比

### 6.3 阶段三：迭代优化

1. 跑评估基线（当前 prompt 的指标值）
2. 逐个 Phase 优化 Prompt 模板和 CoT 步骤
3. 每次优化后跑评估，对比指标变化
4. 积累 Few-Shot 示例库
5. **验证点**：评估指标持续改善

---

## 7. 不做什么

- 不做 Prompt CMS（数据库存储 + UI 编辑器）
- 不做 A/B 测试框架
- 不做动态 Few-Shot RAG 检索（当前阶段）
- 不修改 submission_prompt / quick_prompt / append_prompt / impact_prompt
- 不修改 llm_client.py 的调用接口
- 不引入新的外部依赖

---

## 8. 成功标准

1. 评估套件可运行，输出 5 项指标数值
2. 优化后 prompt 的覆盖率和稳定性指标不低于当前基线
3. 可执行性指标达到 100%
4. 同一个需求跑 3 次，用例集合 Jaccard 相似度 ≥ 0.6
