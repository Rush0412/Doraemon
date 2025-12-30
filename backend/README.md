# Backend (FastAPI)

This service exposes a RESTful API for task management and demonstrates a fully separated backend for the Doraemon project.

## Setup
1. Create a Python virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure database (PostgreSQL): ensure a database named `doraemon` exists and can be accessed with `postgres/123456` on `localhost:5432`. Override with `DATABASE_URL` if needed.
3. Run the API server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. API docs are available at `http://localhost:8000/api/v1/docs`.

## API contract & JSON envelope
All responses follow a unified schema:
```json
{
  "message": "description",
  "data": {"...": "payload"}
}
```
Errors are returned with appropriate HTTP status codes and the same envelope shape.

### Task schema
- `title` (string, required)
- `description` (string, optional)
- `completed` (boolean, default false)

## Cross-origin & security
CORS is enabled for the local Vite dev server (`localhost:5173`). Adjust `CORS` origins in `app/config.py` for other environments.
