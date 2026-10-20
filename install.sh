#!/usr/bin/env bash
# voron0-dockprobe – Installer
#   ./install.sh               interaktive Installation
#   ./install.sh --analyze     nur Analyse, ändert nichts
#   ./install.sh --dry-run     zeigt, was passieren würde
#   ./install.sh --reconfigure Einstellungen neu abfragen
#   ./install.sh --help        alle Optionen
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if [ "$(id -u)" -eq 0 ]; then
  echo "Bitte nicht als root bzw. mit sudo starten – das Script fragt selbst nach sudo, wo nötig."
  exit 1
fi
command -v python3 >/dev/null || { echo "python3 fehlt (sudo apt install python3)"; exit 1; }
exec python3 scripts/installer.py "$@"
