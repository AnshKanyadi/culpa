#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

echo -e "${BLUE}culpa${RED}.${NC} setup"
echo ""

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}python3 not found. Install Python 3.12+ first.${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}node not found. Install Node.js 18+ first.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${DIM}Python ${PYTHON_VERSION}${NC}"
echo -e "${DIM}Node $(node --version)${NC}"
echo ""

if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

echo -e "${BLUE}Activating venv and installing Python deps...${NC}"
source .venv/bin/activate
pip install -e ".[all,dev]" -q

echo -e "${BLUE}Installing dashboard deps...${NC}"
cd dashboard && npm install --silent 2>/dev/null && cd ..

if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file...${NC}"
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    cat > .env << EOF
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=72
DATABASE_URL=sqlite:///./culpa.db
CORS_ORIGINS=http://localhost:5173,http://localhost:8000
EOF
    echo -e "${DIM}Generated random JWT secret${NC}"
else
    echo -e "${DIM}.env already exists, skipping${NC}"
fi

echo -e "${BLUE}Initializing database...${NC}"
python3 -c "
import os
for line in open('.env'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ[k] = v
from server.storage.database import init_db
init_db()
print('Database ready')
"

echo ""
echo -e "${GREEN}Setup complete.${NC}"
echo ""
echo "  Start the server and dashboard:"
echo -e "    ${BLUE}./start.sh${NC}"
echo ""
echo "  Or manually:"
echo "    source .venv/bin/activate"
echo "    cd server && uvicorn main:app --reload"
echo "    cd dashboard && npm run dev"
echo ""
echo "  Record a session:"
echo "    culpa record \"my task\" -- python my_agent.py"
echo "    culpa proxy start --name \"my task\""
echo ""
