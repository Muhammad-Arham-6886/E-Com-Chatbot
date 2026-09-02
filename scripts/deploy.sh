#!/bin/bash
set -e

echo "========================================================"
echo "  AI Commerce Assistant SaaS - Production Deployer"
echo "========================================================"

if [ ! -f .env ]; then
  echo "[!] .env file not found. Copying from .env.example..."
  cp .env.example .env
  echo "[!] Please configure your .env file before deploying to production."
  exit 1
fi

echo "[1/4] Building production container images..."
docker compose -f docker-compose.prod.yml build

echo "[2/4] Starting core databases and services..."
docker compose -f docker-compose.prod.yml up -d postgres redis ollama

echo "[3/4] Preloading local Ollama LLM and embedding models..."
docker compose -f docker-compose.prod.yml exec -T ollama ollama pull nomic-embed-text || true
docker compose -f docker-compose.prod.yml exec -T ollama ollama pull qwen2.5:1.5b || true

echo "[4/4] Starting backend, frontend, and Nginx reverse proxy..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "[✓] Deployment complete! Verification check:"
docker compose -f docker-compose.prod.yml ps
