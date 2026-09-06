# InfoGen AI

### One source. Seven communication formats. NVIDIA first, Gemini fallback.

For a plain-language account of the work and testing, read [What we improved](README-IMPROVEMENTS.md).

InfoGen AI is a college hackathon project that turns a document or pasted text into useful, audience-specific communication. Instead of manually rewriting the same information for a presentation, a briefing and social media, users provide the source once, select their outputs and generate them together.

The current application uses a **FastAPI backend**, the existing **HTML/CSS/JavaScript interface**, **NVIDIA-hosted inference**, and **SQLite** for saved results.

## Latest output-quality improvements

The latest revision focuses on the actual deliverables, not a new application architecture:

| Problem | How it was fixed |
| --- | --- |
| Outputs followed generic templates | Reworked all seven prompts around the source's actual subject, evidence, audience and information density. Optional sections can remain empty. |
| Presentation length was forced | Removed fixed slide, carousel and scene counts. The model chooses the useful length; the PPTX contains exactly its slide list, with no extra cover. |
| Repetitive LinkedIn output | One canonical publishable post is used for preview, clipboard and TXT. Hook, CTA and hashtags are not appended as duplicate sections. Carousel notes are separate in the ZIP. |
| Missing slide numbers | Backend normalization numbers slides/carousels consecutively; previews use the actual array position. |
| PowerPoints all looked the same | Added editable cover, editorial, metric, process, comparison and closing layouts, with a charcoal/white/teal/coral palette, stronger typography and automatic text sizing. Supporting prose goes into notes instead of crowding bullets. |
| Non-security sources became threat reports | Advisory content and headings now distinguish security issues from informational briefings. Empty unrelated sections are omitted. |
| Summary and infographic exports lost fields | Included supporting findings, risks, decisions, references, infographic data points and source labels in exports. |
| A failed NVIDIA request became excerpts immediately | Added per-format Gemini fallback for request failures, timeouts and invalid responses, within one shared deadline. Results identify their actual provider and model. |
| Unsupported figures could appear in drafts | Added a numerical-source guard alongside the existing identifier checks, with corrective retries. This is a heuristic, not a guarantee of factual correctness. |
| Old prototype files cluttered the root | Preserved them under `legacy/streamlit/`. Root `requirements.txt` now installs the active backend dependencies. Removed unused provider placeholders and redundant defaults from environment configuration. |

Existing downloaded files and already-open browser results are not rewritten. **Regenerate the source to see the revised outputs.**

> The normal application runs with NVIDIA credentials in `backend/.env`. Credentials stay on the backend. This README and the example environment files contain no real keys.

## Contents

- [What the application does](#what-the-application-does)
- [The seven deliverables](#the-seven-deliverables)
- [Four ready-to-use examples](#four-ready-to-use-examples)
- [How the system works](#how-the-system-works)
- [What was fixed and how](#what-was-fixed-and-how)
- [NVIDIA integration](#nvidia-integration)
- [Installation and startup](#installation-and-startup)
- [Environment variables](#environment-variables)
- [Testing and verification](#testing-and-verification)
- [Demo walkthrough](#demo-walkthrough)
- [Project structure](#project-structure)
- [API reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Current limitations](#current-limitations)

## What the application does

InfoGen AI accepts news, cybersecurity advisories, research and policy reports, incident reports, announcements, and free-form text. All inputs follow the same processing pipeline.

Users can:

- Paste source text or a direct public article URL.
- Upload UTF-8 TXT, text-based PDF or DOCX files.
- Combine up to four documents, with a 25 MB per-file limit and 50,000 combined extracted characters.
- Choose the source category, target audience, tone, language, level of detail and objective.
- Select any combination of the seven output formats.
- Read formatted results, copy them, download individual deliverables, or download a complete bundle.
- Retain the original text for comparison, adjustment and another generation.

The source category describes the input; it is separate from the selected output formats. A research report can become an executive summary, a LinkedIn post and a slide deck in the same request.

## The seven deliverables

| Deliverable | Generated content | Available export |
| --- | --- | --- |
| Video package | AI-authored narration and scenes, visual directions, timing and browser playback | Script, VTT subtitles and browser-recorded WebM |
| LinkedIn post | Hook, post, key insights, call to action, hashtags and carousel outline | Text/Markdown and complete bundle |
| Twitter / X post | Primary post and a thread; posts are checked against the 280-character limit | Text/Markdown and complete bundle |
| Advisory document | Overview, affected systems, indicators, impact and source-supported actions | PDF |
| Infographic | Key figures, messages, sections and layout recommendations | Standalone HTML |
| Executive summary | Headline, takeaways, findings, risks, actions and conclusion | PDF |
| Presentation deck | Slides with concise points, source-based graphics and speaker notes | PowerPoint PPTX |

Video is a rendered storyboard with optional browser narration, not AI-generated camera footage. WebM recording does not capture speech-synthesis audio.

## Four ready-to-use examples

The built-in **Demo example** selector loads these documents immediately. Each is clearly synthetic; no real incident or organisation is being asserted.

| Example | Subject | Useful things to inspect |
| --- | --- | --- |
| News Article | Riverton's fictional library laptop-lending pilot | The planned 120 devices, seven-day borrowing period and unavailable outcome data |
| Security Advisory | Northstar Gateway's fictional session-expiry flaw | HIGH severity, affected versions, supplied indicators and mitigation |
| Research / Policy Report | Privacy-preserving campus analytics | 240 survey participants, the reported 72% preference, study limitations and retention recommendations |
| Incident Report | Meadowbrook helpdesk account misuse | UTC timeline, 18 ticket records, root cause, remediation and unknown actor identity |

Sample source: [samples/demo.json](samples/demo.json).

For example, the research summary should discuss what the study actually measured. It should not invent energy savings, a budget or a final approval decision.

## How the system works

```text
Pasted text / public URL / TXT / PDF / DOCX
                       |
                       v
          Validation and text extraction
                       |
                       v
      NormalizedSource: source ID, input type,
           text, title and source metadata
                       |
                       v
       ContentIntelligence: source passages,
        explicit figures, risks and actions
                       |
                       v
        Selected output prompts + JSON schema
                       |
                       v
          Parallel NVIDIA model requests
                       |
                       v
       Schema and technical-identifier checks
                       |
                       v
          Structured output + SQLite storage
                       |
                       v
          Frontend results and native downloads
```

### 1. Validate and extract

The backend checks request types, selected formats, source size and upload extensions. PyMuPDF extracts PDF text, python-docx reads paragraphs and table cells, and TXT input is decoded as UTF-8.

Public URLs are restricted to direct HTTP/HTTPS HTML or text responses. Local/private destinations are rejected, redirects are not followed, and response size is capped.

### 2. Normalize the source

All supported inputs become a common `NormalizedSource`. The pipeline retains the input type and source metadata while combining extracted content when multiple inputs are supplied.

This avoids maintaining a separate AI pipeline for every file format.

### 3. Prepare the source context

The normalizer extracts source passages and explicit quantities. Recommendations and risks are identified by source wording, rather than guessed from their position in a document.

This preparation is deterministic text processing. **The actual rewriting and audience adaptation happen in the live NVIDIA generation step.**

### 4. Generate the selected formats

Each format has its own prompt. The backend supplies the user's parameters, source passages, grounding instructions and the actual Pydantic JSON schema.

Only selected formats are requested. Multiple selected formats run concurrently.

### 5. Validate and render

The backend parses JSON, validates types and essential fields, checks for newly introduced technical identifiers, and checks X post lengths. Video subtitles are derived from validated scene times and narration.

The frontend receives structured objects and renders them as readable results. Normal users do not need to read raw JSON.

### 6. Recover honestly from failures

Missing credentials or a missing model produce an explicit configuration error. The application does not silently switch an unconfigured normal run into a demo.

A provider timeout or unusable generated response can still produce **clearly labelled source excerpts** for the affected format. Such output is marked `generation_mode="extractive"`, not `"ai"`. Recovery does not pretend to translate or rewrite tone.

Explicit offline mode remains available for isolated automated tests and development, rather than being the normal product configuration.

## What was fixed and how

The existing architecture and working result renderers were retained. The work focused on completing the source-to-result workflow and correcting misleading or broken behaviour.

| Problem found | How it was fixed | Result |
| --- | --- | --- |
| Startup documentation used an import path that did not match the backend package layout | Standardized startup on `app.main:app --app-dir backend` | The documented command imports and starts the correct application |
| Environment loading depended on the current working directory | Resolved `backend/.env` relative to the configuration module | Consistent environment loading when starting from the project root |
| Normal no-key operation could look like successful AI processing | Configured NVIDIA as the normal provider and added explicit configuration errors | Missing credentials cannot masquerade as live generation |
| Generic demo output discussed InfoGen instead of the supplied source | Replaced the active fallback path with source-based extraction in `grounded.py` | Recovery content reflects the submitted document |
| Some fallback slides invented risk levels, timelines and readiness percentages | Removed fabricated defaults and used unavailable fields or source excerpts | The app no longer adds those hard-coded claims |
| PowerPoint graphics contained fixed values such as availability and readiness scores | Replaced the fixed graphics with source-excerpt visuals | Exported diagrams reflect the actual supplied material |
| Empty or malformed model output could pass through as successful content | Added required-content checks, JSON schema guidance and typed validation | Invalid responses trigger labelled recovery |
| Live output types sometimes disagreed with the prompt examples | Added the actual Pydantic schema to each generation prompt | The provider receives the same field/type contract the backend validates |
| Video generation did not return the subtitles expected by the validator | Build VTT directly from the AI-generated scenes | A valid storyboard remains a live AI output and has usable subtitles |
| Video timing examples included invalid `00:60` timestamps | Corrected the prompt and validated/normalized scene timing | Sequential scene numbering, matching duration and valid VTT timestamps |
| The presentation prompt imposed a fixed briefing size | Replaced fixed counts with source-driven length and increased the response budget | Short and detailed sources can produce different deck lengths |
| The old 35-second provider timeout cut off presentation generation | Added a configurable AI timeout and a longer browser request timeout | The client can wait for longer outputs without prematurely abandoning the request |
| Uploaded files could fail silently while remaining inputs were processed | Added explicit invalid-file and extraction errors | Users know when a document was rejected or unreadable |
| Images/audio/video and old DOC files appeared supported despite placeholder extraction | Restricted accepted uploads to working TXT, PDF and DOCX paths | The interface advertises the formats the MVP can actually process |
| DOCX tables were omitted | Included table-cell text during DOCX extraction | Content in document tables reaches the AI pipeline |
| Uploaded filenames and exported content could be treated as markup | Used text-safe filename rendering and escaped PDF/HTML content | Special characters are preserved without executing supplied markup |
| Users could not remove an individual upload | Added per-file removal controls | Inputs can be corrected before submission |
| Source text disappeared after generation | Retained it until the user explicitly clears or replaces it | Users can compare results with the source and regenerate |
| Repeated generation left the output-count label pointing at an old DOM element | Resolve the current counter element after the button updates | Select/deselect counts remain accurate |
| Job endpoints returned placeholders | Connected job creation and output retrieval to the existing SQLAlchemy models | Completed outputs can be retrieved by job ID |
| Blocking generation ran directly inside async request handling | Run synchronous generation and export work in worker threads | Other API requests can continue while generation is running |
| PDF exports crashed because ReportLab imports were missing | Added the required imports and covered PDF export in integration tests | Advisory and summary PDFs are generated successfully |
| Errors were transient or looked like completed progress | Added persistent error messages, retained inputs and restored controls | A failed request leaves the app usable for retry |
| There were no ready-to-use varied demo sources | Added four labelled synthetic samples and a selector | Friends and judges can test without preparing documents |
| Tests could touch normal configuration or the application's database | Forced explicit test mode and an isolated temporary SQLite database | Automated tests never use the real NVIDIA key |
| Mobile counter text overlapped the source input | Adjusted counter positioning and checked mobile screenshots | The text input and counter remain readable |
| Docker build paths and the health check were inconsistent with the project layout | Corrected the build paths, server command and health check | Container configuration matches the FastAPI architecture; Docker execution is not part of the local verification |

### Where the main fixes live

- [InfoGen_AI.html](InfoGen_AI.html): source selection, upload controls, loading/error states and result rendering.
- [routes_generate.py](backend/app/api/routes_generate.py): request validation, pipeline orchestration, persistence and exports.
- [config.py](backend/app/config.py): environment loading and configuration checks.
- [ai_provider.py](backend/app/services/ai_provider.py): NVIDIA requests and provider configuration.
- [normalizer.py](backend/app/services/normalizer.py): source-context preparation.
- [generator.py](backend/app/services/generator.py): prompts, schema validation, source checks and video completion.
- [grounded.py](backend/app/services/grounded.py): explicitly labelled source-excerpt recovery.
- [ingestion.py](backend/app/services/ingestion.py): TXT/PDF/DOCX and public-page extraction.
- [exporters.py](backend/app/services/exporters.py): PDF, PPTX and infographic exports.
- [routes_jobs.py](backend/app/api/routes_jobs.py): persisted result retrieval.
- [backend/tests](backend/tests): focused regression and integration tests.

## NVIDIA integration

The local configuration uses:

```env
AI_PROVIDER=nvidia
DEMO_MODE=false
MODEL_NAME=nvidia/nemotron-3.5-lightning-30b-a3b
```

The model is called through NVIDIA's `https://integrate.api.nvidia.com/v1` endpoint using the existing compatible Python client.

For this structured content workflow, Nemotron thinking output is disabled and JSON output is requested. NVIDIA uses a 6,000-token response limit. The default total deadline is 150 seconds per format, with up to 90 seconds reserved for the primary provider and the remaining time available to Gemini. The browser allows 180 seconds per request.

One invalid model response per provider can be retried with corrective instructions within its allowance. NVIDIA failures then use Gemini, when configured. Only after the configured providers fail does the app return labelled source excerpts. There are no unlimited retries.

### Gemini fallback

Set `FALLBACK_PROVIDER=gemini`, `GOOGLE_API_KEY` and `GEMINI_MODEL_NAME=gemini-3.6-flash` in the same local `backend/.env`. No second server or SDK is required. Gemini uses the existing client through Google's compatible endpoint with JSON output and a bounded timeout.

The configured Gemini model was verified with the supplied account. The older `gemini-2.5-flash` model was rejected for this account, so it is not used. Model access and quota can change.

Official reference: [Google Gemini compatibility documentation](https://ai.google.dev/gemini-api/docs/openai).

Each deliverable includes `provider`, `model`, `generation_mode` and warnings. A single request may contain some NVIDIA outputs and some Gemini outputs. The UI shows provider attribution for the selected format. Leaving the Gemini key blank disables the optional fallback; it does not disable NVIDIA.

Official reference: [NVIDIA Nemotron 3.5 Lightning inference API](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-5-lightning-30b-a3b-infer). Model availability and account limits can change; the exact configured model must support your NVIDIA account.

Real credentials exist only in the local `backend/.env`. It is ignored by Git and must never be inserted into this README, screenshots, frontend JavaScript or example files.

## Installation and startup

### Prerequisites

- Python 3.10 or newer; Python 3.12 was used for local verification.
- An internet connection for NVIDIA inference.
- A valid NVIDIA key and an available model.
- A modern browser.

### Windows PowerShell

Run these commands from the `InfoGen-AI` directory:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

For a new checkout only, create the local environment file:

```powershell
Copy-Item backend/.env.example backend/.env
```

Set your credential in `backend/.env`. **Do not overwrite an already configured environment file.**

Start the app:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. API documentation is at **http://127.0.0.1:8000/docs**.

There is one application server. A separate frontend build or Node server is not required.

### macOS / Linux

Use `.venv/bin/python` in place of `.venv\Scripts\python.exe`, and `cp backend/.env.example backend/.env` for a new local environment.

Restart the server after changing environment values.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `AI_PROVIDER` | Normal configuration: `nvidia`; existing alternatives are `openai`, `gemini` and `anthropic` |
| `NVIDIA_API_KEY` | Local server-side NVIDIA credential |
| `MODEL_NAME` | Exact model identifier available on the selected provider |
| `FALLBACK_PROVIDER` | Optional `gemini` fallback; blank disables fallback |
| `GOOGLE_API_KEY` | Server-side Gemini credential |
| `GEMINI_MODEL_NAME` | Fallback model; verified here with `gemini-3.6-flash` |
| `AI_TIMEOUT_SECONDS` | Total per-format deadline including fallback; default 150 seconds |
| `PRIMARY_TIMEOUT_SECONDS` | Primary-provider allowance when fallback exists; default 90 seconds |
| `DEMO_MODE` | Keep `false` for live use; `true` is an explicit development/test choice |
| `MAX_FILE_SIZE_MB` | Per-file upload size, default 25; the current UI also uses 25 MB |
| `DATABASE_URL` | Default: `sqlite:///./infogen.db` |
| `CORS_ORIGINS` | JSON list of permitted frontend origins |
| `LOG_LEVEL` | Application logging level |

OpenAI and Anthropic retain their existing optional adapters but are not part of the verified NVIDIA/Gemini path. Anthropic requires its optional SDK.

## Testing and verification

### Verified locally on 6 September 2026

- **82 automated tests passed**, including dynamic deck sizes, canonical social copy, numerical checks, synthetic labels and fallback recovery.
- **All four synthetic samples produced all seven live AI outputs** across verification runs, including actual Gemini fallback on NVIDIA failures. Each successful output reported `generation_mode="ai"`.
- The final four-sample API run completed all 28 deliverables. Gemini successfully recovered several NVIDIA failures. The news deck selected three slides, rather than a forced six.
- PowerPoint opened and rendered the revised deck, with no detected text-box overflow. Desktop/mobile browser checks replayed live API results across all four source types and exercised real exports, video playback, empty input and backend-failure states.
- A final live browser submission verified NVIDIA generation, preservation of synthetic status, matching LinkedIn preview/TXT download and mobile layout. All four current sample results exported successfully to PPTX, advisory PDF, summary PDF and infographic HTML.
- Live-generated news, advisory and research outputs successfully exported to PDF, PPTX and HTML.
- An initial incident request encountered provider timeouts on three formats and returned labelled source excerpts. Retrying the incident sample produced all seven AI outputs successfully. External inference is therefore a dependency, not an error-free guarantee.
- The earlier desktop/mobile workflow checks covered result tabs, source retention, downloads, video canvas playback and input/backend errors.
- Local credentials were confirmed ignored by Git and absent from shareable source files. They are not included in the branch publication.

### Automated regression tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

These tests use a temporary database and explicit test mode. They do not make live NVIDIA requests or consume provider quota.

Coverage includes all four samples and seven output shapes; TXT/PDF/DOCX uploads; PDF/PPTX/HTML exports; job retrieval; empty and invalid input; malformed model responses; simulated timeouts; hallucinated technical identifiers; source-only recovery; missing live credentials; and subtitle generation.

### Live NVIDIA verification

Start the configured server, then run:

```powershell
.venv\Scripts\python.exe scripts/verify_live.py
```

This intentionally sends the four synthetic samples to NVIDIA and requests all seven formats. It fails if any requested format uses recovery rather than live AI output.

A smaller check:

```powershell
.venv\Scripts\python.exe scripts/verify_live.py --sample news --formats "Executive Summary"
```

The script writes per-sample results and a verification report under ignored `test-artifacts/`. Do not confuse a healthy server or a 200 response with successful generation: check each output's `generation_mode`.

### Browser verification

With Microsoft Edge installed:

```powershell
.venv\Scripts\python.exe -m pip install playwright
.venv\Scripts\python.exe scripts/browser_smoke.py --live --sample news
```

Use `--channel chrome` for Chrome. This checks real form submission, result tabs, repeated selection, source retention, a PDF download, moving/nonblank video canvas, mobile layout and backend-disconnection handling. Screenshots go into `test-artifacts/`.

Omit `--live` only when deliberately testing a server configured for explicit offline mode.

## Demo walkthrough

1. Start the server and open the dashboard.
2. Choose **News Article** from **Demo example**.
3. Set the audience to **General Public**, tone to **Professional**, and objective to **Inform**.
4. Keep all seven deliverables selected and click **Generate**.
5. Start with **Executive Summary** to show the main facts.
6. Open **Presentation Deck**, then download the PPTX.
7. Open **Video Package** and play its storyboard.
8. Repeat with **Security Advisory** to show the different source vocabulary and indicators.
9. Use the research example to discuss findings versus limitations.
10. Use the incident example to show timeline and remediation.
11. Compare generated claims with the retained source. Missing information should remain unavailable.
12. Try empty input to demonstrate that validation leaves the app usable.

A useful explanation for friends:

> "We kept the original frontend and backend, then completed the full workflow. Every file becomes text in one common source structure. We send that source to NVIDIA with a different prompt and schema for each selected format. The backend checks the returned objects, saves them, and the frontend renders the results. When an API call fails, the app clearly identifies any source-excerpt recovery instead of calling it AI output."

## Project structure

```text
InfoGen-AI/
|-- InfoGen_AI.html              # Active frontend
|-- README.md                   # Setup, architecture and completion notes
|-- backend/
|   |-- .env                    # Local credentials; Git-ignored
|   |-- .env.example            # Shareable placeholders
|   |-- requirements.txt
|   |-- app/
|   |   |-- main.py             # FastAPI startup and frontend serving
|   |   |-- config.py           # Environment settings
|   |   |-- api/                # Health, samples, generation, ingestion and jobs
|   |   |-- models/             # Existing SQLAlchemy database models
|   |   |-- schemas/            # Request/response/output contracts
|   |   |-- services/           # Ingestion, AI, validation and exporters
|   |   |-- prompts/            # Grounding and output-specific prompts
|   |-- tests/
|-- legacy/streamlit/           # Preserved earlier prototype; not the active app
|-- samples/demo.json           # Four synthetic source documents
|-- scripts/
|   |-- verify_live.py          # Opt-in live sample verification
|   |-- browser_smoke.py        # Desktop/mobile workflow checks
|   |-- check_nvidia.py         # Optional model-connectivity check
|-- pytest.ini
|-- docker-compose.yml
```

The former root `app.py`, `core_engine.py`, `file_exporters.py` and their requirements are preserved under `legacy/streamlit/`. Root `requirements.txt` now points to the active backend.

## API reference

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Frontend |
| GET | `/api/health` | Server status and configuration state, without credentials |
| GET | `/api/samples` | Four synthetic examples |
| POST | `/api/generate` | JSON text or multipart file generation |
| POST | `/api/ingest` | Standalone text/file extraction |
| POST | `/api/export` | PDF, PPTX or HTML export from structured output |
| GET | `/api/jobs/{id}` | Completed job status |
| GET | `/api/outputs/{id}` | Persisted output objects |
| GET | `/docs` | Interactive API documentation |

Generation request example:

```json
{
  "source": "A fictional library will lend 120 laptops for seven days. Outcome data is not yet available.",
  "content_type": "News Article",
  "audience": "General Public",
  "tone": "Professional",
  "language": "English",
  "detail": "Standard",
  "objective": "Inform",
  "output_format": "Executive Summary, LinkedIn Post"
}
```

The response contains `success`, `job_id`, a readable combined `output`, individual `outputs`, and `metadata`. Each deliverable reports its own generation mode and warnings.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `python` is not recognized | Install Python, or use the full path to an existing Python executable |
| Backend import error | Run from the project directory using the exact `--app-dir backend` command above |
| AI configuration error | Check the local provider, key and model values, then restart |
| Provider rejects the model | Check current NVIDIA model availability and account access |
| Output uses source excerpts | Read its warning; check provider availability, quota and model response validity |
| Upload rejected | Use a non-empty UTF-8 TXT, text-based PDF or DOCX within the limits |
| Scanned PDF has no content | Extract its text with OCR separately and paste the result |
| Article URL fails | Paste the article text or use its final direct public URL |
| Port 8000 is occupied | Choose another port, such as `--port 8001`, and open that URL |
| ZIP packaging is unavailable | The complete bundle falls back to a Markdown download |
| Environment edits have no effect | Restart the process; configuration is loaded at startup |

## Current limitations

- This is a local, single-user hackathon MVP, not an authenticated public service.
- NVIDIA and Gemini availability, latency, account permissions and quotas are external dependencies. Fallback reduces interruptions but cannot guarantee success.
- Grounding checks detect some identifier mistakes; they do not prove that every AI claim is correct.
- Translation quality depends on the model. Complex-script PDF typography is not comprehensively verified.
- Supported ingestion is text, direct readable public webpages, TXT, text-based PDF and DOCX.
- Scanned PDFs, old DOC, media transcription, authenticated webpages and JavaScript-only article extraction are not implemented.
- Video playback is a storyboard; browser voice support varies and recorded WebM is silent.
- Very long documents need a shorter excerpt within the 50,000-character combined limit.
- Fonts and ZIP packaging may load optional CDN assets.
- PostgreSQL, Docker execution, Netlify and Vercel deployment are not the verified local run path.

## Sharing the project

Share the repository's code, this README and `.env.example`, not your local `.env`, database, generated logs or credentials. Every friend running a fresh copy should configure their own provider access.

The publication target for this completion work is `Main2-with-improvements-appu` only. The `main` branch is not a push target.
