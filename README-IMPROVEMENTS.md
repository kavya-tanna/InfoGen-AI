# What we improved in InfoGen AI

This is the plain-language story of what we worked on, what we fixed, and how
we tested it. The main [README](README.md) has the full setup instructions.

## Where we started

The project already had the right idea: take one document and turn it into
different kinds of communication. It also had a frontend, a FastAPI backend,
provider integrations and export code. We kept those foundations rather than
starting over.

The main problem was the gap between having the features on screen and being
able to use them confidently in a demo. Some paths were incomplete, some
exports failed, and generated content often repeated itself or followed a
generic template instead of the source.

## Getting the whole workflow working

We connected and checked the complete journey: add a source, choose the output
formats, generate content, review it, and download it.

Pasted text, direct readable public URLs, TXT, text-based PDF and DOCX files all
feed the same internal source structure. DOCX table contents are included too.
We stopped advertising upload formats whose extraction was only a placeholder.
Empty files, unreadable documents, unsupported formats and oversized inputs now
produce useful errors instead of quietly failing.

We also fixed startup instructions and environment loading, connected saved
jobs to the existing SQLite database, and moved blocking generation/export work
off the async request handler. The original source stays in the form after
generation, so someone can compare it with the result and try again.

## Making the seven outputs more useful

We rewrote the output prompts so each format has a different editorial job.
They use the supplied source, audience, tone and level of detail rather than
forcing every document into the same template.

- **Video package:** source-specific narration, scenes and visual directions.
  The scene count is not fixed. The backend checks timing, numbers the scenes
  and builds the narration script and VTT subtitles from them.
- **LinkedIn:** one complete post, not a post followed by the same hook,
  insights, call to action and hashtags all over again. Preview, copy and TXT
  download use the same publishable text. Long paragraphs get readable breaks;
  carousel content remains a separate companion.
- **Twitter / X:** a standalone post with optional continuations. Repeated
  opening posts and redundant numbering are removed, and each post is checked
  against the character limit.
- **Advisory:** a cybersecurity source can become a security advisory, while
  ordinary news or policy content gets an informational briefing. We do not
  need to invent a threat just to fill the template.
- **Infographic:** figures, labels, sections and supporting points come from
  the source. A document without statistics does not need made-up percentages.
- **Executive summary:** the important findings, implications and source-backed
  actions are separated. Empty or irrelevant sections can be left out instead
  of being filled with generic recommendations.
- **Presentation:** the model chooses the number of useful slides. There is no
  fixed five- or six-slide requirement, and the export does not add a surprise
  extra cover slide.

## Improving the PowerPoint design

The earlier export reused almost the same layout on every slide. We added
editable cover, editorial, metric, process, comparison and closing layouts so
the presentation can vary with the story.

The new design uses clearer typography, more deliberate spacing and a
charcoal, white, teal and coral palette. Text sizing adapts to the available
space. Supporting prose and production directions belong in speaker notes
instead of being squeezed beside the main points.

We opened an exported deck in PowerPoint and rendered its slides as images.
The revised news example chose three slides, and the checked deck had no
detected text-box overflow. We also tested that decks with 1, 3, 9 and 16 slides
keep their actual slide count and editable text.

## Using NVIDIA and Gemini together

NVIDIA is the primary provider. Gemini is the fallback for an individual output
when NVIDIA times out, returns an unusable response, or otherwise fails.

This is not just a second key sitting in the configuration. We tested an actual
Gemini response and observed Gemini complete deliverables after NVIDIA failures
during the sample runs. The UI identifies the provider used for the selected
output, so a mixed-provider result is not hidden.

Both providers have bounded time allowances. Responses are checked against the
same structured schema. If the configured providers still cannot finish, the
app can show clearly labelled source excerpts instead of pretending an AI draft
was generated successfully.

The verified configuration uses NVIDIA Nemotron 3.5 Lightning and Gemini 3.6
Flash. Provider access and quotas can change, so model names stay configurable.

## Keeping the content grounded

We added instructions and validation to reduce invented facts, technical
identifiers and numerical claims. Invalid responses can be retried with
corrective feedback. Missing information should remain missing rather than
turning into an invented budget, timeline or outcome.

During review, we caught an unsupported calculation in a generated slide. That
led to a numerical-source regression check as well as tighter prompt wording.
Explicitly synthetic sources also keep a short fictional/synthetic label in
the publishable content.

These checks help, but they do not prove every sentence is correct. The result
is still an AI draft and should be compared with the original before sharing.

## What we actually tested

### Automated checks

**82 automated tests passed**, including a fresh run before preparing this
branch for publication. They use isolated test configuration and a temporary
database, not the real provider credentials.

The suite covers input validation, TXT/PDF/DOCX ingestion, output schemas,
saved jobs, PDF/PPTX/HTML exports, missing credentials, malformed responses,
simulated provider failures, fallback behaviour, social-post duplication,
slide numbering/counts, subtitle construction and selected grounding checks.

To run it from the project directory:

```powershell
.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider
```

### Four different live examples

All four examples are synthetic and available in the app's demo selector:

| Example | What we checked |
| --- | --- |
| News article: Riverton library lending pilot | Planned device availability and loan duration, without claiming outcomes already happened |
| Security advisory: Northstar Gateway | Affected versions, supplied indicators and mitigation |
| Research/policy report: campus analytics | Survey findings, study limitations and privacy recommendations |
| Incident report: Meadowbrook helpdesk | The supplied timeline, impact, remediation and unknown information |

The final four-sample API verification run produced **all 28 requested
deliverables as live AI outputs**. Some came from NVIDIA and some used Gemini
fallback. Earlier runs did encounter timeouts and source-excerpt recovery;
that is why we checked generation mode instead of treating HTTP 200 as proof
that the AI succeeded.

All four sample results were exported successfully to PowerPoint, advisory
PDF, executive-summary PDF and infographic HTML.

### Browser and visual checks

We checked the desktop and mobile layouts, result tabs, retained source text,
selection controls, empty-input errors, download behaviour and recovery when
the backend is unavailable. We also checked that the video canvas was nonblank
and changed during playback.

Some browser checks replayed saved live API responses to test the UI without
making another round of provider calls. Separately, a final real browser
submission went through NVIDIA and verified the LinkedIn result, synthetic
label, matching TXT download and mobile layout.

The optional browser and live-provider scripts are in [scripts](scripts/).
Live checks use provider quota; the normal automated test suite does not.

## Tidying up without losing the old work

We preserved the earlier Streamlit prototype under [legacy/streamlit](legacy/streamlit/)
instead of deleting it. The active frontend is still `InfoGen_AI.html`, and the
active backend is in `backend/app/`. Root `requirements.txt` now points to the
backend dependencies.

We trimmed environment examples to the active setup and moved local runtime
logs into `.logs/`. Credentials remain in the Git-ignored `backend/.env`.
Environment examples contain placeholders only. Local databases, uploads,
virtual environments, logs and generated test artifacts are not part of this
branch's source commit.

## Trying the demo with friends

Follow the installation steps in the main README, configure your own provider
keys in `backend/.env`, then start the app:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000, load one of the four examples, choose the formats and
generate. Compare the result with the source, then try the downloads. Regenerate
an old result to see the latest prompts and formatting.

## What is still limited

This is a hackathon MVP, not an authenticated production service. External AI
providers can still fail or run out of quota. Grounding checks are heuristic,
and translation or complex-script PDF typography needs further testing.

Scanned PDFs need separate OCR. Video is a playable storyboard, not generated
camera footage, and its recorded WebM does not include speech-synthesis audio.
Docker and hosted deployments were not part of the verified local workflow.

## Branch scope

This work is prepared for **`Main2-with-improvements-appu`** in
`kavya-tanna/InfoGen-AI`. The publication target is that branch only, not `main`.
