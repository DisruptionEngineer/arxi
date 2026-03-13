# ARXI — Agentic Rx Intake

AI-native pharmacy prescription management platform with real-time clinical decision support, e-prescribe processing, and local LLM inference.

## Features

- **E-Prescribe Pipeline** — NCPDP SCRIPT XML ingestion with automatic validation and patient matching
- **AI Clinical Decision Support** — Local LLM-powered drug interaction checks, allergy screening, dosage verification, and prescriber credential validation
- **AI Prescribe Assist** — Intelligent Rx recommendations based on patient history and drug data
- **Real-Time AI Pipeline Demo** — SSE-streamed 4-stage inference visualization (data gathering → prompt construction → LLM inference → response parsing)
- **Patient-Centric Workflow** — Smart drug selection with refill/renewal detection and prescriber history
- **3-Tier Patient Matching** — Exact match, LLM-assisted fuzzy matching, and auto-create
- **RBAC** — Role-based access control (admin, pharmacist, technician, agent)
- **Audit Trail** — Full compliance logging with before/after state tracking
- **NPI Validation** — Luhn-10 checksum + NPPES Registry lookup

## Prerequisites

| Dependency | Version | Install |
|-----------|---------|---------|
| Docker | 24+ | [docker.com](https://www.docker.com/) |
| Python | 3.12+ | [python.org](https://www.python.org/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| Ollama | latest | [ollama.com](https://ollama.com/) |
| UV | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Just | latest | `brew install just` or [just.systems](https://just.systems/) |

> Postgres and Redis run in Docker — no need to install them natively.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/DisruptionEngineer/arxi.git
cd arxi

# 2. Backend env
cd backend
cp ../.env.example .env   # or create from scratch (see below)
cd ..

# 3. Pull the LLM model
ollama pull qwen3:8b

# 4. One-command setup (starts Docker, runs migrations, seeds data)
just setup

# 5. Install frontend deps
cd frontend && npm install && cd ..

# 6. Start everything
just start

# 7. Open the app
open http://localhost:3000
```

Login: `pharmacist` / `pharma123`

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
# Lifecycle
just start              # Start everything (Docker + backend + worker + frontend)
just stop               # Stop everything (including Docker containers)
just restart            # Full restart
just status             # Health check all services
just setup              # First-time setup (Docker + migrate + seed)

# Individual services
just restart-backend    # Restart FastAPI only
just restart-frontend   # Restart Next.js only
just restart-worker     # Restart pipeline worker only

# Infrastructure
just start-infra        # Start Docker containers only
just stop-infra         # Stop Docker containers
just infra-status       # Docker container status
just infra-reset        # Wipe Docker volumes and start fresh

# Logs
just logs-backend       # Tail backend logs
just logs-frontend      # Tail frontend logs
just logs-worker        # Tail worker logs
just logs-postgres      # Tail Postgres container logs

# Development
just migrate            # Run Alembic migrations
just seed               # Wipe + rebuild all demo data
just test               # Run pytest
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

**Frontend:** Next.js 16 + TypeScript + Tailwind CSS

**AI:** Ollama (local) with qwen3:8b for clinical review, prescribe-assist, and patient matching

**Infrastructure:** Docker Compose (Postgres 16 + Redis 7)

**Database Schemas:**
- `public` — users, alembic_version
- `arxi` — patients, prescriptions, drugs
- `compliance` — audit_log

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
| POST | `/api/intake/{id}/clinical-review-stream` | SSE streaming clinical review |
| POST | `/api/intake/prescribe-assist` | AI prescribe assist |
| POST | `/api/intake/prescribe-assist-stream` | SSE streaming prescribe assist |
| GET | `/api/drugs/search` | Drug typeahead search |
| GET | `/api/drugs/ndc/{ndc}` | Drug lookup by NDC |
| GET | `/api/patients/` | Patient list |
| GET | `/api/patients/{id}` | Patient detail |
| GET | `/api/patients/{id}/rx-context` | Patient Rx context (prescribers + refill candidates) |
| GET | `/api/prescribers/validate-npi/{npi}` | NPI validation |
| GET | `/api/compliance/audit-log` | Audit trail |

## License

MIT
