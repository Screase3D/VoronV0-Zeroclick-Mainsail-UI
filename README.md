# VoronV0-Zeroclick-Mainsail-UI (voron0-dockprobe)

*English version: [README.en.md](README.en.md)*

Dock-Probe-Kit für den **Voron V0.2** mit Z-Endstop unten und einer magnetisch angedockten Probe (z. B. ZeroClick).
Ein Script analysiert deine Klipper-Config, rechnet Mesh- und Schraubenpositionen aus den Probe-Offsets aus und richtet alles ein:

- Makros für Andocken/Ablegen mit Prüfung über den Probe-Pin
- automatisches Probe-Handling bei `BED_MESH_CALIBRATE`, `SCREWS_TILT_CALCULATE`, `PROBE_ACCURACY`
- `CALIBRATE_ALL`: Home, Aufheizen, Schrauben-Check, Mesh in einem Durchgang
- `CALIBRATE_Z_ENDSTOP` (Papiertest) und `MEASURE_PROBE_OFFSET`
- Kalibrier-Oberfläche als eigener Menüpunkt **„Probe“** in der Mainsail-Seitenleiste
- Updates über den Mainsail-Update-Manager

> **Prinzip:** Z=0 kommt weiterhin vom Z-Endstop. Die Probe misst nur relativ (Mesh, Schrauben).
> Über `zero_reference_position` wird das Mesh am Papiertest-Punkt auf 0 normiert.

## Voraussetzungen

- Klipper + Moonraker + Mainsail (KIAUH oder MainsailOS)
- Probe mit Dock links hinten; Andocken von rechts nach links, Lösen per Y-Bewegung
- Probe-Pin so eingestellt, dass `QUERY_PROBE` mit Probe **im Dock „TRIGGERED“** und **am Toolhead „open“** meldet
  (bei NC-Schaltern meist `^PIN` ohne `!`)

## Installation

```bash
cd ~
git clone https://github.com/Screase3D/VoronV0-Zeroclick-Mainsail-UI.git
cd VoronV0-Zeroclick-Mainsail-UI
./install.sh
```

Das Script

1. analysiert die Config (Includes, Verfahrbereich, Probe, Konflikte, KAMP, nginx, Moonraker),
2. fragt Pin, Offsets, Dock-Position und Schraubenpositionen ab (Vorschläge aus deiner bestehenden Config),
3. berechnet `mesh_min/max`, die Schrauben-Messpunkte, `horizontal_move_z` und den Referenzpunkt,
4. zeigt alle geplanten Änderungen und fragt nach,
5. sichert den Config-Ordner nach `~/dockprobe-backups/`,
6. installiert, bindet die Web-Oberfläche ein und startet Klipper neu.

Nützliche Optionen:

| Option | Wirkung |
|---|---|
| `--analyze` | nur Analyse, ändert nichts |
| `--dry-run` | zeigt alle Schritte, ändert nichts |
| `--reconfigure` | Werte neu abfragen, `probe_dock_settings.cfg` neu erzeugen |
| `--no-web` | ohne Web-Oberfläche |
| `--no-restart` | Klipper nicht neu starten |
| `--yes` | alle Vorschläge übernehmen |
| `--lang de\|en` | Sprache des Installers und der Klipper-Meldungen |

### Was geändert wird

| Datei | Änderung |
|---|---|
| `probe_dock.cfg` | Symlink auf `klipper/probe_dock.cfg` im Repo (Makro-Logik, kommt mit Updates) |
| `probe_dock_settings.cfg` | deine Werte, wird bei Updates **nicht** überschrieben |
| `printer.cfg` | zwei `[include …]`-Zeilen |
| bestehende `[probe]`, `[bed_mesh]`, `[screws_tilt_adjust]`, Dock-/Mesh-Makros | mit `#dockprobe# ` auskommentiert |
| `KAMP_Settings.cfg` | `Adaptive_Meshing.cfg` deaktiviert (Klipper kann `ADAPTIVE=1` selbst) |
| `.theme/navi.json` | Menüeintrag „Probe“ |
| nginx-Site von Mainsail | `include /etc/nginx/snippets/dockprobe.conf;` |
| `moonraker.conf` | `[update_manager voron0-dockprobe]` |

Eine vorhandene Einzeldatei `probe_dock.cfg` wird zu `probe_dock.cfg.old`, ihre Werte werden übernommen.
Steht `z_offset` im SAVE_CONFIG-Block, bleibt er dort (sonst würde jedes `SAVE_CONFIG` fehlschlagen).

## Erste Kalibrierung

In Mainsail unter **Probe** oder in der Konsole:

1. `PROBE_STATUS` – Probe im Dock muss erkannt werden
2. `CALIBRATE_Z_ENDSTOP` – Papiertest, `ACCEPT`, `SAVE_CONFIG`
3. `MEASURE_PROBE_OFFSET` – Ergebnis ≈ 0, sonst `z_offset` = alter Wert + gemeldetes z
4. `PROBE_ACCURACY SAMPLES=10` – Spanne < 0,01 mm ist sehr gut
5. `CALIBRATE_ALL BED=60 SOAK=10` – Schrauben prüfen, Mesh messen

Nach jedem Drehen an den Bettschrauben den Papiertest (Schritt 2) wiederholen.

> `PROBE_CALIBRATE` ist absichtlich gesperrt: Die Probe hängt mehrere mm unter der Düse und würde beim Papiertest ins Bett fahren.

## PRINT_START

```ini
  M190 S{target_bed}
  BED_MESH_CLEAR
  BED_MESH_CALIBRATE ADAPTIVE=1   # holt und bringt die Probe selbst
  DETACH_PROBE                    # Sicherheit, tut nichts, wenn sie im Dock ist
  M109 S{target_extruder}
```

`ADAPTIVE=1` braucht `[exclude_object]` und „Label objects“ im Slicer.

## Web-Oberfläche

Erreichbar über den Menüpunkt **Probe** in Mainsail bzw. `http://<drucker>/probe/`.
Die Seite übernimmt Mainsails Seitenleiste (inkl. eigener `navi.json`-Einträge), Druckernamen, Logo, Primärfarbe und Hell-/Dunkelmodus.

- Probe-Status, Andocken/Ablegen, Genauigkeit, z_offset-Messung mit „Übernehmen“
- Papiertest-Steuerung (erscheint automatisch während `CALIBRATE_Z_ENDSTOP`)
- Schraubenanzeige mit Drehrichtung, Mesh-Heatmap, Konsole
- **Einstellungen bearbeiten:** Offsets, Pin, Dock, Schraubenpositionen, Mesh. Positionen lassen sich anfahren und per Klick übernehmen.
  Mesh-Grenzen, Schrauben-Messpunkte und Referenzpunkt werden live neu berechnet. Beim Speichern zeigt ein Dialog alle Änderungen,
  die alte Datei wird als `.bak` gesichert, dann startet Klipper neu. Steht `z_offset` im SAVE_CONFIG-Block, wird er dort geändert.
Voraussetzung ist, dass der Browser bei Moonraker als vertrauenswürdig gilt (`trusted_clients`) – wie bei Mainsail ohne Login.

## Sprache

- **Installer:** fragt zu Beginn nach der Sprache (oder `--lang de|en`).
- **Web-Oberfläche:** übernimmt die Sprache aus Mainsail bzw. dem Browser; umschalten über **DE/EN** in der Kopfzeile.
- **Klipper-Meldungen der Makros:** `variable_lang` in `probe_dock_settings.cfg` (`"de"` oder `"en"`), auch im UI unter *Einstellungen → Probe*.

## Update & Deinstallation

Updates erscheinen in Mainsail unter *Maschine → Update-Manager*.
Neue Werte (z. B. andere Offsets): `./install.sh --reconfigure`.

```bash
./uninstall.sh
```

entfernt Includes, Symlink, nginx-Eintrag, Menüpunkt und Update-Manager und stellt auskommentierte Sections auf Wunsch wieder her.

## Sicherheit

- Erste Dock-Fahrten mit reduzierter Geschwindigkeit testen (`--reconfigure`, z. B. 1500 mm/min) und Hand am Not-Aus.
- `horizontal_move_z` muss deutlich über dem Überstand der Probe-Spitze liegen – der Installer setzt `z_offset + 4`, mindestens 10.

## Lizenz

MIT
