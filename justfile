# ARXI — Local Development Service Management

set dotenv-load := true
set dotenv-required := false

root_dir := justfile_directory()
pid_dir := root_dir / ".arxi/pids"
log_dir := root_dir / ".arxi/logs"

# === Infrastructure (Docker) ===

# Start postgres and redis containers
start-infra:
	@docker compose up -d postgres redis
	@echo "Waiting for postgres..."
	@docker compose exec postgres sh -c 'until pg_isready -U arxi -d arxi -q; do sleep 0.5; done'
	@echo "Infra ready (postgres:5432, redis:6379)"

# Stop postgres and redis containers
stop-infra:
	@docker compose down
	@echo "Infra stopped"

# Show docker container status
infra-status:
	@docker compose ps

# Tail postgres logs
logs-postgres:
	docker compose logs -f postgres

# Tail redis logs
logs-redis:
	docker compose logs -f redis

# Wipe postgres data and start fresh (destructive!)
infra-reset:
	docker compose down -v
	@echo "Volumes removed — next start-infra will reinitialize"

# === Backend (uvicorn) ===

# Start backend API server (backgrounded)
start-backend:
	@mkdir -p {{pid_dir}} {{log_dir}}
	@if [ -f {{pid_dir}}/backend.pid ] && kill -0 $(cat {{pid_dir}}/backend.pid) 2>/dev/null; then \
		echo "Backend already running (PID $(cat {{pid_dir}}/backend.pid))"; \
	else \
		cd backend && nohup uv run uvicorn arxi.main:app --reload --host 0.0.0.0 --port 8000 \
			> {{log_dir}}/backend.log 2>&1 & \
		echo $! > {{pid_dir}}/backend.pid; \
		echo "Backend started (PID $!, port 8000)"; \
	fi

# Stop backend API server
stop-backend:
	@if [ -f {{pid_dir}}/backend.pid ]; then \
		PID=$(cat {{pid_dir}}/backend.pid); \
		if kill -0 $PID 2>/dev/null; then \
			kill $PID; \
			echo "Backend stopped (PID $PID)"; \
		else \
			echo "Backend was not running (stale PID $PID)"; \
		fi; \
		rm -f {{pid_dir}}/backend.pid; \
	else \
		echo "Backend is not running (no PID file)"; \
	fi

# Restart backend API server
restart-backend: stop-backend start-backend

# === Frontend (Next.js) ===

# Start frontend dev server (backgrounded)
start-frontend:
	@mkdir -p {{pid_dir}} {{log_dir}}
	@if [ -f {{pid_dir}}/frontend.pid ] && kill -0 $(cat {{pid_dir}}/frontend.pid) 2>/dev/null; then \
		echo "Frontend already running (PID $(cat {{pid_dir}}/frontend.pid))"; \
	else \
		cd frontend && nohup npm run dev \
			> {{log_dir}}/frontend.log 2>&1 & \
		echo $! > {{pid_dir}}/frontend.pid; \
		echo "Frontend started (PID $!, port 3000)"; \
	fi

# Stop frontend dev server
stop-frontend:
	@if [ -f {{pid_dir}}/frontend.pid ]; then \
		PID=$(cat {{pid_dir}}/frontend.pid); \
		if kill -0 $PID 2>/dev/null; then \
			kill $PID; \
			echo "Frontend stopped (PID $PID)"; \
		else \
			echo "Frontend was not running (stale PID $PID)"; \
		fi; \
		rm -f {{pid_dir}}/frontend.pid; \
	else \
		echo "Frontend is not running (no PID file)"; \
	fi

# Restart frontend dev server
restart-frontend: stop-frontend start-frontend

# === Worker (pipeline) ===

# Start pipeline worker (backgrounded)
start-worker:
	@mkdir -p {{pid_dir}} {{log_dir}}
	@if [ -f {{pid_dir}}/worker.pid ] && kill -0 $(cat {{pid_dir}}/worker.pid) 2>/dev/null; then \
		echo "Worker already running (PID $(cat {{pid_dir}}/worker.pid))"; \
	else \
		cd backend && nohup uv run python -m arxi.worker \
			> {{log_dir}}/worker.log 2>&1 & \
		echo $! > {{pid_dir}}/worker.pid; \
		echo "Worker started (PID $!, poll 5s)"; \
	fi

# Stop pipeline worker
stop-worker:
	@if [ -f {{pid_dir}}/worker.pid ]; then \
		PID=$(cat {{pid_dir}}/worker.pid); \
		if kill -0 $PID 2>/dev/null; then \
			kill $PID; \
			echo "Worker stopped (PID $PID)"; \
		else \
			echo "Worker was not running (stale PID $PID)"; \
		fi; \
		rm -f {{pid_dir}}/worker.pid; \
	else \
		echo "Worker is not running (no PID file)"; \
	fi

# Restart pipeline worker
restart-worker: stop-worker start-worker

# === Composite ===

# Start all services (infra + backend + worker + frontend)
start: start-infra start-backend start-worker start-frontend
	@echo "All services started"

# Stop all services
stop: stop-frontend stop-worker stop-backend stop-infra
	@echo "All services stopped"

# Restart all services
restart: stop start

# === Status + Logs ===

# Show status of all services
status:
	@echo "=== ARXI Services ==="
	@echo "--- Docker ---"
	@docker compose ps --format "table {{{{.Name}}}}\t{{{{.Status}}}}\t{{{{.Ports}}}}" 2>/dev/null || echo "  Docker Compose not running"
	@echo "--- App ---"
	@if [ -f {{pid_dir}}/backend.pid ] && kill -0 $(cat {{pid_dir}}/backend.pid) 2>/dev/null; then \
		echo "Backend:   UP (PID $(cat {{pid_dir}}/backend.pid), port 8000)"; \
	else \
		echo "Backend:   DOWN"; \
	fi
	@if [ -f {{pid_dir}}/frontend.pid ] && kill -0 $(cat {{pid_dir}}/frontend.pid) 2>/dev/null; then \
		echo "Frontend:  UP (PID $(cat {{pid_dir}}/frontend.pid), port 3000)"; \
	else \
		echo "Frontend:  DOWN"; \
	fi
	@if [ -f {{pid_dir}}/worker.pid ] && kill -0 $(cat {{pid_dir}}/worker.pid) 2>/dev/null; then \
		echo "Worker:    UP (PID $(cat {{pid_dir}}/worker.pid))"; \
	else \
		echo "Worker:    DOWN"; \
	fi
	@echo "Ollama:    $(curl -s -o /dev/null -w 'UP (%{http_code})' http://localhost:11434/api/tags 2>/dev/null || echo 'DOWN')"

# Tail backend logs
logs-backend:
	tail -f {{log_dir}}/backend.log

# Tail frontend logs
logs-frontend:
	tail -f {{log_dir}}/frontend.log

# Tail worker logs
logs-worker:
	tail -f {{log_dir}}/worker.log

# === Development ===

# Run database migrations
migrate:
	cd backend && uv run alembic upgrade head

# Run tests
test:
	cd backend && uv run pytest tests/ -v

# Wipe and rebuild all dev data (users, drugs, patients, prescriptions, e-prescribes)
seed:
	cd backend && uv run python -m scripts.seed

# Full setup: infra + migrate + seed (run once after clone)
setup: start-infra migrate seed
	@echo "Setup complete — run 'just start' to launch all services"
