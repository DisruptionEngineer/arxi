#!/bin/bash
set -e
echo "Starting PharmagentC..."
docker compose up -d postgres redis ollama
echo "Waiting for PostgreSQL..."
sleep 5
docker compose run --rm backend alembic upgrade head
echo "Pulling Ollama model..."
docker compose exec ollama ollama pull qwen3:8b-optimized
docker compose up -d
echo "PharmagentC is running at http://localhost:3000"
