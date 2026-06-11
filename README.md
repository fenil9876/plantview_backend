# PlantView — Backend (FastAPI)

Dynamic, template-driven operations & inventory management for textile machines.

## Stack
- FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (pydantic-settings)
- PostgreSQL (hosted)

## Project layout
```
plantview_backend/
├── app/
│   ├── main.py            # FastAPI app factory + entrypoint
│   ├── api/               # routers (health, ... auth/templates/... to come)
│   ├── core/
│   │   ├── config.py      # settings from .env
│   │   └── database.py    # engine, session, declarative Base
│   └── models/            # SQLAlchemy models (import in __init__ for Alembic)
├── alembic/               # migrations
├── alembic.ini
├── requirements.txt
└── .env                   # local secrets (gitignored)
```

## Setup (Windows / PowerShell)
```powershell
cd plantview_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` → `.env` and fill in the DB credentials.

## Run
```powershell
uvicorn app.main:app --reload
```
- API docs: http://localhost:8000/docs
- Liveness: `GET /health`
- DB readiness: `GET /health/db`

## Migrations
```powershell
# create a new migration after adding/altering models
alembic revision --autogenerate -m "describe change"
# apply
alembic upgrade head
```

## Auth & RBAC
Roles: `admin` (builds templates, manages users), `operator` (feeds data), `viewer` (read-only).

Create the first admin (reads `FIRST_ADMIN_*` from `.env`):
```powershell
python -m app.scripts.seed_admin
```

Endpoints (prefixed with `/api/v1`):
- `POST /auth/login` — OAuth2 password form (`username` = email); returns a JWT.
- `GET  /auth/me` — current user.
- `GET  /users` — list users (admin only).
- `POST /users` — create a user with roles (admin only).
- `PUT  /users/{id}/roles` — replace a user's roles (admin only).

## Template builder (admin writes, authenticated reads)
All under `/api/v1`.

**Machines (master list)**
- `GET /machines` (`?active_only=true`), `GET /machines/{id}`
- `POST /machines`, `PATCH /machines/{id}`, `DELETE /machines/{id}`

**Templates** — a template has ordered `stages`, each with `field_defs` and optional `machine_ids`.
- `GET /templates`, `GET /templates/{id}` (full nested)
- `POST /templates` — create a whole template with nested stages + fields + machine links in one call
- `PATCH /templates/{id}` — metadata only (name/description/is_active)
- `DELETE /templates/{id}`

**Stages & fields (incremental editing)**
- `POST   /templates/{id}/stages`, `PATCH /templates/{id}/stages/{sid}`, `DELETE …/{sid}`
- `PUT    /templates/{id}/stages/{sid}/machines` — set the assigned machine ids
- `POST   /templates/{id}/stages/{sid}/fields`, `PATCH …/fields/{fid}`, `DELETE …/fields/{fid}`

**Field definition** = `{scope, key, label, data_type, required, options, validation, unit, order_index}`
- `scope`: `stage` | `machine_input` | `machine_output`
- `data_type`: `string` | `int` | `decimal` | `bool` | `date` | `datetime` | `enum` (`enum` requires `options`)
- `key` is the snake_case JSON key used in entry data; unique per `(stage, scope)`.

## Data entry (operator/admin writes, authenticated reads)
A **batch** is a physical lot that flows through a template's stages, accumulating
validated data. All under `/api/v1`.

- `POST /batches` — start a batch `{template_id, code}` (begins at the first stage)
- `GET  /batches` (`?template_id=&status=`), `GET /batches/{id}` (full nested entries)
- `PATCH /batches/{id}/status` — `in_progress` | `completed` | `cancelled`
- `DELETE /batches/{id}` (admin)
- `PUT  /batches/{id}/stages/{stage_id}/entry` — create/update one stage's data:
  ```json
  {
    "data": { "quantity": 12.5, "shift": "day" },
    "machines": [
      { "machine_id": 3, "input_data": {"yarn_in": 100}, "output_data": {"fabric_out": 95} }
    ]
  }
  ```
  The payload is validated against the stage's `field_defs` (per scope). Invalid input
  returns `422` with `{detail: {message, errors: [{scope, field, error}]}}`.

**Validation engine** (`app/services/field_validation.py`): coerces and checks each value
by `data_type` (int/decimal/bool/date/datetime/enum/string), enforces `required`, enum
`options`, and `validation` rules (`min`/`max`/`min_length`/`max_length`/`regex`), and
rejects unknown keys. Stored as JSONB normalized to JSON-safe values.

**Audit** — every batch and stage-entry mutation writes an `audit_log` row with
before/after JSONB snapshots. Read via `GET /audit?entity_type=&entity_id=&limit=`.

## Analytics (any authenticated user)
All under `/api/v1/analytics`. Two kinds, because field keys are admin-defined:

**Structural** (independent of field names)
- `GET /overview` — KPIs (templates/machines/batches/entries, batches by status)
- `GET /batches/by-status`, `GET /batches/by-template`
- `GET /batches/timeseries?interval=day|week|month&template_id=&status=`
- `GET /batches/by-current-stage?template_id=` — pipeline distribution (all stages, incl. zero)
- `GET /machines/activity` — per-machine entry & batch counts (utilization proxy)

**Dynamic field aggregation** (you name the field + op)
- `GET /field-aggregate?scope=&field=&op=&template_id=&stage_id=&machine_id=&group_by=`
  - `scope`: `stage` | `machine_input` | `machine_output`; `op`: `sum|avg|min|max|count`
  - `group_by=machine` (machine scopes only) returns per-machine values
  - Aggregates the JSONB field via `(data->>'key')::numeric`, counting only numeric values
- `GET /machines/io-summary?input_field=&output_field=&stage_id=&template_id=`
  - Per machine: input_total, output_total, **wastage** (in−out), **yield_pct**

Protect a route by role in code:
```python
from fastapi import Depends
from app.core.deps import require_roles
from app.core.roles import Role

@router.post("", dependencies=[Depends(require_roles(Role.ADMIN))])
def create_thing(...): ...
```
