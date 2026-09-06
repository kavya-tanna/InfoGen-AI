# ⚡ InfoGen AI — Automated Multi-Format Content Transformation Engine

> **Smart India Hackathon (SIH) · Gen AI Automated Content Transformation Platform**  
> Ingest raw complex intelligence (documents, reports, cyber advisories, whitepapers) and automatically transform it into **7 audience-tailored, multi-modal deliverables** with strict source grounding and zero hallucination.

---

## 🌟 Highlights & Key Capabilities

Transform any source document (PDF, DOCX, TXT) or raw text into **7 distinct production-ready deliverables**:

1. **🎬 Video Production Package**:
   - Built-in interactive **16:9 Canvas Video Player** with animated cyber grid, real-time dynamic typography, and scene progress tracking.
   - Synchronized **Web Speech API narration** with voice toggle (`🔊 Voice: ON/OFF`).
   - Scene-by-scene production storyboard with camera and visual directions.
   - Real-time video export to `.webm` via browser MediaRecorder, plus valid `.vtt` subtitles and `.txt` scripts.
2. **📊 Content-Rich PowerPoint Slide Deck (`.pptx`)**:
   - Generates 6–8 comprehensive, executive-ready slides with category pill badges (`STRATEGIC OVERVIEW`, `TECHNICAL ANALYSIS`, `METRICS & TELEMETRY`, etc.).
   - Includes structured insight cards, executive takeaway boxes, and detailed presenter speaker notes.
   - Automatically embeds custom high-resolution visual diagrams generated via Pillow:
     - *System Architecture & Data Flow*
     - *Quantitative Telemetry & SLA Benchmarks*
     - *Threat Surface & Risk Severity Matrix*
     - *Phased Implementation Roadmap*
     - *Executive Decision & Governance Matrix*
3. **🛡️ Structured Cyber Advisory (`.pdf`)**:
   - Formal document formatted with severity indicators (`CRITICAL` / `HIGH` / `MEDIUM`), affected assets, threat vectors, immediate countermeasures, and long-term mitigation steps.
4. **📋 Executive Briefing & Summary (`.pdf`)**:
   - Concise strategic synthesis highlighting business impact, key findings, critical risks, and prioritized decision matrices.
5. **◔ Interactive Visual Infographic (`.html`)**:
   - Modern, responsive visual dashboard summarizing key statistics, visual hierarchy cards, data points, and color psychology palettes.
6. **💼 LinkedIn Post & Carousel**:
   - High-engagement professional copy featuring an attention-grabbing hook, core bulleted insights, carousel slide breakdowns, call to action, and strategic hashtags.
7. **𝕏 Twitter / X Post & Thread**:
   - 280-character punchy primary announcement plus an expanded, sequential deep-dive thread.

---

## 🔒 Source Grounding & Anti-Hallucination Guardrails

- **Strict Indicator Verification**: Automatically extracts and cross-checks technical identifiers (CVE IDs, IP addresses, hashes, domains, software versions) against the original source text.
- **Grounding Score Telemetry**: Calculates a 0–100% grounding confidence score to ensure no fabricated threat actors, fake vulnerabilities, or unverified claims enter generated artifacts.

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- NVIDIA NIM API Key (Free tier at [build.nvidia.com](https://build.nvidia.com)) or OpenAI / Google Gemini / Anthropic API Key

### 2. Setup Environment

```bash
# Clone the repository
git clone https://github.com/your-username/infogen-ai.git
cd infogen-ai

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables

Create `.env` inside `backend/` (or copy `.env.example`):

```bash
cp .env.example backend/.env
```

Edit `backend/.env` with your API key:
```env
AI_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-key-here
MODEL_NAME=meta/llama-3.2-11b-vision-instruct
FAST_MODEL_NAME=meta/llama-3.2-11b-vision-instruct
```

> **Note**: Even without an external API key, InfoGen AI includes an offline grounded fallback generator that synthesizes all 7 deliverables with complete test coverage!

### 4. Run the Application

```bash
# Start FastAPI backend with frontend serving
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
**http://127.0.0.1:8000/**

---

## 🐳 Docker Deployment

Run InfoGen AI with a single command using Docker Compose:

```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.

---

## 🧪 Test Suite

Run the full automated test suite (39 passing unit and integration tests):

```bash
pytest backend/tests
```

---

## 📁 Repository Structure

```
.
├── InfoGen_AI.html           # Full production single-page application (Dual Theme UI)
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers (generate, export, health, ingest, jobs)
│   │   ├── prompts/          # Grounding rules and 7 format-specific prompts
│   │   ├── schemas/          # Pydantic v2 schemas for all 7 deliverable formats
│   │   ├── services/         # Generation engine, PIL diagram synthesizer, exporters
│   │   ├── models/           # SQLAlchemy persistent job models
│   │   ├── config.py         # App settings and multi-provider credentials
│   │   └── main.py           # FastAPI entrypoint, middleware, static frontend mount
│   ├── tests/                # Comprehensive test suite (39 tests)
│   ├── Dockerfile            # Container build specification
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Sample environment configuration
├── docker-compose.yml        # Multi-container orchestration
├── .gitignore                # Production gitignore (secures keys, DBs, and temp files)
└── README.md                 # Project documentation
```

---

## 📄 License & Attribution

Developed for Smart India Hackathon (SIH) — Automated Content Transformation Platform. Distributed under the MIT License.
