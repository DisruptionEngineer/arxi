---
name: arxi-operator
description: ARXI Operator — AI-native pharmacy management system operations
---

# ARXI Operator

You manage the ARXI pharmacy system — seed data, restart services, query prescriptions, ingest e-prescribes, check service health, and perform any operational task via natural language.

## Quick Reference

| Service | Port | Process |
|---------|------|---------|
| Backend (FastAPI) | 8000 | `uvicorn arxi.main:app` |
| Frontend (Next.js) | 3000 | `npm run dev` |
| Worker (pipeline) | — | `python -m arxi.worker` |
| PostgreSQL 17 | 5432 | Homebrew service |
| Redis 7 | 6379 | Homebrew service |
| Ollama | 11434 | LaunchAgent |

**Login:** admin/admin123, pharmacist/pharma123, agent/agent123

## Service Management

All commands run from the project root via `just`:

```bash
just status             # Health check all services
just start              # Start everything (infra + backend + worker + frontend)
just stop               # Stop everything
just restart            # Full restart
just restart-backend    # Restart FastAPI only
just restart-frontend   # Restart Next.js only
just restart-worker     # Restart pipeline worker only
just logs-backend       # Tail backend logs
just logs-worker        # Tail worker logs
just seed               # Run unified seed (wipe + rebuild all data)
just test               # Run pytest
just migrate            # Run Alembic migrations
```

## Database Operations

**Seed (wipe + rebuild):**
```bash
cd backend && uv run python -m scripts.seed
```
Creates: 3 users, 80 drugs, 12 patients, 25 manual Rxs, 5 e-prescribe XMLs through pipeline.
The 5 e-prescribes enter as PARSED — the worker advances them to PENDING_REVIEW with patient linking.

**Direct SQL (read-only queries):**
```bash
cd backend && python3 -c "
from arxi.database import async_session
from sqlalchemy import text
import asyncio
async def q():
    async with async_session() as db:
        r = await db.execute(text('YOUR_QUERY'))
        for row in r.fetchall(): print(row)
asyncio.run(q())
"
```

**Useful queries:**
```sql
-- Rx status breakdown
SELECT status, COUNT(*) FROM arxi.prescriptions GROUP BY status ORDER BY status;

-- Unlinked prescriptions
SELECT id, patient_first_name, patient_last_name FROM arxi.prescriptions WHERE patient_id IS NULL;

-- Patient prescription count
SELECT p.first_name, p.last_name, COUNT(rx.id) as rx_count
FROM arxi.patients p LEFT JOIN arxi.prescriptions rx ON rx.patient_id = p.id
GROUP BY p.id ORDER BY rx_count DESC;

-- E-prescribes
SELECT LEFT(id,8), status, patient_first_name, patient_last_name, drug_description
FROM arxi.prescriptions WHERE source='e-prescribe';

-- Drug search
SELECT drug_name, ndc, dea_schedule FROM arxi.drugs WHERE drug_name ILIKE '%amox%';

-- Table counts
SELECT 'users' as t, COUNT(*) FROM public.users
UNION ALL SELECT 'drugs', COUNT(*) FROM arxi.drugs
UNION ALL SELECT 'patients', COUNT(*) FROM arxi.patients
UNION ALL SELECT 'prescriptions', COUNT(*) FROM arxi.prescriptions
UNION ALL SELECT 'audit_log', COUNT(*) FROM compliance.audit_log;
```

**Schemas:** `public` (users), `arxi` (prescriptions, patients, drugs), `compliance` (audit_log)

## API Operations

All API calls require auth. Get a session cookie first:

```bash
# Login (stores cookie)
curl -s -c /tmp/arxi.cookie http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Queue (with auth)
curl -s -b /tmp/arxi.cookie http://localhost:8000/api/intake/queue | python3 -m json.tool

# Queue filtered by status
curl -s -b /tmp/arxi.cookie 'http://localhost:8000/api/intake/queue?status=pending_review'

# Single Rx
curl -s -b /tmp/arxi.cookie http://localhost:8000/api/intake/{rx_id}

# Drug search
curl -s -b /tmp/arxi.cookie 'http://localhost:8000/api/drugs/search?q=amox'

# NPI validation
curl -s -b /tmp/arxi.cookie http://localhost:8000/api/prescribers/validate-npi/1003000126

# Patient list
curl -s -b /tmp/arxi.cookie http://localhost:8000/api/patients/

# Ingest e-prescribe XML
curl -s -b /tmp/arxi.cookie http://localhost:8000/api/intake/newrx \
  -H "Content-Type: application/json" \
  -d '"<?xml version=\"1.0\"?><Message>...</Message>"'
```

## Rx Pipeline

```
e-prescribe XML → POST /api/intake/newrx → PARSED
                                              ↓  (worker, 5s poll)
                                          VALIDATED
                                              ↓  (patient matching: exact → LLM → auto-create)
                                        PENDING_REVIEW
                                           ↙        ↘  (pharmacist in UI)
                                      APPROVED    REJECTED → CORRECTED → PENDING_REVIEW
```

Manual entry via `POST /api/intake/manual` goes directly to `PENDING_REVIEW` with patient linking.

## Patient Matching

3-tier system in `backend/arxi/modules/patient/matcher.py`:
- **Tier 1 (exact):** first_name + last_name + DOB → links to existing patient
- **Tier 2 (LLM-assisted):** Ollama fuzzy matching for nicknames, typos
- **Tier 3 (auto-create):** No match found → creates new patient record

## Directory Layout

```
backend/
  arxi/
    main.py                 # FastAPI app + routers
    worker.py               # Pipeline worker (5s poll)
    config.py               # Settings from .env
    database.py             # async_session factory
    auth/                   # JWT, RBAC, User model
    modules/
      intake/               # Rx parser, service, router, models, clinical_review
      patient/              # Patient model, matcher, normalization
      drug/                 # Drug model, search, NDC lookup
      prescriber/           # NPI validation (Luhn-10 + NPPES)
      compliance/           # Audit log
    agents/                 # IntakeAgent (rule-based + LLM validation)
  scripts/
    seed.py                 # Unified seed (wipe + rebuild all data)
  tests/
  alembic/
frontend/
  src/app/
    queue/                  # Rx queue with search + status filters
    review/[id]/            # Rx review + approve/reject
    new-rx/                 # Manual Rx entry with drug search + NPI validation
    ingest/                 # E-prescribe XML ingest page
    patients/               # Patient list + detail with Rx history
    audit/                  # Audit trail (admin only)
    profile/                # User profile
    demo/                   # AI pipeline demo page
  src/components/
    drug-search.tsx         # Drug autocomplete (NDC + name) with refill candidates
    npi-field.tsx           # NPI validation + NPPES lookup
    prescriber-picker.tsx   # Known prescriber selection + manual entry
    rx-queue-table.tsx      # Queue table with search, patient links
    rx-review-form.tsx      # Review form with CDS panel
    sidebar.tsx             # Nav: Dashboard, Queue, New Rx, E-Prescribe, Patients, Audit
.env                        # DATABASE_URL, JWT_SECRET, OLLAMA_URL, REDIS_URL
justfile                    # Service management commands
```

## Interpreting Natural Language

When users say things like:
- "seed the database" / "reset data" / "fresh seed" → `just seed`
- "restart everything" / "restart services" → `just restart`
- "restart the backend" → `just restart-backend`
- "restart the worker" → `just restart-worker`
- "what's the status" / "health check" → `just status`
- "how many prescriptions" / "rx count" → run status breakdown SQL
- "show pending" / "what needs review" → query `status='pending_review'`
- "show patients" / "patient list" → query arxi.patients
- "check worker logs" → `tail -20 .arxi/logs/worker.log`
- "check backend logs" → `tail -20 .arxi/logs/backend.log`
- "ingest an e-prescribe" → build XML and POST to the API
- "run tests" → `just test`
- "run migrations" → `just migrate`

Always report results clearly — counts, statuses, errors, and what action was taken.
