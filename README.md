# 内部智能测试用例生成助手（MVP）

一个面向测试团队的轻量级 Web 工具：输入需求描述，上传参考文档或图片，自动生成 Markdown 表格形式的测试用例，供测试工程师评审和修改。

## 当前能力
- 单页 Web 界面，支持输入需求描述。
- 支持上传文档：`txt`、`md`、`pdf`、`docx`。
- 支持上传图片并作为多模态输入发送给兼容模型。
- 通过 OpenAI 兼容接口调用大模型生成测试用例。
- 结果以 Markdown 表格渲染展示，并支持一键复制。
- 保存生成记录、附件元数据和原始模型响应，便于后续扩展知识库与反馈闭环。

## 技术栈
- 后端：`FastAPI` + `SQLAlchemy`
- 前端：`React` + `Vite` + `TypeScript` + `Ant Design`
- 数据库：开发可用 SQLite，部署推荐 PostgreSQL
- 模型接入：OpenAI 兼容接口

## 目录结构
```text
backend/
  app/
  tests/
frontend/
  src/
Dockerfile
docker-compose.yml
.env.example
```

## 环境变量
从 `.env.example` 复制生成 `.env`，再填入真实值：

```bash
cp .env.example .env
```

关键变量：
- `LLM_BASE_URL`：OpenAI 兼容 API 地址
- `LLM_API_KEY`：模型密钥，只放在环境变量中，不写入代码
- `LLM_MODEL`：模型名称，例如 `gpt-4o-mini`
- `DATABASE_URL`：数据库连接串

## 本地开发

### 1. 启动后端
建议使用 Python 3.12：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
uvicorn app.main:app --app-dir backend --reload
```

默认启动后端地址：`http://localhost:8000`

### 2. 启动前端
```bash
cd frontend
npm install
npm run dev
```

默认启动前端地址：`http://localhost:5173`

开发模式下，Vite 会将 `/api` 请求代理到后端。

## Docker Compose 启动
适合内网服务器单机部署：

```bash
cp .env.example .env
docker compose up --build
```

启动后访问：
- 应用：[http://localhost:8000](http://localhost:8000)
- 健康检查：[http://localhost:8000/api/health](http://localhost:8000/api/health)

## API 说明

### `POST /api/v1/generate`
`multipart/form-data`

字段：
- `requirement_text`：需求描述，必填
- `documentFiles`：参考文档，可多传
- `imageFiles`：参考图片，可多传

成功返回示例：
```json
{
  "generationId": "uuid",
  "markdown": "| 用例ID | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | ...",
  "modelName": "gpt-4o-mini",
  "attachmentCount": 2,
  "createdAt": "2026-04-03T00:00:00Z"
}
```

## Prompt 设计
系统 Prompt 固定 AI 角色为资深测试工程师，并明确要求：
- 仅输出 Markdown 表格
- 列固定为：`用例ID`、`测试标题`、`前置条件`、`测试步骤`、`预期结果`
- 尽量覆盖正常流程、异常流程、边界条件和输入校验

实现位置：
- `backend/app/prompts/testcase_prompt.py`

## 已知限制
- 扫描版 PDF 暂不保证高质量文本提取。
- 图片理解依赖所接入模型具备视觉能力；若不支持，请关闭图片上传或更换模型。
- 当前只做单轮生成，不保留前端会话上下文。
