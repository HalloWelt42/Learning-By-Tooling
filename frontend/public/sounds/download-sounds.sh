#!/bin/bash
# Sound-Assets fuer LernVault Gamification
# Alle Sounds sind Pixabay Content License (frei, keine Attribution noetig)
# Dieses Script laedt die Originale erneut herunter falls noetig.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Lade Sound-Assets herunter..."

# Korrekte Antwort -- kurzer positiver Ton
curl -L -o correct.mp3 "https://cdn.pixabay.com/audio/2025/08/24/audio_0461b7a976.mp3"
echo "  correct.mp3 ($(du -h correct.mp3 | cut -f1))"

# Muenzgeraeusch beim Ernten (Result-Screen Muenzenregen)
curl -L -o coin.mp3 "https://cdn.pixabay.com/audio/2025/08/24/audio_ab7e75c300.mp3"
echo "  coin.mp3 ($(du -h coin.mp3 | cut -f1))"

# Bonus-Sound bei Zusammenfassung am Ende
curl -L -o bonus.mp3 "https://cdn.pixabay.com/audio/2025/08/24/audio_13e886b3c5.mp3"
echo "  bonus.mp3 ($(du -h bonus.mp3 | cut -f1))"

# Fehlersound bei falscher Antwort
curl -L -o error.mp3 "https://cdn.pixabay.com/audio/2025/08/24/audio_4c16641a7d.mp3"
echo "  error.mp3 ($(du -h error.mp3 | cut -f1))"

# Perfekte Session -- 20+ Karten fehlerfrei
curl -L -o perfect.mp3 "https://cdn.pixabay.com/audio/2023/07/06/audio_e12e5bea9d.mp3"
echo "  perfect.mp3 ($(du -h perfect.mp3 | cut -f1))"

echo ""
echo "Fertig. Alle 5 Sounds heruntergeladen."
echo "Lizenz: Pixabay Content License (frei, keine Attribution)"
