# VoronV0-Zeroclick-Mainsail-UI

> [!NOTE]
> **This repository was written by Claude Opus 5.5**, Anthropic's AI model – code, macros, installer, web UI and
> documentation. Review the macros before using them on your printer and run the first dock moves slowly.

**Dock probe kit for the Voron V0.2:** Klipper macros, a one-command installer and a Probe page in Mainsail's sidebar,
for a magnetically docked [ZeroClick](https://github.com/zruncho3d/ZeroClick)-style probe on a printer that keeps its
Z endstop.

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
![Printer: Voron V0.2](https://img.shields.io/badge/printer-Voron%20V0.2-red)
![Klipper](https://img.shields.io/badge/firmware-Klipper-b12f35)
![Mainsail](https://img.shields.io/badge/UI-Mainsail-2196f3)
![Languages](https://img.shields.io/badge/languages-English%20%7C%20Deutsch-lightgrey)

![The Probe page inside Mainsail](docs/screenshot.png)

## What you get

- **Safe dock moves** – `ATTACH_PROBE` / `DETACH_PROBE` check the probe pin after every move, retry once slowly and
  stop with an error instead of carrying on with the probe in the wrong place.
- **Print guard** – `PROBE_GUARD` in `PRINT_START` makes sure the probe is docked before the print starts.
- **Hands-off probing** – `BED_MESH_CALIBRATE`, `SCREWS_TILT_CALCULATE` and `PROBE_ACCURACY` fetch and return the
  probe themselves; `CALIBRATE_ALL` heat-soaks, checks the screws and meshes in one go.
- **Z stays on the endstop** – the probe only measures relative heights, so its `z_offset` cannot shift your first layer.
- **Probe page** – *Operate* for daily use, *Setup & calibration* for the checklist, tests and settings, plus a history
  of all measurements. Uses Mainsail's own look and your theme.
- **Installer, updates, uninstaller** – backs up first, updates via Mainsail's update manager, removes everything again.
- **Optional KlipperScreen menu**, English and German throughout.

## Requirements

- Klipper, Moonraker and Mainsail (installed with [KIAUH](https://github.com/dw-0/kiauh) or MainsailOS)
- `QUERY_PROBE` reports **TRIGGERED** with the probe docked and **open** with it on the toolhead
  (NC switch: usually `^PIN` without `!`)
- A dock at the rear left, rear right, as in the ZeroClick sample – or any position you can describe with waypoints

Tested on a Voron V0.2 (Kirigami bed, Dragon Burner, BTT Pi) with Mainsail 2.19.

## Installation

```bash
cd ~
git clone https://github.com/Screase3D/VoronV0-Zeroclick-Mainsail-UI.git
cd VoronV0-Zeroclick-Mainsail-UI
./install.sh --dry-run      # shows every step, changes nothing
./install.sh
```

Run it as your normal user, not while printing. The installer reads your config, suggests every value, shows all
planned changes and asks before it touches anything. A backup goes to `~/dockprobe-backups/`.
It can also add `PROBE_GUARD` to your `PRINT_START` and the KlipperScreen menu.
Options and the list of changed files: [reference](docs/REFERENCE.md#installer).

## First calibration

Open **Probe** in Mainsail's sidebar. A fresh install starts in **Setup & calibration** – work through the checklist:

1. Probe detection – the docked probe must read TRIGGERED
2. Dock test – slowly, hand on the emergency stop
3. Accuracy – a range below 0.01 mm is very good
4. Bed screws – turn until all show ≈ 00:00
5. Z endstop paper test, then `SAVE_CONFIG`
6. Check z_offset – ≈ 0 means it fits, otherwise click **Apply**
7. Bed mesh, then `SAVE_CONFIG`

Redo step 5 after every turn of a bed screw. Afterwards switch to **Operate** – that's all you need day to day.

<table>
<tr>
<td width="50%"><img src="docs/control.png" alt="Operate: control panel"></td>
<td width="50%"><img src="docs/history.png" alt="History with trend charts"></td>
</tr>
</table>

## PRINT_START

```ini
[gcode_macro PRINT_START]
gcode:
  G28
  M190 S{params.BED|int}
  BED_MESH_CALIBRATE ADAPTIVE=1   # attaches and detaches the probe itself
  PROBE_GUARD                     # probe must be docked – docks it or stops the print
  M109 S{params.EXTRUDER|int}
```

`ADAPTIVE=1` needs `[exclude_object]` and *Label objects* in the slicer.

## KlipperScreen

On request the installer adds a **Probe** menu under *More* with attach/dock, tests, paper test, mesh and full
calibration. It is one include line plus a symlink; the uninstaller removes both.

<img src="docs/klipperscreen-probe.png" alt="The Probe menu in KlipperScreen" width="480">

## Updating and uninstalling

Updates appear in Mainsail under **Machine → Update Manager**; your `probe_dock_settings.cfg` is never overwritten.
If an update adds new settings, the Probe page offers to add them. `./uninstall.sh` removes everything the installer
added and can restore the sections it commented out.

## Troubleshooting

| Problem | Fix |
|---|---|
| *"Probe was not picked up"* although it is attached | pin logic inverted – toggle the `!` in `pin:` |
| *"retrying slowly"* shows up often | check the dock position with a slow `DOCK_TEST F=1500` |
| Probe scrapes the bed while meshing | `z_offset` wrong – run *Check z_offset*, apply, save |
| Probe page shows a 404 | use `/server/dockprobe/`, run `./install.sh` again |

More – macros, every setting, dock layouts, installer options, KlipperScreen buttons – in the
**[reference](docs/REFERENCE.md)**.

## Credits

[ZeroClick](https://github.com/zruncho3d/ZeroClick) by Zruncho (probe, dock and the sample macros the dock sequence is
based on) · [Klicky Probe](https://github.com/jlas1/Klicky-Probe) by jlas1 ·
[Voron V0](https://github.com/VoronDesign/Voron-0) by Voron Design ·
[Kirigami bed](https://github.com/christophmuellerorg/voron_0_kirigami_bed) by Christoph Müller ·
[Klipper](https://github.com/Klipper3d/klipper) · [Moonraker](https://github.com/Arksine/moonraker) ·
[Mainsail](https://github.com/mainsail-crew/mainsail) · [Vuetify](https://github.com/vuetifyjs/vuetify) ·
[Material Design Icons](https://pictogrammers.com/library/mdi/) ·
[KAMP](https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging).
Not affiliated with or endorsed by any of these projects.

## License

Copyright © 2026 [Screase3D](https://github.com/Screase3D) – **GPL-3.0-or-later**, see [LICENSE](LICENSE).
The dock sequence derives from the ZeroClick sample macros (GPL-3.0); the web UI mirrors a few Mainsail styles
(GPL-3.0) and embeds Material Design Icons (Apache-2.0). Details: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
