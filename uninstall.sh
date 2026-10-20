#!/usr/bin/env bash
# voron0-dockprobe – Deinstallation
set -euo pipefail
exec "$(dirname "$(readlink -f "$0")")/install.sh" --uninstall "$@"
