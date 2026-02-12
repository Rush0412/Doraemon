# Backend (FastAPI)

后端负责量化任务编排、数据落库、回测与分析执行。

## 技术栈

- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- abupy（本地集成源码）

## 启动步骤

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 可选：覆盖数据库连接
# $env:DATABASE_URL="postgresql://postgres:123456@localhost:5432/doraemon"

uvicorn app.main:app --reload --port 8002
```

## 访问地址

- 健康检查：`http://localhost:8002/health`
- Swagger：`http://localhost:8002/api/v1/docs`
- ReDoc：`http://localhost:8002/api/v1/redoc`
- OpenAPI JSON：`http://localhost:8002/api/v1/openapi.json`

## 配置项

`backend/app/config.py`（支持 `.env` 覆盖）：

- `DATABASE_URL`
- `API_PREFIX`（默认 `/api/v1`）
- `CORS_ORIGINS`（默认允许 `http://localhost:5173`）

## 数据库表

- `quant_jobs`：异步任务记录（状态、参数、结果、错误）
- `stock_symbols`：股票/指数基础信息
- `stock_klines`：K 线与衍生字段（含 `atr14/atr21`）

说明：服务启动时会自动执行 `create_all`。

## 主要 API

- `GET /api/v1/quant/symbols`
- `POST /api/v1/quant/symbols/import`
- `POST /api/v1/quant/symbols/manual`
- `GET /api/v1/quant/klines`
- `GET /api/v1/quant/strategies`
- `GET /api/v1/quant/verify`
- `POST /api/v1/quant/kl/update`
- `POST /api/v1/quant/backtest`
- `POST /api/v1/quant/grid-search`
- `POST /api/v1/quant/tools`
- `GET /api/v1/jobs/`
- `GET /api/v1/jobs/{job_id}`
- `DELETE /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/export`

## 返回格式

统一 envelope：

```json
{
  "message": "success",
  "data": {}
}
```
