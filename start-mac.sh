#!/bin/bash
# start-mac.sh -- Learning-By-Tooling lokal auf dem Mac starten
# Ausführen: chmod +x start-mac.sh && ./start-mac.sh

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${GREEN}=== Learning-By-Tooling starten ===${NC}"
echo "Pfad: $DIR"
echo ""

# Voraussetzungen prüfen
command -v python3 >/dev/null || { echo -e "${RED}python3 nicht gefunden${NC}"; exit 1; }
command -v node    >/dev/null || { echo -e "${RED}node nicht gefunden${NC}"; exit 1; }
command -v npm     >/dev/null || { echo -e "${RED}npm nicht gefunden${NC}"; exit 1; }

PY=$(python3 --version | awk '{print $2}')
NODE=$(node --version)
echo "Python: $PY | Node: $NODE"
echo ""

# Backend
echo -e "${YELLOW}[1/3] Backend vorbereiten...${NC}"
cd "$DIR/backend"

if [ ! -d venv ]; then
    python3 -m venv venv
    echo "     Virtualenv erstellt"
fi

source venv/bin/activate
pip install -r requirements.txt -q
echo "     Abhängigkeiten installiert"

# Frontend
echo -e "${YELLOW}[2/3] Frontend vorbereiten...${NC}"
cd "$DIR/frontend"
npm install --silent
echo "     npm install fertig"

# Starten
echo -e "${YELLOW}[3/3] Starten...${NC}"
echo ""

# Backend im Hintergrund
cd "$DIR/backend"
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8030 --reload &
BACKEND_PID=$!

sleep 1

# Frontend im Vordergrund (blockiert)
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}=== Learning-By-Tooling läuft ===${NC}"
echo ""
echo "  Backend:  http://localhost:8030"
echo "  Frontend: http://localhost:8031"
echo "  API Docs: http://localhost:8030/docs"
echo ""
echo "  Stoppen:  Ctrl+C"
echo ""

# Sauberes Beenden bei Ctrl+C
trap "echo ''; echo 'Stoppe Learning-By-Tooling...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait $FRONTEND_PID
