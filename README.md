# ARXI — Agentic Rx Intake

AI-native pharmacy prescription management platform with real-time clinical decision support, e-prescribe processing, and local LLM inference.

## Features

- **E-Prescribe Pipeline** — NCPDP SCRIPT XML ingestion with automatic validation and patient matching
- **AI Clinical Decision Support** — Local LLM-powered drug interaction checks, allergy screening, dosage verification, and prescriber credential validation
- **AI Prescribe Assist** — Intelligent Rx recommendations based on patient history and drug data
- **Patient-Centric Workflow** — Smart drug selection with refill/renewal detection and prescriber history
- **3-Tier Patient Matching** — Exact match, LLM-assisted fuzzy matching, and auto-create
- **RBAC** — Role-based access control (admin, pharmacist, technician, agent)
- **Audit Trail** — Full compliance logging with before/after state tracking
- **NPI Validation** — Luhn-10 checksum + NPPES Registry lookup

## Prerequisites

Install these on your machine before starting:

| Dependency | Version | Install |
|-----------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| PostgreSQL | 16+ | `brew install postgresql@17` or [postgresql.org](https://www.postgresql.org/) |
| Redis | 7+ | `brew install redis` or [redis.io](https://redis.io/) |
| Ollama | latest | [ollama.com](https://ollama.com/) |
| UV | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Just | latest | `brew install just` or [just.systems](https://just.systems/) |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/DisruptionEngineer/arxi.git
cd arxi

# 2. Start infrastructure
brew services start postgresql@17
brew services start redis
ollama serve  # if not already running

# 3. Pull the LLM model
ollama pull qwen3:8b

# 4. Create the database
createdb arxi
psql arxi -c "CREATE USER arxi WITH PASSWORD 'arxi'; GRANT ALL ON DATABASE arxi TO arxi; ALTER USER arxi CREATEDB;"

# 5. Backend setup
cd backend
cp ../.env.example .env   # or create from scratch (see below)
uv sync                   # install Python dependencies
uv run alembic upgrade head  # run migrations

# 6. Seed demo data
uv run python -m scripts.seed

# 7. Frontend setup
cd ../frontend
npm install

# 8. Start everything (from project root)
cd ..
just start

# 9. Open the app
open http://localhost:3000
```

## Environment Variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://arxi:arxi@localhost:5432/arxi
REDIS_URL=redis://localhost:6379/0
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
JWT_SECRET=change-me-in-production
CORS_ORIGINS=["http://localhost:3000"]
UPLOAD_DIR=./uploads
```

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| pharmacist | pharma123 | Pharmacist |
| agent | agent123 | Agent |

## Service Management

All commands via `just` from the project root:

```bash
just start              # Start everything (infra + backend + worker + frontend)
just stop               # Stop everything
just restart            # Full restart
just status             # Health check all services
just restart-backend    # Restart FastAPI only
just restart-frontend   # Restart Next.js only
just restart-worker     # Restart pipeline worker only
just logs-backend       # Tail backend logs
just logs-worker        # Tail worker logs
just seed               # Wipe + rebuild all demo data
just test               # Run pytest
just migrate            # Run Alembic migrations
```

## Architecture

```
                    +-----------+
  E-Prescribe XML ---->| Parser  |----> PARSED
                    +-----------+
                         |
                    +-----------+
                    |  Worker   |----> VALIDATED ----> Patient Matching
                    +-----------+                         |
                         |                          +-----------+
                         |                          | Ollama    |  (fuzzy match)
                         |                          +-----------+
                         v
                   PENDING_REVIEW
                      /     \
               APPROVED    REJECTED ---> CORRECTED
```

**Backend:** FastAPI + SQLAlchemy (async) + Alembic + Redis

**Frontend:** Next.js 15 + TypeScript + Tailwind CSS

**AI:** Ollama (local) with qwen3:8b for clinical review, prescribe-assist, and patient matching

**Database Schemas:**
- `public` — users
- `arxi` — patients, prescriptions, drugs
- `compliance` — audit_log

## Optional: Docker Compose

For infrastructure only (Postgres, Redis, Ollama):

```bash
docker compose up -d postgres redis ollama
```

Then run backend/frontend locally as above.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/intake/queue` | Prescription queue |
| GET | `/api/intake/{id}` | Single prescription |
| POST | `/api/intake/manual` | Manual Rx entry |
| POST | `/api/intake/newrx` | E-prescribe XML ingest |
| POST | `/api/intake/{id}/review` | Review (approve/reject) |
| POST | `/api/intake/{id}/clinical-review` | Run AI clinical review |
| POST | `/api/intake/prescribe-assist` | AI prescribe assist |
| GET | `/api/drugs/search` | Drug typeahead search |
| GET | `/api/drugs/ndc/{ndc}` | Drug lookup by NDC |
| GET | `/api/patients/` | Patient list |
| GET | `/api/patients/{id}` | Patient detail |
| GET | `/api/patients/{id}/rx-context` | Patient Rx context (prescribers + refill candidates) |
| GET | `/api/prescribers/validate-npi/{npi}` | NPI validation |
| GET | `/api/compliance/audit-log` | Audit trail |

## License

MIT
