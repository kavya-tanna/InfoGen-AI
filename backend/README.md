# InfoGen AI — Backend

## Gen AI Platform for Automated Content Transformation | SIH PS 26154

### Architecture

```
Frontend (InfoGen_AI.html)
    │
    ▼  POST /api/generate
Backend (FastAPI)
    │
    ├── Ingestion (PDF, DOCX, TXT, URL, Image, Audio, Video)
    │       │
    │       ▼
    ├── Normalization (NormalizedSource)
    │       │
    │       ▼
    ├── Content Intelligence Extraction (AI)
    │       │
    │       ▼
    ├── Format-Specific Generation (7 formats, parallel)
    │       │
    │       ▼
    ├── Schema Validation + Grounding Check
    │       │
    │       ▼
    └── Structured Response
```

### Quick Start

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Configure API key
# Edit backend/.env — paste your NVIDIA NIM API key:
#   NVIDIA_API_KEY=nvapi-your-key-here

# 3. Run the server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 4. Open in browser
# Frontend: http://127.0.0.1:8000/
# API Docs: http://127.0.0.1:8000/docs
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check + provider status |
| `POST` | `/api/generate` | Generate deliverables (JSON or multipart) |
| `POST` | `/api/ingest` | Standalone file upload + extraction |
| `GET` | `/api/jobs/{id}` | Job status |
| `GET` | `/api/outputs/{id}` | Job outputs |

### AI Providers

| Provider | Env Variable | Models |
|----------|-------------|--------|
| **NVIDIA NIM** (default) | `NVIDIA_API_KEY` | DeepSeek V4 Pro, DeepSeek V4 Flash, Nemotron |
| OpenAI | `OPENAI_API_KEY` | GPT-4o, GPT-4o-mini |
| Google Gemini | `GOOGLE_API_KEY` | Gemini 2.0 Flash |
| Anthropic | `ANTHROPIC_API_KEY` | Claude Sonnet |
| Demo | `DEMO_MODE=true` | Mock output (no API key needed) |

### 7 Output Formats

1. **Video Package** — Script, storyboard, scenes, VTT subtitles
2. **LinkedIn Post** — Hook, body, insights, carousel, hashtags
3. **Twitter / X Post** — Tweet, thread, indicators, hashtags
4. **Advisory Document** — Severity, IOCs, impact, mitigation
5. **Infographic** — Layout spec, statistics, sections, colors
6. **Executive Summary** — Headline, takeaways, actions, risks
7. **Presentation Deck** — Slides with speaker notes, visuals

### Testing

```bash
cd backend
pytest tests/ -v
```

### Docker

```bash
# From project root
docker-compose up --build
```

### Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Settings + env vars
│   ├── api/
│   │   ├── routes_generate.py
│   │   ├── routes_health.py
│   │   ├── routes_ingest.py
│   │   └── routes_jobs.py
│   ├── schemas/
│   │   ├── requests.py
│   │   ├── responses.py
│   │   └── outputs.py        # 7 Pydantic output models
│   ├── services/
│   │   ├── ai_provider.py    # NVIDIA/OpenAI/Gemini/Anthropic/Demo
│   │   ├── generator.py      # 7 format generators
│   │   ├── ingestion.py      # PDF/DOCX/TXT/URL extraction
│   │   ├── normalizer.py     # ContentIntelligence
│   │   ├── security.py       # File/URL/injection validation
│   │   └── validator.py      # Schema + grounding validation
│   ├── prompts/
│   │   ├── system/            # System prompts
│   │   └── outputs/           # 7 format prompt templates
│   └── utils/
│       └── logging.py
├── tests/
├── requirements.txt
├── .env
└── Dockerfile
```
