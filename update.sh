#!/bin/bash
# Learning-By-Tooling Update-Script
# Verwendung: ./update.sh <version>
# Beispiel:   ./update.sh 3.0.0
#
# NIEMALS gelöscht: data/ (DB) und uploads/ (Dokumente)

set -e

VERSION=${1:-""}
if [ -z "$VERSION" ]; then
  echo "Verwendung: ./update.sh <version>"
  exit 1
fi

ZIP="/tmp/lbt-v${VERSION}.zip"

if [ ! -f "$ZIP" ]; then
  echo "Datei nicht gefunden: $ZIP"
  echo "Zuerst: scp lbt-v${VERSION}.zip pi@192.168.178.49:/tmp/"
  exit 1
fi

echo "=== Learning-By-Tooling Update auf v${VERSION} ==="

# DB-Backup
if [ -f "./data/lbt.db" ]; then
  cp ./data/lbt.db "./data/lbt.db.bak.$(date +%Y%m%d%H%M)"
  echo "DB-Backup erstellt"
fi

# Entpacken in Temp
rm -rf /tmp/lbt-update
unzip -o "$ZIP" -d /tmp/lbt-update/
SRC="/tmp/lbt-update"

# Nur Code + Konfiguration ersetzen -- NIEMALS data/ oder uploads/
cp -r "$SRC/backend"         ./
cp -r "$SRC/frontend"        ./
cp    "$SRC/docker-compose.yml" ./
cp    "$SRC/update.sh"          ./
chmod +x ./update.sh ./start-mac.sh

rm -rf /tmp/lbt-update

# Sicherstellen dass Datenpfade existieren
mkdir -p data uploads

# Nur npm-Cache löschen, nicht die DB
docker compose down
docker volume rm lbt-nm 2>/dev/null || true
docker compose up -d

echo ""
echo "=== Update auf v${VERSION} abgeschlossen ==="
echo "Erhalten: data/, uploads/"
