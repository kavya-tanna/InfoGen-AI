# InfoGen AI backend

The verified MVP is FastAPI plus the root `InfoGen_AI.html` frontend.

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
python -m pytest -q
```

Open http://127.0.0.1:8000. NVIDIA primary and Gemini fallback configuration live in the Git-ignored `backend/.env`; see the [main README](../README.md) for setup, the fix breakdown, live verification and demo samples. Each output reports which provider generated it.

Endpoints: `/api/health`, `/api/samples`, `/api/generate`, `/api/ingest`, `/api/export`, `/api/jobs/{id}`, `/api/outputs/{id}`.

Generation accepts JSON or multipart documents. Supported uploads: UTF-8 TXT, text-based PDF and DOCX. Completed outputs are stored in SQLite. The interactive API reference is at `/docs`.
