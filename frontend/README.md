# Frontend (Vue3 + Vite)

This Vite-powered Vue3 SPA consumes the FastAPI backend via REST.

## Getting started
```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` calls to `http://localhost:8000` (see `vite.config.js`).

## Architecture
- **State**: Pinia store at `src/stores/taskStore.js` keeps task list and loading flags.
- **Routing**: Vue Router with a single `TaskBoard` route; more views can be added under `src/router`.
- **API client**: Axios instance at `src/services/api.js` enforces JSON headers and unified error messages.
- **UI**: `TaskBoard.vue` handles CRUD interactions and demonstrates the API contract.
