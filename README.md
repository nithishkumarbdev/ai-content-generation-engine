# AI Content Generation Engine

Turns a product name, description, and reference photo into a generated
creative. An LLM writes an image-generation prompt from the product info,
an image provider generates a result from that prompt plus the reference
image, and the whole thing runs as an async job you can poll for status.

The service accepts product information and a reference image, uses an LLM to generate an image-generation prompt, and runs image generation as an asynchronous job with status polling.
---

## Overview

```
                     POST /generate
                          |
                          v
              +--------------------------+
              |   create Job (pending)   |
              |   save reference image   |
              +--------------------------+
                          |
              202 Accepted { id, status }        <-- caller gets this immediately
                          |
                          v  (background task)
              +--------------------------+
              | status -> processing     |
              | LLM: product -> prompt   |
              | image provider: prompt   |
              |   + reference -> image   |
              | status -> completed/     |
              |   failed                 |
              +--------------------------+

              GET /jobs/:id  -> poll for status + result
              GET /jobs      -> list all jobs (frontend job list)
```

The job *is* the unit of work: one row per generation, holding both the
request and its eventual result. No queue, no worker fleet. A single
`BackgroundTasks` call is enough at this scale, and reaching for
Celery/Redis/Kafka here would be solving a problem this app doesn't have.

## Tech stack

| Layer      | Choice                          | Why |
|------------|----------------------------------|-----|
| Backend    | Python, FastAPI                  | Async-friendly, built-in request validation (Pydantic), free OpenAPI docs at `/docs` which doubles as API documentation |
| Database   | PostgreSQL + SQLAlchemy           | PostgreSQL provides persistent job storage, while SQLAlchemy's declarative models keep the data layer simple for a single-table application. |
| Job runner | FastAPI `BackgroundTasks`         | The whole job is one LLM call + one image call; a message broker would be overkill |
| LLM        | Groq (OpenAI-compatible), swappable | Free tier, fast, and the same `httpx` call works for any OpenAI-compatible provider by changing env vars |
| Image gen  | Mock provider by default, ComfyUI provider available |The mock provider is enabled by default for local development; the provider interface allows ComfyUI or another image model to be swapped in without changing the rest of the pipeline. |
| Frontend   | Single static HTML page, vanilla JS `fetch` | A single static HTML page keeps the frontend lightweight and avoids a separate build pipeline. |

8 runtime dependencies in `backend/requirements.txt`, all of them load-bearing.

## Folder structure

```
ai-content-generation-engine/
├── .github/
│   └── workflows/
│       └── python.yml         CI: install deps, verify import, run tests
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI app, CORS, static mounts, startup
│   │   ├── config.py             All env-var driven settings, in one place
│   │   ├── database.py           SQLAlchemy engine/session/init
│   │   ├── models.py             Job ORM model + status enum
│   │   ├── schemas.py            Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── jobs.py           POST /generate, GET /jobs, GET /jobs/:id
│   │   │   └── health.py         GET /health
│   │   ├── services/
│   │   │   ├── job_service.py    Job lifecycle + pipeline orchestration
│   │   │   ├── providers.py      Picks the active LLM/image provider
│   │   │   ├── llm/              LLMProvider interface + Groq implementation
│   │   │   └── image/            ImageProvider interface + mock/ComfyUI implementations
│   │   └── utils/files.py        Upload/save/URL helpers
│   ├── tests/                     Pytest suite (runs against SQLite, no Postgres needed)
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── requirements-dev.txt       requirements.txt + pytest
│   └── .env.example
├── frontend/
│   └── index.html                 Form + job list + result viewer
├── Dockerfile
└── README.md
```

Routes stay thin (parse request, call service, map errors to HTTP status);
all business logic — job creation, the generation pipeline, status
transitions — lives in `services/`. There's no separate repository layer:
with one table, a repository on top of the ORM would be an abstraction
without a second implementation to justify it.

## API

**`POST /generate`** — `multipart/form-data`: `product_name`, `product_description`, `image` (jpeg/png/webp)

>The reference image is required because it is used as the source image for the image-generation workflow.
> description`, but the scenario above it, and the sample input/output, both
> require a reference image for img2img generation. `image` is a required
> field here, not an oversight.

Returns `202 Accepted`:
```json
{ "id": "uuid", "status": "pending" }
```
`400` if `product_name`/`product_description` are blank or the image is missing/unsupported.

**`GET /jobs/:id`** — full job state:
```json
{
  "id": "uuid",
  "product_name": "Florentine Wooden Salad Bowl",
  "product_description": "...",
  "reference_image_url": "/static/uploads/....jpg",
  "status": "completed",
  "generated_prompt": "...",
  "result_image_url": "/static/generated/....png",
  "error_message": null,
  "created_at": "...",
  "updated_at": "..."
}
```
`404` if the job doesn't exist.

**`GET /jobs`** — array of the above, newest first.

**`GET /health`** — `{ "status": "ok" }`

Interactive docs (request/response schemas, try-it-out) are auto-generated at `/docs`.

## Setup

**Requirements:** Python 3.12 (3.11+ should also work), a PostgreSQL database.

```bash
cd backend
python3 -m venv venv

# activate it:
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL and LLM_API_KEY
uvicorn app.main:app --reload
```

Open `http://localhost:8000` — the frontend is served from the same app.
Tables are created automatically on startup (no migration step needed).

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string |
| `LLM_API_KEY` | yes (for real generations) | API key for the LLM provider. Get a free one at [console.groq.com](https://console.groq.com) |
| `LLM_BASE_URL` | no | Defaults to Groq's OpenAI-compatible endpoint |
| `LLM_MODEL` | no | Defaults to `llama-3.1-8b-instant` |
| `IMAGE_PROVIDER` | no | `mock` (default) or `comfyui` |
| `COMFYUI_BASE_URL` | only if `IMAGE_PROVIDER=comfyui` | Base URL of your deployed ComfyUI instance |
| `PUBLIC_BASE_URL` | no | Absolute base URL once deployed, so image URLs in API responses are absolute rather than relative |

Without `LLM_API_KEY` set, jobs will fail cleanly with a `failed` status and
an explanatory `error_message` — the app still runs, it just can't complete
generations.

## Deploying

The `Dockerfile` at the repo root builds the whole app (API + frontend) as
one container:

```bash
docker build -t glitrai-content-engine .
docker run -p 8000:8000 --env-file backend/.env glitrai-content-engine
```

Any host that runs a container plus gives you a Postgres instance works —
e.g. Render, Railway, or Fly.io all offer a free tier that covers this app.
Point `DATABASE_URL` at the managed Postgres instance and set `PUBLIC_BASE_URL`
to the assigned public URL.

## Testing

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

Tests run against a throwaway SQLite database (set up automatically in
`tests/conftest.py`), not your real Postgres instance — no setup needed
beyond installing dependencies. They cover:

- `/health` returns correctly
- `/generate` rejects blank fields, a missing image, and an unsupported file type
- `/jobs/:id` returns 404 for a job that doesn't exist
- the actual job pipeline: a job reaches `completed` with a working LLM call,
  and fails cleanly with a readable `error_message` when the LLM call breaks

This isn't a complete test suite, just coverage of the parts that would
actually break the app if they regressed.

## GitHub Actions

`.github/workflows/python.yml` runs on every push and pull request to `main`:
installs dependencies, checks the app imports without errors, then runs the
test suite above. No deployment step — it's a correctness check, not a CD
pipeline.

Any repo that offers to auto-generate a starter workflow (GitHub's "Actions"
tab does this) may be tempting to click, but check what it actually assumes
first — the Conda-based Python template GitHub suggests by default doesn't
apply here (this project doesn't use Conda, and the template also assumes
`requirements.txt` and any tests live at the repo root, when they're inside
`backend/`).

## Tradeoffs made

- **No repository/DAO layer.** One table doesn't earn the extra
  indirection; the service layer talks to SQLAlchemy directly.
- **No migrations tool.** `Base.metadata.create_all()` on startup is enough
  for a schema this small and stable. Alembic would be setup cost with no
  real benefit here.
- **`BackgroundTasks`, not a task queue.** Fine for a single-instance app
  with lightweight, short jobs. It would *not* scale to multiple app
  instances (a job queued on instance A won't be picked up correctly if
  that process restarts mid-job) — see Future Improvements.
- **Frontend has no build step.** A single HTML file with `fetch` calls
  covers "submit a form, see a job list, view a result" without adding
  React/Vue tooling for a UI that's explicitly not meant to be polished.
- **SQLAlchemy's portable `Uuid` type, not `postgresql.UUID`.** Both produce
  a native `uuid` column on Postgres, but the generic one also compiles
  against SQLite — which is what makes running tests without a live
  Postgres server possible at all.

## Known limitations

- Background jobs live in the API process's memory. If the process
  restarts while a job is `processing`, that job is stuck and won't retry
  automatically.
- No auth. Anyone with the URL can submit jobs and see all of them, which
  is fine for a demo but not for production.
- The ComfyUI provider (`app/services/image/comfyui_provider.py`) handles
  upload → queue → poll → fetch generically, but `_fill_workflow` raises
  `NotImplementedError` on purpose: it requires an exported ComfyUI workflow JSON whose node IDs match the selected checkpoint and upscaling workflow.Wire that in and switch
  `IMAGE_PROVIDER=comfyui` to use it.
- Test coverage is deliberately narrow (health, validation, the job
  pipeline) rather than exhaustive — see Testing above.

## Troubleshooting

**`RuntimeError: Directory '...' does not exist` on startup** — the
`static/uploads` and `static/generated` folders are missing. They're
created automatically on startup (`ensure_dirs()` in `main.py`), so this
usually means the app crashed before reaching that point, or `STATIC_DIR`
points somewhere unexpected. Check your `.env`.

**Jobs stay stuck on `failed` with `LLM_API_KEY is not configured`** —
expected if you haven't set `LLM_API_KEY` in `.env`. Get a free one at
[console.groq.com](https://console.groq.com).

**`psycopg2` fails to install** — it needs PostgreSQL's client headers.
On Debian/Ubuntu: `sudo apt install libpq-dev python3-dev`. On Mac:
`brew install postgresql`.

**Frontend loads but shows no jobs / a blank page** — check the browser
console for CORS or network errors, and confirm the API is actually
reachable at the URL the page is calling (`API_BASE` in `frontend/index.html`,
currently a relative path assuming frontend and API are served together).

## License

MIT License. See LICENSE.

## Future improvements

- Move job execution to a real worker (even a single `arq`/RQ process
  backed by Redis) once running more than one API instance.
  `BackgroundTasks` stops being safe as soon as there's more than one
  process handling requests.
- Retry LLM/image calls with backoff before marking a job failed.
- Add auth so jobs are scoped to a user instead of globally visible.
- Stream job status over a websocket/SSE instead of the frontend's
  2-second polling.
