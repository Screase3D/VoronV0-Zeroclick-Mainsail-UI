# VoronV0-Zeroclick-Mainsail-UI (voron0-dockprobe)

*English version: [README.en.md](README.en.md)*

![Probe-Seite in Mainsail](docs/screenshot.png)

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

Erreichbar über den Menüpunkt **Probe** in Mainsail bzw. `http://<drucker>/server/dockprobe/` (alternativ `/probe/`).
Der Pfad unter `/server/` ist Absicht: Dort greift Mainsails Service-Worker nicht ein, der bei Zugriff über https sonst
jede andere Adresse auf Mainsail umleiten würde.

**Schneller Seitenwechsel:** Die Probe-Seite lädt Mainsail unsichtbar im Hintergrund. Ein Klick auf Dashboard, Konsole usw.
blendet es nur ein – ohne erneutes Initialisieren –, und „Probe“ in Mainsails Menü springt sofort zurück. Vor/Zurück im
Browser funktioniert. Abschaltbar über „Schneller Wechsel“ unten in der Seitenleiste oder mit `?shell=0`. Kostet im Browser
eine zweite Verbindung zu Moonraker, auf dem Drucker praktisch nichts.

**Aussehen:** Die Seite lädt zur Laufzeit die Stylesheets deiner installierten Mainsail-Version und nutzt dieselben
Bausteine (Panels, Buttons, Eingabefelder, Seitenleiste). Übernommen werden außerdem Mainsails Theme (z. B. „Voron Design“),
Primär- und Logofarbe, Hell-/Dunkelmodus, Icons-only-Navigation sowie alles aus `config/.theme/`
(`custom.css`, `sidebar-logo`, `sidebar-background`, `main-background`, `navi.json`).

**Panels**

- **Einrichtung:** Checkliste in der richtigen Reihenfolge (Erkennung → Dock-Test → Genauigkeit → Schrauben → Papiertest → z_offset → Mesh).
  Schritte haken sich nach erfolgreicher Messung selbst ab.
- **Probe:** Status, Andocken/Ablegen, Genauigkeitstest mit Diagramm und Bewertung, z_offset-Messung mit „Übernehmen“.
- **Dock-Test:** `DOCK_TEST CYCLES=n F=mm/min` – mehrfach andocken/ablegen, jeder Schritt wird über den Probe-Pin geprüft.
- **Bett & Schrauben:** Live-Ansicht mit Düse, Probe (im Dock oder am Toolhead mit aktueller Position), Dock-Halter
  außerhalb des Druckbereichs, Anfahrweg, Mesh-Bereich und Z0-Punkt; Schrauben mit Drehrichtung und Vergleich zur vorherigen Messung.
- **Bed Mesh:** Heatmap, Profile laden/speichern/löschen.
- **Kalibrierung:** `CALIBRATE_ALL` mit Temperatur, Soak, Schrauben und Mesh.
- **Einstellungen:** Offsets, Pin, Dock, Schraubenpositionen, Mesh, Sprache der Klipper-Meldungen. Positionen mit den
  Verfahr-Buttons anfahren und per Klick übernehmen. Mesh-Grenzen, Messpunkte und Referenzpunkt werden live berechnet;
  beim Speichern zeigt ein Dialog alle Änderungen, die alte Datei wird als `.bak` gesichert, dann startet Klipper neu.
- **Papiertest:** erscheint während `CALIBRATE_Z_ENDSTOP` als Dialog wie in Mainsail, auch per Tastatur (↑/↓, Shift, Bild↑/↓).
- **Konsole**

Voraussetzung ist, dass der Browser bei Moonraker als vertrauenswürdig gilt (`trusted_clients`) – wie bei Mainsail ohne Login.

## Sprache

- **Installer:** fragt zu Beginn nach der Sprache (oder `--lang de|en`).
- **Web-Oberfläche:** übernimmt die Sprache aus Mainsail bzw. dem Browser; umschalten über **DE/EN** in der Kopfzeile.
- **Klipper-Meldungen der Makros:** `variable_lang` in `probe_dock_settings.cfg` (`"de"` oder `"en"`), auch im UI unter *Einstellungen → Probe*.

## Update & Deinstallation

Der Installer trägt das Repo in `moonraker.conf` ein:

```ini
[update_manager voron0-dockprobe]
type: git_repo
channel: dev
path: ~/VoronV0-Zeroclick-Mainsail-UI
origin: https://github.com/Screase3D/VoronV0-Zeroclick-Mainsail-UI.git
primary_branch: main
managed_services: klipper
info_tags:
    desc=ZeroClick Dock-Probe (Voron V0.2)
```

Neue Versionen auf GitHub erscheinen dann in Mainsail unter *Maschine → Update-Manager* und zusätzlich als Hinweis auf
der Probe-Seite (mit „Jetzt aktualisieren“). Beim Update gilt:

- Makros (`probe_dock.cfg` ist ein Link ins Repo) und Web-Oberfläche sind sofort aktuell, Klipper wird automatisch neu gestartet.
- Deine Werte in `probe_dock_settings.cfg` bleiben unverändert. Bringt ein Update neue Einstellungsfelder mit, zeigt die
  Probe-Seite einen Hinweis – einmal unter *Einstellungen* speichern ergänzt sie.
- Voraussetzung: per `git clone` installiert und keine lokalen Änderungen im Repo-Ordner (sonst meldet Moonraker „dirty“).

Neue Werte per Script: `./install.sh --reconfigure`.

Änderungen an nginx oder am Menüeintrag (z. B. der Pfad `/server/dockprobe/`) übernimmt ein Update nicht automatisch –
dafür einmal `./install.sh` ausführen und die Frage nach neuen Einstellungen mit Enter (Nein) beantworten.

```bash
./uninstall.sh
```

entfernt Includes, Symlink, nginx-Eintrag, Menüpunkt und Update-Manager und stellt auskommentierte Sections auf Wunsch wieder her.

## Sicherheit

- Erste Dock-Fahrten mit reduzierter Geschwindigkeit testen (`--reconfigure`, z. B. 1500 mm/min) und Hand am Not-Aus.
- `horizontal_move_z` muss deutlich über dem Überstand der Probe-Spitze liegen – der Installer setzt `z_offset + 4`, mindestens 10.

## Lizenz

MIT
