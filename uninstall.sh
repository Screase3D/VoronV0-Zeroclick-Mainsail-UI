#!/usr/bin/env bash
# voron0-dockprobe – uninstaller
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
exec "$(dirname "$(readlink -f "$0")")/install.sh" --uninstall "$@"
