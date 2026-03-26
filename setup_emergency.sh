#!/bin/bash
# Chakravyuh Emergency Features - Quick Setup & Test Script
# Usage: bash setup_emergency_features.sh

set -e

echo "🚀 Chakravyuh Emergency Features Setup"
echo "======================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found. Please run from project root.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"
cd dashboard-deploy
npm install 2>&1 | grep -E "(added|up to date|npm warn)" || echo "Dependencies ready"
cd ..

echo -e "${GREEN}✅ Step 1 Complete${NC}"
echo ""

echo -e "${YELLOW}Step 2: Checking Python dependencies...${NC}"
if command -v python3 &> /dev/null; then
    python3 -m pip install --quiet fastapi uvicorn docker kafka-python 2>/dev/null || echo "Some packages already installed"
    echo -e "${GREEN}✅ Python packages ready${NC}"
else
    echo -e "${YELLOW}⚠️  Python3 not found. Please install: pip install -r backend/api/requirements.txt${NC}"
fi
echo ""

echo -e "${YELLOW}Step 3: Starting backend API...${NC}"
cd backend
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/api/stats > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend API running on http://localhost:8000${NC}"
else
    echo -e "${RED}❌ Backend failed to start. Check /tmp/backend.log${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
cd ..
echo ""

echo -e "${YELLOW}Step 4: Starting frontend dev server...${NC}"
cd dashboard-deploy
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
sleep 5

# Check if frontend is accessible
if curl -s http://localhost:5173/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend running on http://localhost:5173${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend may take a moment to start. Check /tmp/frontend.log${NC}"
fi
cd ..
echo ""

echo "======================================="
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "======================================="
echo ""
echo "📊 Dashboard: http://localhost:5173"
echo "🔌 API: http://localhost:8000"
echo ""
echo "🧪 Quick Test:"
echo "  1. Open http://localhost:5173 in your browser"
echo "  2. Look for 🚨 button in bottom-right corner"
echo "  3. Click to open Emergency Control Center"
echo "  4. Select a node and try an action"
echo ""
echo "📝 Logs:"
echo "  Backend: tail -f /tmp/backend.log"
echo "  Frontend: tail -f /tmp/frontend.log"
echo ""
echo "🛑 To stop:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "💡 Default test data:"
echo "  - Nodes: Delhi Node, Mumbai Node, Bangalore, Hyderabad"
echo "  - Blocked IPs: 203.168.1.1, 185.220.101.45"
echo "  - Mock alerts with critical threats"
echo ""

# Keep script running and cleanup on exit
trap "echo ''; echo -e '${YELLOW}Shutting down services...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT

wait
