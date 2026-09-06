# Cerebro Development Current State

Checkpoint date: 2026-09-06

This is a repository-state checkpoint. It records verified repository contents and verification results at the time of writing. It does not implement Phase 1A.

## 1. Current Phase

- **Phase 0 — Foundation: COMPLETED / VERIFIED.** This status is the current CroadMap position supplied for this checkpoint. Repository evidence includes the FastAPI foundation, static frontend prototype, Docker configuration, API boundary, and smoke-test source; this checkpoint did not execute the tests.
- **Phase 1 — Cerebro Core: NOT STARTED.** No Job model, state machine, engineering loop, event system, or trace system is implemented in the repository.

## 2. Current Milestone

**Phase 1A — Job Lifecycle**

Status: **NOT STARTED**

Phase 1A is the next milestone. It is not currently implemented. The intended future lifecycle direction is provided by CroadMap; it must not be represented as current behavior.

## 3. Repository State

Verified tracked repository structure:

```text
Cerebro/
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── cerebro/
│       ├── __init__.py
│       ├── api/app.py
│       └── {agents, approvals, config, core, execution, experience,
│           jobs, memory, projects, providers, tools, trace}/__init__.py
├── frontend/
│   ├── index.html
│   ├── README.md
│   ├── css/{base,components,layout,views}.css
│   └── js/{api,app,state}.js
├── tests/test_api.py
├── workspace/.gitkeep
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

The domain directories listed above are present but, other than the API application, contain package markers and `.gitkeep` files only. The workspace directory is empty except for `.gitkeep`.

## 4. Backend Status

Status: **IMPLEMENTED / UNVERIFIED** for the minimal FastAPI foundation; all Cerebro domain functionality is **NOT STARTED**.

- `backend/pyproject.toml` requires Python `>=3.12`; the Docker base image is `python:3.12-slim`.
- `backend/cerebro/api/app.py` creates a FastAPI application titled `Cerebro API`, version `0.1.0`.
- Implemented HTTP routes are listed in [API Status](#11-api-status).
- The WebSocket route accepts a connection, emits one `{"type":"connected","service":"cerebro"}` message, and immediately closes. A persistent event stream is **NOT STARTED**.
- The package structure reserves boundaries for agents, approvals, config, core, execution, experience, jobs, memory, projects, providers, tools, and trace. No domain logic is implemented in those packages.
- Persistence, database access, schema definitions, migrations, and repositories are **NOT STARTED**.
- Authentication and authorization are **NOT STARTED**.
- Tool management, execution controls, and actual tool execution are **NOT STARTED**.
- `/api/system/health` reports `core`, `jobs`, `agents`, and `memory` as `"scaffold"`; it does not execute component health checks.

## 5. Frontend Status

Status: **IMPLEMENTED / UNVERIFIED** as a static UI prototype; backend integration is **NOT STARTED**.

- Technology: static HTML, CSS, and vanilla JavaScript. No frontend package manager, bundler, transpiler, or framework is present.
- `frontend/index.html` contains hash-routed prototype views for overview, jobs, job detail, approvals, activity, projects, agents, memory, experience, tools, providers, health, logs, YouTube, and settings.
- `frontend/js/state.js` contains hard-coded presentation state, including example jobs. `frontend/js/app.js` renders this local state and uses local toast messages for job creation and approval actions.
- `frontend/js/api.js` defines a browser client boundary for job list/read/create, approval, and WebSocket calls. `app.js` does not call this client; therefore there is no actual frontend-to-backend data integration.
- The browser WebSocket client points to `/ws/events`, but the current server closes the connection after one message.
- The frontend README labels several endpoints as suggested/proposed; those are not implemented merely because they appear in the frontend.

Known integration limitations:

- The FastAPI application serves the HTML document only at `/`. It has no enabled static mount for the frontend's `css/*` and `js/*` references. The only `app.mount` expression is conditional on `False` and targets `/assets`, while the HTML references `/css/...` and `/js/...`. Container runtime asset delivery is therefore **UNVERIFIED** and, based on the configured routes, likely unavailable.
- The client API contract is internally inconsistent: `frontend/README.md` proposes `POST /api/jobs/{id}/approve`, while `frontend/js/api.js` uses `POST /api/approvals/{id}/approve`. Neither route is currently implemented.

## 6. Docker / Deployment Status

Status: **IMPLEMENTED / UNVERIFIED**.

- `Dockerfile` builds from `python:3.12-slim`, installs `curl` and `git`, installs `backend/requirements.txt`, copies backend/frontend/workspace into `/app`, sets `PYTHONPATH=/app/backend`, exposes port `8000`, and starts Uvicorn with `cerebro.api.app:app` bound to `0.0.0.0:8000`.
- `docker-compose.yml` defines one `cerebro` service built from the repository Dockerfile. It maps `${CEREBRO_PORT:-8000}` to container port `8000`, reads `.env`, mounts `./workspace` at `/app/workspace`, and uses `restart: unless-stopped`.
- The Compose healthcheck calls `curl -fsS http://localhost:8000/api/health` every 15 seconds with a 5-second timeout, five retries, and a 15-second start period.
- No Compose build, container start, or healthcheck execution was run for this checkpoint. Operational status is **UNVERIFIED**.

## 7. Tests

Status: **UNVERIFIED**.

- Test file present: `tests/test_api.py`.
- It defines two TestClient tests:
  - `test_health` expects `GET /api/health` to return HTTP 200 and `status == "ok"`.
  - `test_system_health` expects `GET /api/system/health` to return HTTP 200 and `status == "healthy"`.
- No tests cover Job Lifecycle, persistence, schemas, state transitions, approvals, event delivery, traces, authorization, tools, execution, frontend behavior, static asset delivery, or Docker runtime behavior. Those test areas are **NOT STARTED**.
- Test command attempted for this checkpoint:

  ```powershell
  $env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPATH='backend'; python -m pytest -p no:cacheprovider tests/test_api.py -q
  ```

  Result: **UNVERIFIED**. PowerShell reported that `python.exe` could not be accessed by the environment, so pytest did not start and no pass/fail result was produced.

## 8. Verification Performed

The following checks were performed for this checkpoint:

- Inspected repository structure and tracked file list.
- Inspected `git status --short` before this documentation change: no output (clean working tree).
- Inspected the current branch: `main`.
- Inspected `git log --oneline -10`: one visible commit, `2473e3c chore: initialize Cerebro Docker foundation`.
- Inspected backend application, project configuration, dependency list, frontend files/README, Dockerfile, Compose configuration, and API test file.
- Inspected route and client-contract references using repository text search.
- Attempted the existing pytest health tests; the Python executable was inaccessible, so the endpoint behavior was not executed or independently verified.

## 9. Known Issues

| Status | Issue | Verified evidence |
|---|---|---|
| **IN PROGRESS** | Static frontend asset serving is incomplete or mismatched. | FastAPI only returns the index at `/`; the sole static mount is disabled and does not match the `css/*` and `js/*` asset URLs. Runtime behavior was not container-tested. |
| **NOT STARTED** | Persistent WebSocket event lifecycle. | The only WebSocket route sends one connection message and then closes. |
| **NOT STARTED** | Frontend/backend job and approval integration. | Browser API calls are defined but unused by UI code; backend job/approval routes do not exist. |
| **NOT STARTED** | Persistence and durable audit/event data. | No database package, schema, migration, model, or repository is present. |
| **IN PROGRESS** | API contract consolidation. | README and browser API client specify different approval route shapes. |
| **IN PROGRESS** | Accurate runtime health reporting. | System health exposes static scaffold labels rather than checked component state. |
| **UNVERIFIED** | Automated test execution in this environment. | Pytest could not start because Python was inaccessible. |

The hard-coded frontend jobs, approvals, logs, provider status, and health displays are prototype content, not verified backend state.

## 10. Database / Schema Status

Status: **NOT STARTED**.

No database configuration, database dependency, ORM, SQL schema, Pydantic domain schema, migration framework, repository, or persistence implementation exists in the inspected repository. No database was introduced for this checkpoint.

## 11. API Status

### IMPLEMENTED

| Endpoint | Current behavior | Verification status |
|---|---|---|
| `GET /` | Returns `/app/frontend/index.html`. | IMPLEMENTED / UNVERIFIED at runtime |
| `GET /api/health` | Returns a static service health payload. | IMPLEMENTED / UNVERIFIED; test exists but did not run |
| `GET /api/system/health` | Returns static component statuses, including scaffold labels. | IMPLEMENTED / UNVERIFIED; test exists but did not run |
| `WS /ws/events` | Accepts, sends one connection payload, then closes. | IMPLEMENTED / UNVERIFIED at runtime |

### PLANNED / NOT IMPLEMENTED

The frontend README proposes, but the backend does not implement:

- `GET /api/jobs`
- `GET /api/jobs/{id}`
- `POST /api/jobs`
- `GET /api/jobs/{id}/tasks`
- `GET /api/jobs/{id}/events`
- `POST /api/jobs/{id}/approve`
- `POST /api/jobs/{id}/reject`
- `GET /api/projects`
- `GET /api/tools`
- `GET /api/providers`
- `GET /api/memory`

`frontend/js/api.js` additionally names `POST /api/approvals/{id}/approve`; it is also **NOT IMPLEMENTED**.

## 12. Git Status

Before this task:

- Branch: `main`.
- Latest commit: `2473e3c chore: initialize Cerebro Docker foundation`.
- Working tree: clean; no uncommitted changes were reported by `git status --short`.

This checkpoint introduces `docs/development/current-state.md` as the only intended repository change. Git status must be checked again after writing this file before any future commit.

## 13. Architecture Decisions

### Evident from the repository

- The backend is a Python/FastAPI service, with Python `>=3.12` declared and Python 3.12 used in Docker.
- The frontend is intentionally a static vanilla HTML/CSS/JavaScript client; the frontend README says Python owns the system's intelligence, state, permissions, approvals, execution, memory, providers, and persistence.
- The browser and API are intended to share one service, as indicated by the API comment that this avoids CORS complexity in V1.
- The repository uses a single-container Compose deployment with a bind-mounted workspace and an HTTP healthcheck.
- Package names establish planned separation between job, approval, execution, agent, memory, project, provider, tool, trace, and configuration concerns. They do not establish implemented behavior.

### Development direction / CroadMap decision

- CroadMap identifies Phase 0 as completed/verified and Phase 1 as not started.
- The next milestone is Phase 1A — Job Lifecycle.
- The intended autonomy boundary is **Suggest → Approve → Execute**.
- Reliability precedes autonomy; the Engineer retains authority over goals, constraints, approvals, and final decisions.

## 14. Next Recommended Action

The next action is **Phase 1A — Job Lifecycle**, but implementation must not begin without a design and review step.

Before implementation, design and review:

- the Job model;
- the Job state machine and valid transitions;
- lifecycle event requirements;
- trace requirements;
- persistence approach;
- API contract; and
- relevant tests.

## 15. Handoff Instructions

If Codex becomes unavailable, continue from verified repository state:

1. Read `docs/development/current-state.md`.
2. Run `git status`.
3. Run `git log --oneline -10`.
4. Inspect `git diff`.
5. Inspect affected source files and tests.
6. Verify `current-state.md` against the actual repository state.
7. Determine the smallest unfinished logical task.
8. Continue manually.
9. Test and verify.
10. Update `current-state.md`.
11. Commit a coherent, verified checkpoint.

**The actual repository, tests, and Git history take precedence over this document if they disagree.**
