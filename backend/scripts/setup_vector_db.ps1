# ==============================================================================
# Verism AI - Vector Database (Qdrant) Management Script
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Verism AI - Qdrant Vector Database Initializer" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Docker status
Write-Host "`n[1/4] Checking Qdrant Docker Container..." -ForegroundColor Yellow
$qdrantContainer = docker ps -a --filter "name=local-qdrant" --format "{{.Status}}"

if (-not $qdrantContainer) {
    Write-Host "Creating and starting local-qdrant container on port 6333..." -ForegroundColor Green
    docker run -d --name local-qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
} elseif ($qdrantContainer -notmatch "Up") {
    Write-Host "Starting existing local-qdrant container..." -ForegroundColor Green
    docker start local-qdrant
} else {
    Write-Host "local-qdrant is already running ($qdrantContainer)" -ForegroundColor Green
}

# 2. Test HTTP API
Write-Host "`n[2/4] Verifying Qdrant HTTP REST API on http://localhost:6333..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -Method Get -TimeoutSec 5
    Write-Host "Qdrant REST API is healthy: $health" -ForegroundColor Green
} catch {
    Write-Host "Warning: Waiting 3 seconds for Qdrant to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    $health = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -Method Get
    Write-Host "Qdrant REST API is healthy: $health" -ForegroundColor Green
}

# 3. Verify Collections
Write-Host "`n[3/4] Querying Vector Collections..." -ForegroundColor Yellow
$collections = Invoke-RestMethod -Uri "http://localhost:6333/collections" -Method Get
Write-Host "Active collections in Qdrant:" -ForegroundColor Green
$collections.result.collections | ForEach-Object { Write-Host " - $($_.name)" -ForegroundColor White }

# 4. Run Vector Indexing Test
Write-Host "`n[4/4] Verifying Python Vector Service Integration..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe .\scripts\verify_vector_db.py

Write-Host "`n[SUCCESS] Qdrant Vector Database is online and ready for peer plagiarism indexing!" -ForegroundColor Green
