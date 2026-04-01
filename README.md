# haoxhealth_ai

一个面向 **1k 并发连接** 的通用聊天机器人工程骨架：
- 后端：FastAPI + SSE流式 + MCP工具网关
- 前端：Next.js 聊天页面 + 工具事件展示
- 功能：自动工具调用（高德路线、知识库检索）、异步深度研究任务

## 目录结构

- `backend/` FastAPI 服务
- `frontend/` Next.js 应用

## 后端启动

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

可选环境变量（`backend/.env`）：

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## 前端启动

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000/api npm run dev
```

## 核心接口

- `POST /api/chat/{session_id}/stream` 聊天流式输出（SSE）
- `GET /api/tools` 工具目录
- `POST /api/tools/execute` 工具执行（受控）
- `POST /api/research/jobs` 创建深度研究任务（异步）
- `GET /api/research/jobs/{job_id}` 查询任务
- `GET /api/research/jobs/{job_id}/result` 获取研究结果

## 测试脚本样例

### 自动化测试（推荐）

```bash
cd backend
pytest -q
```

覆盖点：
- 健康检查与工具目录
- 工具执行成功/参数错误
- 聊天流式事件完整性（含自动工具调用）
- 深度研究任务生命周期

### 手工冒烟脚本

```bash
cd backend
python scripts/smoke_demo.py
```

该脚本会依次调用 `/health`、`/tools`、`/tools/execute` 与 `/chat/.../stream`，打印结果用于快速验收。

## 当前实现说明

- 默认模型：`qwen-plus`（可在请求中覆盖）
- `tool_mode=auto`：根据对话意图自动触发工具
- 路线规划工具：`amap_route_plan`（当前为可替换的适配器桩实现）
- 知识库检索：`kb_search`（当前为Milvus链路桩实现）
- 深度研究：异步任务状态机（queued/planning/searching/synthesizing/completed）
