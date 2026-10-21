#!/usr/bin/env bash
# voron0-dockprobe – installer
# SPDX-License-Identifier: GPL-3.0-or-later
#
#   ./install.sh               interactive installation
#   ./install.sh --analyze     analysis only, changes nothing
#   ./install.sh --dry-run     show what would happen
#   ./install.sh --reconfigure ask for the settings again
#   ./install.sh --lang en     English output (de = German)
#   ./install.sh --help        all options
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if [ "$(id -u)" -eq 0 ]; then
  echo "Please do not run as root or with sudo – the script asks for sudo itself where needed."
  echo "Bitte nicht als root bzw. mit sudo starten – das Script fragt selbst nach sudo, wo nötig."
  exit 1
fi
command -v python3 >/dev/null || { echo "python3 is missing / fehlt (sudo apt install python3)"; exit 1; }
exec python3 scripts/installer.py "$@"
