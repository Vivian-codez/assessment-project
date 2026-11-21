# ==============================================================================
# Verism AI - Vector Database (Qdrant) Management Script
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
# Execute command: Write-Host "  Verism AI - Qdrant Vector Database Initializer" -Foregro
Write-Host "  Verism AI - Qdrant Vector Database Initializer" -ForegroundColor Cyan
# Execute command: Write-Host "==========================================================
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Docker status
Write-Host "`n[1/4] Checking Qdrant Docker Container..." -ForegroundColor Yellow
# Execute command: $qdrantContainer = docker ps -a --filter "name=local-qdrant" --format 
$qdrantContainer = docker ps -a --filter "name=local-qdrant" --format "{{.Status}}"

# Execute command: if (-not $qdrantContainer) {
if (-not $qdrantContainer) {
    # Execute command: Write-Host "Creating and starting local-qdrant container on port 6333.
    Write-Host "Creating and starting local-qdrant container on port 6333..." -ForegroundColor Green
    # Execute command: docker run -d --name local-qdrant -p 6333:6333 -p 6334:6334 qdrant/qdr
    docker run -d --name local-qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
# Execute command: } elseif ($qdrantContainer -notmatch "Up") {
} elseif ($qdrantContainer -notmatch "Up") {
    # Execute command: Write-Host "Starting existing local-qdrant container..." -ForegroundCo
    Write-Host "Starting existing local-qdrant container..." -ForegroundColor Green
    # Execute command: docker start local-qdrant
    docker start local-qdrant
# Execute command: } else {
} else {
    # Execute command: Write-Host "local-qdrant is already running ($qdrantContainer)" -Foreg
    Write-Host "local-qdrant is already running ($qdrantContainer)" -ForegroundColor Green
}

# 2. Test HTTP API
Write-Host "`n[2/4] Verifying Qdrant HTTP REST API on http://localhost:6333..." -ForegroundColor Yellow
# Execute command: try {
try {
    # Execute command: $health = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -Meth
    $health = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -Method Get -TimeoutSec 5
    # Execute command: Write-Host "Qdrant REST API is healthy: $health" -ForegroundColor Gree
    Write-Host "Qdrant REST API is healthy: $health" -ForegroundColor Green
# Execute command: } catch {
} catch {
    # Execute command: Write-Host "Warning: Waiting 3 seconds for Qdrant to initialize..." -F
    Write-Host "Warning: Waiting 3 seconds for Qdrant to initialize..." -ForegroundColor Yellow
    # Execute command: Start-Sleep -Seconds 3
    Start-Sleep -Seconds 3
    # Execute command: $health = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -Meth
    $health = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -Method Get
    # Execute command: Write-Host "Qdrant REST API is healthy: $health" -ForegroundColor Gree
    Write-Host "Qdrant REST API is healthy: $health" -ForegroundColor Green
}

# 3. Verify Collections
Write-Host "`n[3/4] Querying Vector Collections..." -ForegroundColor Yellow
# Execute command: $collections = Invoke-RestMethod -Uri "http://localhost:6333/collectio
$collections = Invoke-RestMethod -Uri "http://localhost:6333/collections" -Method Get
# Execute command: Write-Host "Active collections in Qdrant:" -ForegroundColor Green
Write-Host "Active collections in Qdrant:" -ForegroundColor Green
# Execute command: $collections.result.collections | ForEach-Object { Write-Host " - $($_
$collections.result.collections | ForEach-Object { Write-Host " - $($_.name)" -ForegroundColor White }

# 4. Run Vector Indexing Test
Write-Host "`n[4/4] Verifying Python Vector Service Integration..." -ForegroundColor Yellow
# Execute command: & .\.venv\Scripts\python.exe .\scripts\verify_vector_db.py
& .\.venv\Scripts\python.exe .\scripts\verify_vector_db.py

# Execute command: Write-Host "`n[SUCCESS] Qdrant Vector Database is online and ready for
Write-Host "`n[SUCCESS] Qdrant Vector Database is online and ready for peer plagiarism indexing!" -ForegroundColor Green
