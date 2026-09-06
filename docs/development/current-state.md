# Cerebro Development Current State

## Project

**Cerebro** — reliability-first, human-directed Collaborative AI Software Engineer.

> Engineer provides the vision. Cerebro provides the engineering capability. Together, they build the software.

---

## Current Development Phase

**Phase 1 — Cerebro Core**

### Current Milestone

**Phase 1B — Tasks**

**Status: COMPLETED / VERIFIED**

Phase 1A established the first persistent Cerebro domain lifecycle:

```text
CREATED
   ↓
UNDERSTANDING
   ↓
PLANNING
   ↓
PLAN_READY
   ↓
WAITING_FOR_APPROVAL
```

The lifecycle is controlled by an explicit state-transition policy.

Phase 1A deliberately stops at WAITING_FOR_APPROVAL. The transition from WAITING_FOR_APPROVAL to EXECUTING belongs to Phase 2 — Human Control / Approval Gates.

---

# Completed Work

## Phase 0 — Foundation

**Status: COMPLETED / VERIFIED**

Completed:

- Repository structure
- Python backend foundation
- FastAPI application
- Frontend foundation
- Docker structure
- Docker Compose configuration
- API boundary
- Health endpoints
- WebSocket endpoint scaffold
- Workspace directory
- Initial project documentation

Phase 0 was previously validated with the Dockerized application and health endpoint.

---

# Phase 1A — Job Lifecycle

**Status: COMPLETED / VERIFIED**

Implemented:

- Job domain model
- Job status enumeration
- Controlled job state transitions
- Job service
- Job repository abstraction
- SQLite repository adapter
- Persistent job storage
- Job REST API
- Job lifecycle tests
- Repository abstraction test
- API validation and error handling

## Job States

The current Phase 1A states are:

```text
CREATED
UNDERSTANDING
PLANNING
PLAN_READY
WAITING_FOR_APPROVAL
EXECUTING
OBSERVING
EVALUATING
COMPLETED
FAILED
CANCELLED
```

The full state vocabulary exists, while Phase 1A only permits progression through:

```text
CREATED
    ↓
UNDERSTANDING
    ↓
PLANNING
    ↓
PLAN_READY
    ↓
WAITING_FOR_APPROVAL
```

Terminal and failure/cancellation transitions are controlled by the transition policy.

WAITING_FOR_APPROVAL → EXECUTING is intentionally not permitted by the generic Phase 1A transition endpoint. Approval authority will be implemented in Phase 2.

---

# Phase 1B — Tasks

**Status: COMPLETED / VERIFIED**

Phase 1B introduces the persistent Task domain beneath Jobs without
implementing execution, approvals, events, or automatic Job transitions.

Implemented:

- Task domain model
- Task status enumeration
- Controlled Task state transitions
- Task service
- Task repository abstraction
- SQLite Task repository
- Persistent Task storage
- Task ordering by position
- Optimistic Task versioning
- Task REST API
- Parent Job validation at the API boundary
- Task lifecycle tests
- API integration tests

## Task States

The current Phase 1B Task states are:

```text
PENDING
READY
RUNNING
COMPLETED
FAILED
CANCELLED
```

## Task Lifecycle

The controlled lifecycle is:

```text
PENDING → READY → RUNNING → COMPLETED
                       ├── FAILED
                       └── CANCELLED

PENDING → CANCELLED
READY → CANCELLED
```

`COMPLETED`, `FAILED`, and `CANCELLED` are terminal states.

Phase 1B deliberately does not automatically transition the parent
Job based on Task state. Job orchestration remains a later concern.

## Persistence

Tasks are persisted independently in SQLite.

The current storage abstraction is:

```text
TaskService
    ↓
TaskRepository Protocol
    ↓
SqliteTaskRepository
```

Tasks are associated with exactly one Job through `job_id` and are
returned in `position ASC, id ASC` order.

## Verification

Automated verification:

```text
14 tests passed
2 warnings
```

Live runtime verification confirmed:

- Task creation through the REST API
- Multiple Tasks belonging to the same Job
- Task listing and position ordering
- `PENDING → READY`
- `READY → RUNNING`
- `RUNNING → COMPLETED`
- `PENDING → CANCELLED`
- Terminal-state protection for `COMPLETED`
- Terminal-state protection for `CANCELLED`
- Optimistic version increments
- SQLite persistence
- Persistence across Uvicorn application restart

A stale Uvicorn process initially caused the Task endpoint to return
`404`. The process was identified and stopped, the current application
was restarted, and the Task API then passed live runtime verification.

The parent Job remained `CREATED` throughout Task transitions, as
required by the Phase 1B boundary.

# Backend Structure

Current Job Lifecycle implementation:

```text
backend/
└── cerebro/
    ├── api/
    │   ├── app.py
    │   └── jobs.py
    │
    └── jobs/
        ├── __init__.py
        ├── models.py
        ├── repository.py
        ├── service.py
        └── state.py
```

Supporting development tests:

```text
tests/
├── test_api.py
└── test_jobs.py
```

---

# Job Domain

The Job model currently contains:

- Job ID
- Objective
- Optional project reference
- Job status
- Creation timestamp
- Updated timestamp
- Version

The version is incremented when a job transition is persisted.

---

# State Transition Policy

Job state transitions are explicitly controlled.

Invalid transitions are rejected rather than allowing arbitrary state changes.

Example:

```text
WAITING_FOR_APPROVAL
        ↓
    EXECUTING
```

is currently rejected by the generic Phase 1A transition endpoint.

This is intentional because human approval is a Phase 2 capability.

The transition policy therefore prevents Phase 1A from implicitly bypassing the future approval system.

---

# Persistence Architecture

Persistence is required, but the storage implementation is abstracted behind a domain-oriented repository contract.

Current architecture:

```text
                         Cerebro
                            │
                            ▼
                       Job Service
                            │
                            ▼
                    JobRepository
                       (Protocol)
                            │
                            ▼
                  SqliteJobRepository
                            │
                            ▼
                         SQLite
```

Dependency direction:

```text
API
 ↓
Job Service
 ↓
Job Repository Interface
 ↓
SQLite Repository Adapter
 ↓
SQLite
```

The JobService depends on the JobRepository abstraction rather than directly depending on SQLite.

SQLite is currently the concrete persistence adapter and is not part of the Cerebro Core contract.

The current repository contract is domain-oriented:

```text
create
get
list
transition
```

Future domain repositories can follow the same architectural pattern:

```text
TaskRepository
PlanRepository
EventRepository
TraceRepository
```

The project should avoid introducing a giant generic storage abstraction unless a concrete requirement emerges.

---

# Database

Current persistence implementation:

**SQLite**

Default database location:

```text
workspace/data/cerebro.sqlite3
```

The application supports an explicit database path through:

```text
CEREBRO_DATABASE_PATH
```

Persistence has been verified using a dedicated runtime SQLite database.

A job was created, transitioned, the application was stopped, the application was restarted using the same database, and the job remained available with its state, version, and timestamps preserved.

Therefore persistence is:

**COMPLETED / VERIFIED**

---

# API

## Health

```text
GET /api/health
```

Verified successfully.

## System Health

```text
GET /api/system/health
```

Existing endpoint remains available.

## Create Job

```text
POST /api/jobs
```

Creates a persistent Job in CREATED state.

## List Jobs

```text
GET /api/jobs
```

Returns persisted jobs.

## Get Job

```text
GET /api/jobs/{job_id}
```

Returns a specific persisted job.

## Transition Job

```text
POST /api/jobs/{job_id}/transition
```

Request:

```json
{
  "target_state": "UNDERSTANDING"
}
```

The API validates the requested state and applies the domain transition policy.

Invalid transitions return an error instead of mutating the job.

---

# Verification

## Automated Tests

Full test suite:

```text
8 passed, 2 warnings
```

Command:

```text
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
........ [100%]

8 passed, 2 warnings
```

The warnings are dependency deprecation warnings from the installed FastAPI/Starlette/AnyIO stack. They did not cause test failures.

## Repository Abstraction Test

The Job Service was tested using a fake repository implementation.

This verifies that the service depends on the repository contract rather than requiring the SQLite implementation directly.

Result:

```text
6 passed, 2 warnings
```

for the Job Lifecycle test suite.

## Runtime HTTP Verification

A real Uvicorn instance was started and verified through HTTP requests.

Verified:

- Health endpoint
- Job creation
- Job listing
- Job retrieval
- Valid state transitions
- Invalid state transition rejection

The verified lifecycle progression was:

```text
CREATED
  ↓
UNDERSTANDING
  ↓
PLANNING
  ↓
PLAN_READY
  ↓
WAITING_FOR_APPROVAL
```

## Persistence Verification

SQLite persistence was verified across an application restart.

The same job database was reused after stopping and restarting Uvicorn.

The previously created job remained available with its state and version intact.

Therefore persistence is:

**COMPLETED / VERIFIED**

---

# Current Implementation Status

| Component | Status |
| --- | --- |
| Phase 0 Foundation | COMPLETED / VERIFIED |
| Job domain model | COMPLETED / VERIFIED |
| Job state model | COMPLETED / VERIFIED |
| Transition policy | COMPLETED / VERIFIED |
| Job service | COMPLETED / VERIFIED |
| Job repository abstraction | COMPLETED / VERIFIED |
| SQLite repository | COMPLETED / VERIFIED |
| Job persistence | COMPLETED / VERIFIED |
| Job REST API | COMPLETED / VERIFIED |
| Job lifecycle tests | COMPLETED / VERIFIED |
| Repository boundary test | COMPLETED / VERIFIED |
| Runtime HTTP behavior | COMPLETED / VERIFIED |
| Persistence across restart | COMPLETED / VERIFIED |
| WebSocket event system | NOT STARTED |
| Task model/lifecycle | COMPLETED / VERIFIED |
| Plan model | NOT STARTED |
| Approval system | NOT STARTED |
| Execution system | NOT STARTED |
| Decision trace system | NOT STARTED |
| Full Engineering Loop | NOT STARTED |
| Memory / Experience | NOT STARTED |
| Dashboard integration | NOT STARTED |
| YouTube application | NOT STARTED |

---

# Known Issues

The following items remain intentionally outside Phase 1A:

1. WebSocket events are still only scaffolded.
2. The frontend is not yet connected to the real Job API lifecycle.
3. Human approval gates are not yet implemented.
4. Execution controls and permissions are not yet implemented.
5. Tasks have not yet been implemented.
6. Plans and decision traces have not yet been implemented.
7. The Engineering Loop has not yet been implemented.
8. Memory and Experience systems have not yet been implemented.
9. Authentication/authorization has not yet been implemented.

These are future milestones and should not be added to Phase 1A merely to make the current milestone appear more complete.

---

# Architecture Decisions

## Human-directed autonomy

Initial Cerebro autonomy follows:

```text
Cerebro analyzes
      ↓
Cerebro proposes
      ↓
Engineer reviews
      ↓
Engineer approves
      ↓
Cerebro executes
      ↓
Cerebro reports result
```

Reliability takes priority over autonomy.

## Domain-oriented architecture

Business logic should remain outside API route handlers.

Preferred structure:

```text
API
 ↓
Cerebro Engine / Service
 ↓
Domain
 ↓
Repository Interface
 ↓
Concrete Adapter
```

## Storage abstraction

Cerebro Core must not depend directly on a specific database technology.

For the current Job domain:

```text
JobService
    ↓
JobRepository Protocol
    ↓
SqliteJobRepository
```

SQLite is an implementation detail that can later be replaced by another repository adapter.

## Controlled state transitions

Jobs cannot arbitrarily change state.

All transitions pass through the domain transition policy.

## Phase boundaries

Phase 1A establishes the persistent Job lifecycle.

Phase 2 owns human approval and execution authorization.

Later phases own tools, agents, debugging, memory, and applications.

---

# Phase 1C-A — Event Domain Model + Event Persistence

**Status: COMPLETED / VERIFIED**

Implemented:

- Event model
- Event types
- Immutable event records
- EventRepository
- SQLite persistence
- JSON payload serialization
- Deterministic ordering
- Job/Task filtering
- Duplicate-ID protection
- 10 Event tests
- Full suite: **24 passed, 2 warnings**

Phase 1C-A deliberately does not perform automatic event emission.

There is no WebSocket integration yet.

The Event domain remains an independent domain/persistence layer and
has not been connected to the existing Job or Task lifecycle.

The next milestone is: **Phase 1C-B — Lifecycle Event Emission**.

# Git State

Current branch:

```text
main
```

Previous development checkpoints:

```text
5f02cf517b003866b9b262cade5eedbd35958a16
```

Commit message:

```text
docs: establish development state checkpoint
```

Phase 1A checkpoint:

```text
4fc25e8
```

Commit message:

```text
feat: implement Phase 1A job lifecycle
```

Phase 1B implementation and verification are now ready to be
committed as the next coherent development checkpoint.

The repository is intentionally not being pushed to origin at this
checkpoint.

# Current Milestone Result

Phase 1B has achieved its intended purpose:

> Cerebro now has a persistent Task domain associated with Jobs, a controlled Task lifecycle, a service layer, a storage abstraction, SQLite persistence, optimistic versioning, a verified REST API, and verified runtime behavior across application restarts.

The Task lifecycle is implemented, persisted, tested, and verified
through the real application.

Phase 1A remains complete and provides the persistent Job lifecycle
that the Task domain belongs to.
