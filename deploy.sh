#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Premium shell styling
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}=== STARTING INTERVIEW COPILOT DEPLOYMENT PIPELINE ===${NC}"

# 1. Dependency checks
echo -e "${CYAN}[1/4] Verifying local development system dependencies...${NC}"
if ! command -v docker &> /dev/null; then
    echo "CRITICAL: Docker is not installed or running. Please install Docker Desktop."
    exit 1
fi
if ! command -v docker-compose &> /dev/null; then
    echo "CRITICAL: docker-compose is not installed. Please check your path variables."
    exit 1
fi
echo -e "${GREEN}✓ Docker & Docker Compose are available.${NC}"

# 2. Spin up containers
echo -e "${CYAN}[2/4] Initializing PostgreSQL and Qdrant containers...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ Postgres and Qdrant are active in the background.${NC}"

# 3. Wait for PostgreSQL readiness
echo -e "${CYAN}[3/4] Sanity-checking PostgreSQL connection availability...${NC}"
until docker exec copilot_postgres pg_isready -U postgres &> /dev/null; do
  echo "PostgreSQL is starting up... pausing 2 seconds."
  sleep 2
done
echo -e "${GREEN}✓ PostgreSQL database is fully receptive on port 5432.${NC}"

# 4. Bootstrap FastAPI Backend Local Run
echo -e "${CYAN}[4/4] Starting FastAPI backend service...${NC}"
cd backend-service

# Setup virtual environment if missing
if [ ! -d "venv" ]; then
    echo "Creating python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo -e "${GREEN}✓ Dependencies synchronized successfully.${NC}"
echo -e "${PURPLE}====================================================${NC}"
echo -e "${GREEN}Interview Copilot AI Services are successfully established!${NC}"
echo -e "${CYAN}Backend: http://localhost:8000/health (FastAPI)${NC}"
echo -e "${CYAN}Qdrant Dashboard: http://localhost:6333/dashboard${NC}"
echo -e "${PURPLE}To launch backend local server, run: 'uvicorn app.main:app --reload'${NC}"
echo -e "${PURPLE}====================================================${NC}"
