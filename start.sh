#!/bin/bash
#
# Startup script for LinkedIn Post Generator
# Starts both the API server and Web UI
#

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Log directory
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  LinkedIn Post Generator - Startup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"

    # Kill API server
    if [ ! -z "$API_PID" ] && kill -0 "$API_PID" 2>/dev/null; then
        echo -e "  ${YELLOW}→${NC} Stopping API server (PID: $API_PID)"
        kill "$API_PID" 2>/dev/null || true
    fi

    # Kill web server
    if [ ! -z "$WEB_PID" ] && kill -0 "$WEB_PID" 2>/dev/null; then
        echo -e "  ${YELLOW}→${NC} Stopping Web UI (PID: $WEB_PID)"
        kill "$WEB_PID" 2>/dev/null || true
    fi

    # Kill any remaining processes on ports
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
    lsof -ti:4321 2>/dev/null | xargs kill -9 2>/dev/null || true

    echo -e "${GREEN}✓ Shutdown complete${NC}"
    exit 0
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}✗ Virtual environment not found!${NC}"
    echo -e "  Run: ${YELLOW}python -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "web/node_modules" ]; then
    echo -e "${YELLOW}! Node modules not found. Installing...${NC}"
    cd web
    npm install
    cd ..
fi

echo -e "${BLUE}[1/3]${NC} Starting API server..."

# Kill any existing processes on port 8000
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# Start API server
source venv/bin/activate
nohup uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/api_server.log" 2>&1 &
API_PID=$!

# Wait for API to be ready
echo -e "  ${YELLOW}→${NC} Waiting for API server to start..."
for i in {1..15}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} API server running on ${GREEN}http://localhost:8000${NC} (PID: $API_PID)"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "  ${RED}✗${NC} API server failed to start. Check logs/api_server.log"
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${BLUE}[2/3]${NC} Starting Web UI..."

# Kill any existing processes on port 4321
lsof -ti:4321 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# Start web server
cd web
nohup npm run dev > "$LOG_DIR/web_server.log" 2>&1 &
WEB_PID=$!
cd ..

# Wait for web server to be ready
echo -e "  ${YELLOW}→${NC} Waiting for Web UI to start..."
for i in {1..15}; do
    if curl -s http://localhost:4321 > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Web UI running on ${GREEN}http://localhost:4321${NC} (PID: $WEB_PID)"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "  ${RED}✗${NC} Web UI failed to start. Check logs/web_server.log"
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${BLUE}[3/3]${NC} Checking services..."

# Test API health
API_HEALTH=$(curl -s http://localhost:8000/api/health | grep -o '"status":"ok"' || echo "")
if [ -n "$API_HEALTH" ]; then
    echo -e "  ${GREEN}✓${NC} API health check passed"
else
    echo -e "  ${YELLOW}!${NC} API health check warning"
fi

# Check if Ollama is running (for LLM)
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Ollama is running"
else
    echo -e "  ${YELLOW}!${NC} Ollama is not running (required for post generation)"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  ${GREEN}➜${NC}  API Server:  ${GREEN}http://localhost:8000${NC}"
echo -e "  ${GREEN}➜${NC}  Web UI:      ${GREEN}http://localhost:4321${NC}"
echo -e "  ${GREEN}➜${NC}  API Docs:    ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  ${YELLOW}→${NC}  API:  tail -f logs/api_server.log"
echo -e "  ${YELLOW}→${NC}  Web:  tail -f logs/web_server.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep script running and wait for signals
while true; do
    # Check if processes are still running
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo -e "${RED}✗ API server stopped unexpectedly${NC}"
        exit 1
    fi
    if ! kill -0 "$WEB_PID" 2>/dev/null; then
        echo -e "${RED}✗ Web UI stopped unexpectedly${NC}"
        exit 1
    fi
    sleep 2
done
