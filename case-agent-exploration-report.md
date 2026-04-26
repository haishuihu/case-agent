# AI Test Design Workbench — 项目探索报告

> 基于逐文件审查分析
> 分析日期：2026-04-26

---

## 第一部分：工作流不合理环节

### 1.1 数据模型与数据库 Schema 不一致

**严重性：高** — 可能导致运行时错误或数据损坏

| 实体 | ORM 模型字段 | migrate.py 创建的 Schema | 问题 |
|------|-------------|------------------------|------|
| `CaseReview` | `review_status`, `completeness_score`, `executability_score`, 等 | 匹配 | ✅ 一致 |
| `ReviewComment` | `author`, `content`, `case_id`, `case_title`, `parent_comment_id` | 匹配 | ✅ 一致 |
| `Defect` | `submission_id`, `recommendation_id`, `execution_id`, `browser`, `environment`, `root_cause` | 匹配 | ✅ 一致 |
| **技术文档 vs 实际** | `docs/后端技术实施方案.md` 描述包含 `generation_id`, `case_id`, `case_title`, `reproduction_steps`, `expected_result`, `actual_result`, `regression_status`, `ai_analysis` 的 `Defect` 模型 | 实际 Defect 完全不同 | ❌ **严重偏差** — 技术文档与代码完全不同 |

**主要差异（技术文档 vs 实际代码）：**
- 技术文档描述 Defect 关联 `execution_records` + `generation_records`，具有 `reproduction_steps`, `expected_result`, `actual_result`
- 实际 Defect 模型关联 `submissions`，具有 `browser`, `environment`, `root_cause`
- **结论**：文档描述了一个"从执行创建缺陷"的模型，代码实现了一个"从提测/回归创建缺陷"的模型。两者讲的是不同的故事。

### 1.2 API 前缀 Bug — `quick_generate_history.py`

**严重性：高** — 此路由完全不可访问

```python
# backend/app/api/routes/quick_generate_history.py 第16行
router = APIRouter(prefix="/api/v1/generate/quick", tags=["quick-generate"])
```

而主路由器已经在 `/api/v1` 下挂载此路由器：

```python
# backend/app/api/router.py
api_router.include_router(quick_history_router)  # 没有额外的 /api/v1
```

在 `main.py` 中，路由器挂载在 `settings.api_v1_prefix`（即 `/api/v1`）：

```python
app.include_router(api_router, prefix=settings.api_v1_prefix)
```

**结果 URL**: `/api/v1/api/v1/generate/quick/history` — ❌ 双 `/api/v1`

**影响**：历史记录快速生成的查看和清除功能通过正确的 URL 无法访问。然而，实际快速生成端点（在 `generate.py` 中，`POST /api/v1/generate/quick`）工作正常，因为它是在 `generate.py` 中定义的，那里使用 `router = APIRouter(tags=["generate"])` 且没有额外的前缀。

### 1.3 AI 评审结果序列化 — 架构不匹配

**严重性：中** — 可能导致前端数据渲染静默失败

**后端流程**：
1. `case_review.py` 中的 `run_ai_review()` 调用 `CaseReviewService.run_ai_review()`
2. 那返回一个包含 `dimensions` 的字典，该字典是字典列表（`{dimension, label, score, description}`）
3. 该字典通过 `_serialize_ai_details_from_dict(ai_result)` 序列化为 JSON 字符串
4. 存储为 `review.ai_review_details`
5. 当通过 `_review_to_response()` 检索时，`_deserialize_ai_details(review.ai_review_details)` 尝试将 JSON 解析为 `AIReviewResult`
6. 但 `AIReviewResult` 期望 `dimensions: list[AIReviewDimension]`，而实际的 JSON 有 `dimensions: list[dict]`

**问题**：`_deserialize_ai_details()` 直接调用 `AIReviewResult(**data)`，这将尝试 Pydantic 验证。如果维度字典缺少 `label` 或 `description` 字段，这可能会失败。此外，`CaseReviewResponse.ai_review_details` 的类型是 `Optional[AIReviewResult]`，这意味着 Pydantic 根据 JSON 数据构造 `AIReviewResult`，如果合适的话会进行字段名转换。这可能有效，但在边缘情况下可能因字段不匹配而静默失败。

### 1.4 缺失专用 `DefectService`

**严重性：中** — 业务逻辑泄漏到路由层

技术实施文档规划了 `defect_service.py`，但实际中：
- 所有缺陷 CRUD 直接在 `defect.py` 路由中处理
- 只有 `create_defect_from_execution` 使用服务的 `ExecutionTracker.create_defect_from_execution()`
- 缺少 `DefectAnalysisService`（AI 辅助分析）— 技术文档中规划但未实现
- 缺陷状态流转在路由层硬编码 — 对于工作流扩展不利

### 1.5 令人困惑的双重影响分析端点

**严重性：低** — 功能重复的设计问题

存在两个影响分析路径：

| 端点 | 位置 | 功能 |
|--------|----------|------|
| `POST /api/v1/submissions/checklist/impact` | `submission.py` 路由 | 使用 ChecklistGenerator 的简单分析 |
| `POST /api/v1/impact-analysis` | `impact.py` 路由 | 使用 ImpactAnalyzer + RegressionRecommender 的完整分析 |

前端两者都使用：
- `analyzeImpact()`（在 `submission.ts` 中）→ 简单端点，在 `SubmissionForm.tsx` 中用于 AI 生成 Checklist 前的预览
- `createImpactAnalysis()`（在 `impact.ts` 中）→ 完整端点，在 `SubmissionDetailPage.tsx` 中用于深度分析

**问题**：简单端点（在 submission 路由器上）调用 `ChecklistGenerator.analyze_impact()`，它调用 LLM 进行分析。完整端点（在 impact 路由器上）调用 `ImpactAnalyzer.analyze()`，它执行代码解析、依赖图分析和 LLM 分析。两者都返回类似的结果结构，但实现完全不同。这种职责分离不明确。

### 1.6 前端路由与实际导航不一致

**严重性：低** —  UI/UX 不一致

- 前端技术方案规划了 `/submissions/new` 用于创建
- 实际实现使用 `/submissions?mode=create`
- 这并不破坏，但与文档不同，如果任何外部链接期望 `/submissions/new` 格式，可能会感到困惑

### 1.7 代码中缺少 `review_prompt.py`

**严重性：低** — 提示管理不一致

技术实施文档规划了 `prompts/review_prompt.py` 用于 AI 评审提示，但实际中 `ai_reviewer.py` 服务可能在其代码中包含提示逻辑，使得在不同模型间定位和维护提示更加困难。

---

## 第二部分：半成品功能模块

### 2.1 用例评审 — 有骨架但操作流程缺失

**状态**: ⚠️ 部分实现

**已经实现的**：
- ✅ 完整数据模型（`CaseReview`, `ReviewComment`）
- ✅ 完整 CRUD API（创建、列表、获取、更新、删除评审 + 评论处理）
- ✅ AI 评审 API（`POST /reviews/ai-review`）
- ✅ 前端列表页面（`ReviewListPage.tsx`）带有详情弹窗和状态管理
- ✅ 前端服务层（`review.ts`）

**缺失的**：
- ❌ 前端"新建评审"页面/表单 — "新建评审"按钮仅导航到 `"/"`（主生成页），没有一个合适的表单来输入 `generation_id`、需求文本、生成的用例来创建评审
- ❌ 前端发起 AI 评审的功能 — 没有 UI 控件来调用 `POST /reviews/ai-review`
- ❌ 用例行内评论 — 评论 API 存在但前端列表页面没有实现评论 UI
- ❌ 评审与生成页面的集成 — 用户生成用例后，没有"提交评审"的按钮将用例发送到评审流程

### 2.2 缺陷管理 — 基本 CRUD 但缺少关键集成

**状态**: ⚠️ 部分实现

**已经实现的**：
- ✅ 完整数据模型（`Defect`）
- ✅ 完整 CRUD API 和前端页面（列表、创建、详情、状态流转）
- ✅ "从执行创建缺陷"的 API（`POST /defects/from-execution`）

**缺失的**：
- ❌ **没有 AI 辅助缺陷分析** — `DefectAnalysisService`（技术文档中规划）不存在，缺少自动复现步骤生成、根因推荐或缺陷聚类
- ❌ **没有用例-缺陷关联** — 缺陷模型有关联字段（`execution_id`, `recommendation_id`），但前端 UI 没有显示此关系，也没有从用例详情导航到相关缺陷的功能
- ❌ **缺陷创建未与执行结果集成** — `createDefectFromExecution` API 存在，但没有前端 UI 从执行失败直接创建缺陷的一键流程
- ❌ **缺陷修复后没有自动"待回归"标记** — 技术文档中规划的功能

### 2.3 缺失 Sprint 1 功能（用例版本管理和标签系统）

**状态**: ❌ 未实现

根据 `docs/需求挖掘与迭代计划.md`，Sprint 1 包含：

| 功能 | 计划 | 状态 |
|---------|--------|--------|
| `TestCaseVersion` 模型 | 存储用例快照、支持版本对比 | ❌ 不存在 |
| 版本对比 UI | Diff 展示 | ❌ 不存在 |
| `Tag` 模型 | 名称/类型/颜色，多对多关联用例 | ❌ 不存在 |
| 标签管理 API | 标签 CRUD | ❌ 不存在 |
| 标签分类 | 预设+自定义标签 | ❌ 不存在 |

**影响**：项目没有版本管理或标签基础设施，这意味着无法追踪用例随时间的变化或按自定义维度组织用例。

### 2.4 缺失 Sprint 2 功能（通用执行追踪）

**状态**: ❌ 未实现（回归特定执行存在）

**规划中的**：
- `ExecutionRecord` 模型 — 通用的执行记录，包含状态、结果、附件
- `TestPlan` 模型 — 测试计划管理
- 批量执行状态更新
- Excel 导入/导出

**实际存在的**：
- `RegressionExecution` — 紧密绑定到回归推荐，不是一个通用的执行记录
- 没有 `TestPlan` 模型
- 没有批量导入/导出 API

**影响**：执行追踪仅适用于回归推荐上下文。用户无法将生成的测试用例标记为"通过/失败"，按计划组织用例，或从外部工具导入执行结果。

### 2.5 缺失 Sprint 3 功能（缺陷 AI 分析）

**状态**: ❌ 未实现

技术文档详细描述了：
- `DefectAnalysisService` 用于 AI 辅助分析
- AI 生成复现步骤
- AI 基于历史数据推荐可能原因
- 缺陷聚类以识别相同根本原因

实际代码中这些都没有实现。缺陷是一个基本的 CRUD 功能，没有 AI 加持。

### 2.6 缺失 Sprint 4 功能（全链路测试覆盖）

**状态**: ❌ 未实现

完全没有实现：
- 接口测试用例生成
- 性能测试场景生成
- 安全测试用例生成
- 自动化脚本生成

### 2.7 缺失 Sprint 5 功能（知识图谱与报告）

**状态**: ❌ 部分实现

**知识库**（✅ 存在——完整实现具有 RAG、向量嵌入、全文搜索）
**知识图谱**（❌ 不存在——没有 `Requirement` 模型、没有需求-用例关系、没有图谱可视化）
**测试报告**（❌ 不存在——没有 `ReportGenerationService`）

### 2.8 对比 Sprint 规划 — 看板

| Sprint | 已实现的任务 | 缺失的任务 |
|--------|----------------|-------------|
| **Sprint 0**: 快速生成 | 快速模式、追加生成 | — |
| **Sprint 1**: 质量门禁+评审 | 提测申请 CRUD, AI Checklist, 门禁状态、CaseReview 模型+API, ReviewComment API | 用例版本管理、标签系统、前端评审创建流程 |
| **Sprint 2**: 影响分析+回归 | 变更解析、依赖图、回归推荐、回归执行 | 通用 `ExecutionRecord`、`TestPlan`、批量导入/导出 |
| **Sprint 3**: 缺陷管理 | 缺陷 CRUD、"从执行创建" API、前端列表+创建 | AI 辅助分析（复现步骤、根因推荐、聚类） |
| **Sprint 4**: 全链路测试 | — | 接口、性能、安全、自动化生成 |
| **Sprint 5**: 知识图谱 | 知识库文档管理（独立功能） | `Requirement` 模型、需求-用例关联、图谱可视化、`ReportGenerationService` |

---

## 第三部分：其他发现

### 3.1 死代码 / 冗余模式

- `append_generate.py` 模型存在且有迁移，但 `AppendGenerateRecord` 正在被使用（在 generate.py 路由的 append 端点中），所以不是死代码

### 3.2 配置 Issue

- `ModelProfile` 中 OpenAI 的 `max_output_tokens` 默认为 `131_072`，这在大多数 OpenAI 模型中不支持（gpt-4o-mini 限制为 16K）。这可能导致静默截断或 API 错误。
- `ModelProfile` 配置中没有 OpenAI 供应商条目，但配置有 `llm_base_url`, `llm_api_key` 等，这些在 `get_model_profiles()` 中没有映射——这意味着 OpenAI 通道默认没有可用的模型配置。

### 3.3 前端重复的 jsonRequest 模式

- `submission.ts`, `defect.ts`, `impact.ts`, `regression_execution.ts` 各自复制粘贴相同的 `jsonRequest` 和 `API_BASE_URL` 逻辑
- `api.ts` 中的共享 `jsonRequest` 函数更健壮（HTML 检测、更好的错误消息）
- 但 `review.ts` 使用了 `api.ts` 的 `jsonRequest`，而其他服务文件重新实现了它
- 这造成不一致的错误处理和用户体验

---

## 总结

该项目的核心能力（测试用例生成、知识库 RAG、提测质量门禁、变更影响分析、回归推荐）**健壮且完全实现**。但扩展功能（评审、缺陷、执行追踪）更像**带骨架的半成品**——数据库模型和 API 端点存在，但缺少至关重要的前端集成和用户工作流。

最紧迫的问题：
1. 🔴 `quick_generate_history.py` 中的**双 `/api/v1` 前缀 bug** 使两个 API 端点无法访问
2. 🟠 **前端缺少评审创建流程**使得用例评审功能实际上无法使用
3. 🟠 **AI 评审结果序列化**可能因 Pydantic 验证问题在边缘情况下失败
4. 🟡 **代码和文档在 Defect 模型上的差异**表明规划与执行之间存在脱节
5. 🟡 整个 Sprint 1 功能（版本、标签）**从未实现**，留下重大技术债务
