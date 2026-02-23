# Doraemon

基于 `abupy` 的前后端分离量化交易系统。  
当前项目已从“单体教程仓库”升级为“可交互的量化工作台”：前端负责交互与可视化，后端负责任务编排、数据落库与回测/分析执行。

## 当前能力

- 前端交互选股、保存组合、发起量化任务
- 后端异步任务队列（`queued/running/succeeded/failed`）
- 股票数据导入与 K 线更新（写入 PostgreSQL）
- 回测（买入/卖出策略可配置）
- 网格寻优（支持 `holdout` / `walk_forward`）
- 量化分析工具（支撑阻力、相关性、距离矩阵、跳空等）
- 任务结果导出（JSON/CSV）

## 架构概览

```text
frontend (Vue3 + Vite + Pinia + lightweight-charts)
        |
        |  /api/v1/*
        v
backend (FastAPI + SQLAlchemy + ThreadPoolExecutor)
        |
        |  调用
        v
abupy 本地源码（策略/回测/量化分析）
        |
        v
PostgreSQL（quant_jobs / stock_symbols / stock_klines）
```

## 目录说明

- `frontend/`：前端 SPA，主界面为量化工作台
- `backend/`：FastAPI 服务与任务执行逻辑
- `backend/app/routes.py`：核心 API 与任务执行入口
- `backend/app/strategies.py`：自定义 MACD 策略因子
- `abupy/`：本地集成的 ABU 量化框架
- `abupy_lecture/`、`abupy_ui/`、`ipython/`：历史教程与 Notebook 资料

## 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 13+

## 快速启动

### 1. 启动 PostgreSQL 并创建数据库

数据库名默认是 `doraemon`。  
后端默认连接串在 `backend/app/config.py` 中：

`postgresql://postgres:123456@localhost:5432/doraemon`

你可以通过环境变量 `DATABASE_URL` 覆盖它。

### 2. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# 可选：覆盖数据库连接
# $env:DATABASE_URL="postgresql://postgres:123456@localhost:5432/doraemon"

python -m uvicorn app.main:app --reload --port 8002
```

启动后可访问：

- OpenAPI 文档：`http://localhost:8002/api/v1/docs`
- 健康检查：`http://localhost:8002/health`

### 3. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

访问：`http://localhost:5173`

说明：`frontend/vite.config.js` 默认把 `/api` 代理到 `http://localhost:8002`。  
如果你把后端跑在其他端口，请设置 `VITE_API_TARGET`。

## 使用手册（推荐流程）

### 0. 环境验证

在页面点击“环境验证”，会调用 `GET /api/v1/quant/verify`，生成 `verify` 任务并返回 Python 与 abupy 可用性信息。

### 1. 数据准备

- 在“数据准备”页导入股票池（按市场导入）
- 检索股票并加入“选股篮”
- 启动 K 线更新任务（`POST /api/v1/quant/kl/update`）

常用参数：

- `market`: `SH` / `SZ` / `300` / `CN` / `US` / `HK`
- `symbols`: 逗号分隔代码（如 `sh600036,sz000001`）
- `all`: `true` 时按市场全量更新
- `start` / `end`: `YYYY-MM-DD`
- `n_folds`: 回溯年数

### 2. 策略回测

在“策略验证”页配置标的、资金、买卖策略与参数后，发起：

- `POST /api/v1/quant/backtest`

主要输出：

- `summary`：收益、胜率、夏普、回撤等摘要
- `orders`：交易明细（预览最多 200 条）
- `actions`：行为明细（预览最多 200 条）

当前策略 ID（与后端一致）：

- 买入：`breakout` `momentum_break` `double_ma` `up_down_trend` `up_down_golden` `down_up_trend` `week_win` `put_break` `put_xdbk` `macd_cross`
- 卖出：`atr_stop` `atr_close` `atr_pre` `sell_break` `sell_xdbk` `sell_n_day` `double_ma_sell` `macd_cross`

### 3. 参数寻优（Grid Search）

在“参数交叉验证”页发起：

- `POST /api/v1/quant/grid-search`

支持：

- 多买卖策略组合并行评分
- 参数网格（`buy_params_grid` / `sell_params_grid`）
- 验证模式：`none` / `holdout` / `walk_forward`
- 最大运行次数限制：`max_runs`

结果中 `best` 可一键回填到回测表单。

### 4. 量化分析工具

在“量化分析工具”页发起：

- `POST /api/v1/quant/tools`

支持工具：

- `support_resistance`
- `jump_gap`
- `trend_speed`
- `shift_distance`
- `regress`
- `price_channel`
- `golden_ratio`
- `correlation`
- `distance`
- `p_change_stats`
- `date_week_wave`
- `date_week_win`
- `bcut_change_vc`
- `qcut_change_vc`
- `wave_change_rate`

其中 `support_resistance` 会生成 `signal`，给出动作建议（如 `breakout` / `near_support`）和止损止盈参考价。

### 5. 任务管理与导出

所有任务都进入统一任务表：

- 列表：`GET /api/v1/jobs/`
- 详情：`GET /api/v1/jobs/{job_id}`
- 删除：`DELETE /api/v1/jobs/{job_id}`
- 导出：`GET /api/v1/jobs/{job_id}/export?format=json|csv&section=...`

常见导出：

- 订单 CSV：`section=orders`
- 行为 CSV：`section=actions`

## 核心 API 速查

- `GET /api/v1/quant/symbols`：检索股票/指数
- `POST /api/v1/quant/symbols/import`：批量导入股票池
- `POST /api/v1/quant/symbols/manual`：手动写入股票池
- `GET /api/v1/quant/klines`：读取 K 线
- `GET /api/v1/quant/strategies`：获取策略目录
- `GET /api/v1/quant/verify`：环境验证任务
- `POST /api/v1/quant/kl/update`：K 线更新任务
- `POST /api/v1/quant/backtest`：回测任务
- `POST /api/v1/quant/grid-search`：参数寻优任务
- `POST /api/v1/quant/tools`：量化分析任务

说明：接口统一返回结构为 `{ "message": "...", "data": ... }`。

## 常见问题

- 前端能选哪些市场？
- 当前页面主要面向 A 股（`SH/SZ/300`）。后端接口本身支持 `US/HK`，可通过 API 直接调用。

- 回测报“无可用 K 线”怎么办？
- 先执行一次 `kl_update`，并适当扩大时间范围（可不填 `start/end`）。

- 第一次启动是否需要手工建表？
- 不需要。`backend/app/main.py` 启动时会自动 `create_all`。

## 历史资料

如果你还需要原始 ABU 教程与 Notebook：

- `abupy_lecture/`
- `abupy_ui/`
- `ipython/`
- `python/`

## License

本项目遵循仓库内 `LICENSE`。
