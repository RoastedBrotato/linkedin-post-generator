#!/bin/bash
#
# Stop script for LinkedIn Post Generator
# Stops both the API server and Web UI
#

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping LinkedIn Post Generator...${NC}"
echo ""

# Stop processes on port 8000 (API)
if lsof -ti:8000 >/dev/null 2>&1; then
    echo -e "  ${YELLOW}→${NC} Stopping API server (port 8000)"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} API server stopped"
else
    echo -e "  ${YELLOW}→${NC} API server not running"
fi

# Stop processes on port 4321 (Web UI)
if lsof -ti:4321 >/dev/null 2>&1; then
    echo -e "  ${YELLOW}→${NC} Stopping Web UI (port 4321)"
    lsof -ti:4321 | xargs kill -9 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Web UI stopped"
else
    echo -e "  ${YELLOW}→${NC} Web UI not running"
fi

echo ""
echo -e "${GREEN}✓ All services stopped${NC}"
