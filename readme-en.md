# Doraemon

A front-end/back-end quantitative trading system built on top of local `abupy` integration.

This repository is now a runnable quant workstation:

- Frontend for interaction and visualization
- Backend for async jobs, data persistence, backtesting, and analysis

## Current Capabilities

- Symbol search and portfolio selection in UI
- Async job queue (`queued/running/succeeded/failed`)
- Market symbol import and K-line update into PostgreSQL
- Backtesting with configurable buy/sell strategies
- Grid search with `none` / `holdout` / `walk_forward`
- Quant analysis tools (support/resistance, correlation, distance, gap, etc.)
- Job export in JSON/CSV

## Architecture

```text
frontend (Vue3 + Vite + Pinia + lightweight-charts)
        |
        |  /api/v1/*
        v
backend (FastAPI + SQLAlchemy + ThreadPoolExecutor)
        |
        |  calls
        v
local abupy source (strategy/backtest/analysis)
        |
        v
PostgreSQL (quant_jobs / stock_symbols / stock_klines)
```

## Repository Layout

- `frontend/`: SPA quant workstation
- `backend/`: FastAPI service and job runtime
- `backend/app/routes.py`: core API + job execution logic
- `backend/app/strategies.py`: custom MACD factors
- `abupy/`: local integrated ABU framework source
- `abupy_lecture/`, `abupy_ui/`, `ipython/`: legacy tutorials and notebooks

## Requirements

- Python 3.10+
- Node.js 18+
- PostgreSQL 13+

## Quick Start

### 1) Prepare PostgreSQL

Default DB name is `doraemon`.

Default backend DSN in `backend/app/config.py`:

`postgresql://postgres:123456@localhost:5432/doraemon`

Override with `DATABASE_URL` if needed.

### 2) Start backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# optional override:
# $env:DATABASE_URL="postgresql://postgres:123456@localhost:5432/doraemon"

python -m uvicorn app.main:app --reload --port 8002
```

Available URLs:

- Health: `http://localhost:8002/health`
- Swagger: `http://localhost:8002/api/v1/docs`
- ReDoc: `http://localhost:8002/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8002/api/v1/openapi.json`

### 3) Start frontend

```powershell
cd frontend
npm install
npm run dev
```

Open: `http://localhost:5173`

`frontend/vite.config.js` proxies `/api` to `http://localhost:8002` by default.  
You can override with `VITE_API_TARGET`.

## User Workflow (Recommended)

### 0. Environment Check

Click verify in UI, which calls:

- `GET /api/v1/quant/verify`

It creates a `verify` job and returns Python/abupy availability info.

### 1. Data Preparation

- Import symbols by market
- Search symbols and build your selection basket
- Start K-line update:
  - `POST /api/v1/quant/kl/update`

Common params:

- `market`: `SH` / `SZ` / `300` / `CN` / `US` / `HK`
- `symbols`: comma-separated list (e.g. `sh600036,sz000001`)
- `all`: `true` for full-market update
- `start` / `end`: `YYYY-MM-DD`
- `n_folds`: lookback years

### 2. Backtest

Run:

- `POST /api/v1/quant/backtest`

Main outputs:

- `summary`: return/win-rate/sharpe/drawdown and other stats
- `orders`: order preview (up to 200 rows)
- `actions`: action preview (up to 200 rows)

Strategy IDs (current backend):

- Buy: `breakout` `momentum_break` `double_ma` `up_down_trend` `up_down_golden` `down_up_trend` `week_win` `put_break` `put_xdbk` `macd_cross`
- Sell: `atr_stop` `atr_close` `atr_pre` `sell_break` `sell_xdbk` `sell_n_day` `double_ma_sell` `macd_cross`

### 3. Grid Search

Run:

- `POST /api/v1/quant/grid-search`

Supports:

- Multi buy/sell strategy combinations
- Param grid (`buy_params_grid` / `sell_params_grid`)
- Validation modes: `none` / `holdout` / `walk_forward`
- Run cap: `max_runs`

`best` result can be applied back to backtest form.

### 4. Quant Tools

Run:

- `POST /api/v1/quant/tools`

Supported tools:

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

`support_resistance` also returns `signal` with action hints (`breakout`, `near_support`, etc.) and stop-loss/take-profit references.

### 5. Jobs and Export

All jobs are centrally managed:

- `GET /api/v1/jobs/`
- `GET /api/v1/jobs/{job_id}`
- `DELETE /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/export?format=json|csv&section=...`

Typical exports:

- Orders CSV: `section=orders`
- Actions CSV: `section=actions`

## API Quick Reference

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

All responses follow a unified envelope:

```json
{
  "message": "success",
  "data": {}
}
```

## FAQ

- Which markets are available in frontend?
- Current UI is mainly configured for A-share flows (`SH/SZ/300`). Backend APIs also support `US/HK`.

- Backtest says no K-line data, what should I do?
- Run `kl_update` first, and widen date range (or leave `start/end` empty).

- Do I need manual SQL migrations for first run?
- No. Tables are created automatically on backend startup via `create_all`.

## Legacy Materials

If you still need the original ABU tutorials:

- `abupy_lecture/`
- `abupy_ui/`
- `ipython/`
- `python/`

## License

See `LICENSE`.
