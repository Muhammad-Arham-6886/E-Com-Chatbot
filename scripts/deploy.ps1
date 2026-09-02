Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  AI Commerce Assistant SaaS - Windows Production Deployer" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Write-Host "[!] .env file not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[!] Please configure your .env file before deploying to production." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/4] Building production container images..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml build

Write-Host "[2/4] Starting core databases and services..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml up -d postgres redis ollama

Write-Host "[3/4] Preloading local Ollama LLM and embedding models..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml exec -T ollama ollama pull nomic-embed-text
docker compose -f docker-compose.prod.yml exec -T ollama ollama pull qwen2.5:1.5b

Write-Host "[4/4] Starting backend, frontend, and Nginx reverse proxy..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml up -d

Write-Host ""
Write-Host "[✓] Deployment complete! Active containers:" -ForegroundColor Cyan
docker compose -f docker-compose.prod.yml ps
