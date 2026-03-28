#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

if [ ! -d ".venv" ]; then
    echo -e "${RED}Run ./setup.sh first${NC}"
    exit 1
fi

source .venv/bin/activate

if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

cleanup() {
    echo ""
    echo -e "${DIM}Stopping...${NC}"
    kill $SERVER_PID $DASHBOARD_PID 2>/dev/null
    wait $SERVER_PID $DASHBOARD_PID 2>/dev/null
    echo -e "${GREEN}Done${NC}"
}
trap cleanup EXIT INT TERM

echo -e "${BLUE}culpa${RED}.${NC} starting"
echo ""

cd server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload 2>&1 | sed "s/^/$(printf "${CYAN}[server]${NC} ")/" &
SERVER_PID=$!
cd ..

cd dashboard
npm run dev 2>&1 | sed "s/^/$(printf "${GREEN}[dashboard]${NC} ")/" &
DASHBOARD_PID=$!
cd ..

echo ""
echo -e "  ${CYAN}API${NC}        http://localhost:8000"
echo -e "  ${GREEN}Dashboard${NC}  http://localhost:5173"
echo -e "  ${DIM}API docs${NC}   http://localhost:8000/docs"
echo ""
echo -e "  ${DIM}Press Ctrl+C to stop${NC}"
echo ""

wait
