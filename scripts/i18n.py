"""Translation of the installer output (German is the source text).

tr() replaces known German phrases with English when LANG == "en".
Variable parts (paths, numbers, names) stay unchanged.

SPDX-License-Identifier: GPL-3.0-or-later
"""
import os
import re

LANG = "de"

# (German, English) – applied sorted by length, longest first
PHRASES = [
    # headings
    ("voron0-dockprobe – Dock-Probe-Kit für Voron V0.2", "voron0-dockprobe – dock probe kit for Voron V0.2"),
    ("Umgebung", "Environment"), ("Drucker", "Printer"), ("Installationsstand", "Installation state"),
    ("Konflikte", "Conflicts"), ("Einstellungen", "Settings"), ("Berechnet", "Calculated"),
    ("Geplante Änderungen", "Planned changes"), ("Deinstallation", "Uninstall"), ("Fertig", "Done"),
    # analysis
    ("Config-Ordner:  ", "Config folder:  "), ("nicht gefunden", "not found"), ("Dienst ", "Service "),
    ("Verfahrbereich X", "Travel range X"),
    ("Z-Endstop unten (Homing nach Z-max) – Z=0 kommt vom Endstop", "Z endstop at the bottom (homing to Z max) – Z=0 comes from the endstop"),
    ("Z-Endstop scheint oben zu sitzen – das Paket ist für den V0.2-Endstop unten ausgelegt",
     "Z endstop seems to be at the top – this kit is designed for the V0.2 bottom endstop"),
    ("Klipper unterstützt BED_MESH_CALIBRATE ADAPTIVE=1", "Klipper supports BED_MESH_CALIBRATE ADAPTIVE=1"),
    ("Klipper zu alt für ADAPTIVE=1 – Klipper aktualisieren", "Klipper too old for ADAPTIVE=1 – update Klipper"),
    ("fehlt (nötig für ADAPTIVE=1)", "missing (required for ADAPTIVE=1)"),
    ("Keine [probe]-Section gefunden", "No [probe] section found"),
    ("z_offset im SAVE_CONFIG-Block:", "z_offset in SAVE_CONFIG block:"),
    ("Symlink aufs Repo", "symlink to the repo"),
    ("alte Einzeldatei (wird ersetzt, Werte werden übernommen)", "old single file (will be replaced, values are kept)"),
    ("Includes in printer.cfg: ", "Includes in printer.cfg: "), ("unvollständig", "incomplete"), ("vollständig", "complete"),
    ("Web-Oberfläche in nginx: ", "Web UI in nginx: "), ("eingebunden", "included"),
    ("Menüeintrag in Mainsail: ", "Menu entry in Mainsail: "), ("eingetragen", "registered"),
    ("KAMP Adaptive_Meshing eingebunden in", "KAMP Adaptive_Meshing included in"),
    ("Include nicht gefunden:", "Include not found:"), ("Datei nicht lesbar:", "File not readable:"),
    # questions
    ("Sprache / Language", "Language / Sprache"),
    ("Enter übernimmt den Vorschlag in [Klammern]. Dezimal mit Punkt oder Komma.",
     "Enter accepts the suggestion in [brackets]. Decimals with point or comma."),
    ("Probe-Pin (z. B. ^PG15, NC-Schalter meist ohne !)", "Probe pin (e.g. ^PG15, NC switches usually without !)"),
    ("Probe x_offset (links der Düse = negativ)", "Probe x_offset (left of nozzle = negative)"),
    ("Probe y_offset (hinter der Düse = positiv)", "Probe y_offset (behind nozzle = positive)"),
    ("(aus SAVE_CONFIG-Block, bleibt dort)", "(from SAVE_CONFIG block, stays there)"),
    ("Probe z_offset (Auslösehöhe, per MEASURE_PROBE_OFFSET)", "Probe z_offset (trigger height, via MEASURE_PROBE_OFFSET)"),
    ("Probe-Geschwindigkeit mm/s", "Probe speed mm/s"),
    ("Dock (Düsenposition, wenn die Probe im Dock sitzt)", "Dock (nozzle position while the probe sits in the dock)"),
    ("Dock-Wege (Wegpunkte relativ zur Dock-Position):", "Dock paths (waypoints relative to the dock position):"),
    ("Dock hinten links: von rechts einfahren, zum Lösen nach vorne", "dock at the rear left: enter from the right, release towards the front"),
    ("Dock hinten rechts: von links einfahren, zum Lösen nach vorne", "dock at the rear right: enter from the left, release towards the front"),
    ("wie im ZeroClick-README-Beispiel (Center Dock)", "as in the ZeroClick README sample (center dock)"),
    ("eigene Wegpunkte", "custom waypoints"), ("Dock-Layout (1-4)", "Dock layout (1-4)"),
    ("Wegpunkte Andocken (dx,dy; dx,dy; ...)", "Attach waypoints (dx,dy; dx,dy; ...)"),
    ("Wegpunkte Ablegen (dx,dy; dx,dy; ...)", "Detach waypoints (dx,dy; dx,dy; ...)"),
    ("Ungültige Wegpunkte – Format: dx,dy; dx,dy (mindestens zwei Punkte, einer davon 0,0)",
     "Invalid waypoints – format: dx,dy; dx,dy (at least two points, one of them 0,0)"),
    ("Anfahrweg seitlich vom Dock (mm)", "Approach distance beside the dock (mm)"),
    ("Y-Abstand der Anfahrbahn / Löseweg (mm)", "Y distance of the approach lane / release travel (mm)"),
    ("Wiederholversuche beim An-/Ablegen", "Retries when attaching/detaching"),
    ("Dock X (Düsenposition beim Andocken)", "Dock X (nozzle position when attaching)"),
    ("Z-Höhe für Dock-Fahrten", "Z height for dock moves"), ("Verfahrgeschwindigkeit mm/min", "Travel speed mm/min"),
    ("Dock-Geschwindigkeit mm/min", "Dock speed mm/min"),
    ("Andock-Status per Probe-Pin prüfen", "Verify dock state via probe pin"),
    ("Bettschrauben: Düsenposition, wenn die Düse genau über der Schraube steht",
     "Bed screws: nozzle position when the nozzle is exactly above the screw"),
    ("Anzahl Schrauben", "Number of screws"), ("Gewinde (CW-M3 / CCW-M3)", "Thread (CW-M3 / CCW-M3)"),
    ("Randabstand fürs Mesh (mm)", "Mesh edge margin (mm)"),
    ("Sprache der Klipper-Meldungen (de/en)", "Language of Klipper messages (de/en)"),
    ("Wert erforderlich.", "Value required."), ("Bitte eine Zahl eingeben.", "Please enter a number."),
    ("– interaktiv ausführen oder Wert in der Config setzen.", "– run interactively or set the value in the config."),
    ("Kein Wert für", "No value for"),
    # calculation
    ("Mesh-Bereich ist leer – Offsets oder Randabstand prüfen.", "Mesh area is empty – check offsets or edge margin."),
    ("Mesh (Probe-Koordinaten):", "Mesh (probe coordinates):"), (" bis ", " to "),
    ("Düse fährt dabei X", "Nozzle travels X"),
    ("Referenz-/Parkposition (zero_reference, Papiertest):", "Reference/park position (zero_reference, paper test):"),
    ("Probe misst", "probe measures"), ("mm neben der Schraube", "mm away from the screw"),
    ("Probe direkt über der Schraube", "probe directly above the screw"),
    ("Probe {d} mm neben der Schraube", "probe {d} mm away from the screw"),
    ("ist knapp über der Probe-Spitze", "is barely above the probe tip"), ("Kollisionsgefahr", "risk of collision"),
    ("Dock-Höhe", "Dock height"),
    ("liegt außerhalb des Verfahrbereichs", "is outside the travel range"),
    ("Wegpunkt ", "Waypoint "), ("(Andocken)", "(attach)"), ("(Ablegen)", "(detach)"),
    ("Wegpunkte Andocken: ", "Attach waypoints: "), ("Wegpunkte Ablegen:  ", "Detach waypoints: "),
    (": Düse ", ": nozzle "), ("Schraube ", "Screw "),
    # plan
    ("Backup des Config-Ordners nach ~/dockprobe-backups/", "Back up the config folder to ~/dockprobe-backups/"),
    ("umbenennen in", "rename to"), ("als Symlink aufs Repo anlegen", "create as symlink to the repo"),
    ("neu erzeugen", "regenerate"), ("anlegen", "create"), ("auskommentieren", "comment out"),
    ("liegt außerhalb des Config-Ordners, bitte manuell entfernen", "is outside the config folder, please remove manually"),
    ("KAMP Adaptive_Meshing-Include in", "KAMP Adaptive_Meshing include in"),
    ("Includes in printer.cfg ergänzen", "Add includes to printer.cfg"),
    ("Web-Oberfläche in nginx einbinden und Menüeintrag in Mainsail anlegen", "Add the web UI to nginx and create a menu entry in Mainsail"),
    ("Update-Manager in moonraker.conf eintragen (falls per git clone installiert)", "Register update manager in moonraker.conf (if installed via git clone)"),
    ("Klipper neu starten", "Restart Klipper"), ("Fortfahren?", "Continue?"), ("Abgebrochen.", "Aborted."),
    ("PROBE_GUARD in PRINT_START einfügen (Schutz vor Druck mit angedockter Probe)?",
     "Insert PROBE_GUARD into PRINT_START (protection against printing with the probe attached)?"),
    ("PRINT_START liegt außerhalb des Config-Ordners – PROBE_GUARD bitte manuell einfügen",
     "PRINT_START is outside the config folder – please add PROBE_GUARD manually"),
    ("Probe-Menü in KlipperScreen einbinden (Mehr → Probe)?", "Add the probe menu to KlipperScreen (More → Probe)?"),
    ("PROBE_GUARD in PRINT_START einfügen", "Insert PROBE_GUARD into PRINT_START"),
    ("KlipperScreen-Menü einbinden und KlipperScreen neu starten", "Add the KlipperScreen menu and restart KlipperScreen"),
    ("PROBE_GUARD in PRINT_START eingefügt", "PROBE_GUARD inserted into PRINT_START"),
    ("KlipperScreen neu gestartet", "KlipperScreen restarted"),
    ("KlipperScreen bitte neu starten, damit die Änderung wirkt", "Please restart KlipperScreen to apply the change"),
    ("KlipperScreen-Menü eingebunden (Mehr → Probe)", "KlipperScreen menu added (More → Probe)"),
    ("KlipperScreen-Menü entfernt", "KlipperScreen menu removed"),
    ("KlipperScreen-Menü auf die Sprache der Klipper-Meldungen umgestellt (wirkt nach Neustart von KlipperScreen)",
     "KlipperScreen menu switched to the language of the Klipper messages (applies after restarting KlipperScreen)"),
    ("PROBE_GUARD vorhanden", "PROBE_GUARD present"), ("PROBE_GUARD fehlt", "PROBE_GUARD missing"),
    ("KlipperScreen-Menü: ", "KlipperScreen menu: "),
    ("ältere Einstellungsdatei – neue Optionen (Dock-Wege, Wiederholversuche) mit --reconfigure oder durch Speichern in der Web-Oberfläche ergänzen",
     "older settings file – add the new options (dock paths, retries) with --reconfigure or by saving in the web UI"),
    ("existiert – Werte neu abfragen und Datei neu erzeugen?", "exists – ask for values again and regenerate the file?"),
    # execution
    ("gesichert als", "saved as"), ("verlinkt", "linked"), ("geschrieben", "written"), ("auskommentiert", "commented out"),
    ("bitte manuell entfernen", "please remove manually"), ("deaktiviert", "disabled"),
    ("Includes in printer.cfg eingetragen", "Includes added to printer.cfg"),
    ("Includes aus printer.cfg entfernt", "Includes removed from printer.cfg"),
    ("Auskommentierte Zeilen in", "Restored commented lines in"), ("wiederhergestellt", ""),
    ("nginx-Site von Mainsail nicht gefunden – Web-Oberfläche übersprungen", "Mainsail nginx site not found – web UI skipped"),
    ("Kein server-Block in", "No server block in"), ("– bitte", "– please add"), ("manuell eintragen", "manually"),
    ("nginx-Binary nicht gefunden – Test und Reload übersprungen", "nginx binary not found – test and reload skipped"),
    ("nginx-Test fehlgeschlagen, Änderung wird zurückgenommen:", "nginx test failed, change reverted:"),
    ("Web-Oberfläche in nginx eingebunden (/server/dockprobe/ und /probe/)", "Web UI added to nginx (/server/dockprobe/ and /probe/)"),
    ("ist für nginx nicht betretbar – ggf.", "is not accessible for nginx – maybe run"),
    ("nginx-Eintrag entfernt", "nginx entry removed"),
    ("ist kein gültiges JSON-Array – Menüeintrag übersprungen", "is not a valid JSON array – menu entry skipped"),
    ("Menüeintrag 'Probe' in Mainsail angelegt (Browser neu laden)", "Menu entry 'Probe' created in Mainsail (reload the browser)"),
    ("Menüeintrag entfernt", "Menu entry removed"),
    ("moonraker.conf nicht gefunden – Update-Manager übersprungen", "moonraker.conf not found – update manager skipped"),
    ("Repo hat keinen git-origin (nicht per git clone installiert) – Update-Manager übersprungen",
     "Repo has no git origin (not installed via git clone) – update manager skipped"),
    ("Update-Manager in moonraker.conf eingetragen", "Update manager registered in moonraker.conf"),
    ("Update-Manager-Eintrag entfernt", "Update manager entry removed"),
    ("Es läuft ein Druck – Neustart übersprungen. Danach RESTART ausführen.", "A print is running – restart skipped. Run RESTART afterwards."),
    ("Moonraker nicht erreichbar – bitte Klipper manuell neu starten (RESTART)", "Moonraker not reachable – please restart Klipper manually (RESTART)"),
    ("Moonraker wird neu gestartet", "Restarting Moonraker"),
    ("Moonraker-Neustart fehlgeschlagen – bitte manuell neu starten", "Moonraker restart failed – please restart manually"),
    ("Klipper-Neustart über Moonraker fehlgeschlagen – bitte RESTART ausführen", "Klipper restart via Moonraker failed – please run RESTART"),
    ("Warte auf Klipper ...", "Waiting for Klipper ..."), ("Klipper ist bereit", "Klipper is ready"),
    ("Klipper meldet einen Fehler:", "Klipper reports an error:"),
    ("Klipper ist nach 30 s noch nicht bereit – Status in Mainsail prüfen", "Klipper is not ready after 30 s – check the status in Mainsail"),
    ("Nächste Schritte (in Mainsail unter 'Probe' oder in der Konsole):", "Next steps (in Mainsail under 'Probe' or in the console):"),
    ("– Probe im Dock muss TRIGGERED melden", "– docked probe must report TRIGGERED"),
    ("– Papiertest, ACCEPT, SAVE_CONFIG", "– paper test, ACCEPT, SAVE_CONFIG"),
    ("– Ergebnis ~0, sonst z_offset anpassen", "– result ~0, otherwise adjust z_offset"),
    ("Bei Problemen: Backup liegt in", "If something goes wrong: backup is in"),
    ("Deinstallation mit ./uninstall.sh", "uninstall with ./uninstall.sh"),
    ("voron0-dockprobe entfernen?", "Remove voron0-dockprobe?"), ("-Symlink entfernt", " symlink removed"),
    ("löschen? (Nein = behalten für spätere Neuinstallation)", "delete? (No = keep for a later reinstall)"),
    ("gelöscht", "deleted"), ("Vom Installer auskommentierte Sections wiederherstellen?", "Restore sections commented out by the installer?"),
    ("printer.cfg nicht gefunden – mit --config-dir angeben.", "printer.cfg not found – specify it with --config-dir."),
    ("Befehl fehlgeschlagen:", "Command failed:"),
    ("Installation unvollständig – Backup liegt in ~/dockprobe-backups/", "Installation incomplete – backup is in ~/dockprobe-backups/"),
    ("[dry-run] schreibe", "[dry-run] write"), ("[dry-run] entferne", "[dry-run] remove"),
    ("[dry-run] Backup nach", "[dry-run] backup to"), ("[dry-run] Klipper-Neustart", "[dry-run] Klipper restart"),
    ("alte ", "old "),
    # comments in probe_dock_settings.cfg
    ("voron0-dockprobe – DEINE Einstellungen", "voron0-dockprobe – YOUR settings"),
    ("Erzeugt von install.sh am", "Generated by install.sh on"),
    ("Wird bei Updates NICHT überschrieben. Werte neu berechnen lassen:", "NOT overwritten by updates. Recalculate values with:"),
    ('Die Zeilen mit "#@" merkt sich der Installer für --reconfigure.', 'Lines starting with "#@" are remembered by the installer for --reconfigure.'),
    ("Einstellungen für Dock, Wege und Ablauf (voron0-dockprobe)", "Settings for dock, moves and sequence (voron0-dockprobe)"),
    ("verify: Andock-Status per QUERY_PROBE prüfen", "verify: check dock state via QUERY_PROBE"),
    ("Probe im Dock -> TRIGGERED, Probe am Toolhead -> open", "probe docked -> TRIGGERED, probe on toolhead -> open"),
    ("enthält nur Einstellungen", "only holds settings"),
    ("Andock-Wege: Wegpunkte [dx, dy] relativ zu dock_x/dock_y (Vorlage: dock_layout)",
     "dock paths: waypoints [dx, dy] relative to dock_x/dock_y (preset: dock_layout)"),
    ("retries: Wiederholversuche, wenn die Pin-Prüfung nach dem Andocken/Ablegen fehlschlägt",
     "retries: extra attempts when the pin check after attaching/detaching fails"),
    ("Sprache der Klipper-Meldungen: de / en", "language of Klipper messages: de / en"),
    ("] vorhanden", "] present"), ("Update-Manager: ", "Update manager: "),
    ("Düsenpositionen, an denen die Probe über (bzw. möglichst nah an) der Schraube misst",
     "nozzle positions where the probe measures above (or as close as possible to) the screw"),
    ("(steht im SAVE_CONFIG-Block von printer.cfg)", "(stored in the SAVE_CONFIG block of printer.cfg)"),
]
PHRASES.sort(key=lambda p: -len(p[0]))

# sentences with a different word order in English
RULES = [
    (r"^alte (\S+) umbenennen in (\S+)$", r"Rename old \1 to \2"),
    (r"^(\S+) als Symlink aufs Repo anlegen$", r"Create \1 as symlink to the repo"),
    (r"^(\S+) neu erzeugen$", r"Regenerate \1"),
    (r"^(\S+) anlegen$", r"Create \1"),
    (r"^KAMP Adaptive_Meshing-Include in (\S+) auskommentieren$", r"Comment out KAMP Adaptive_Meshing include in \1"),
    (r"^\[(.+)\] in (\S+) auskommentieren$", r"Comment out [\1] in \2"),
    (r"\(Probe (\d+) mm neben der Schraube\)", r"(probe \1 mm away from the screw)"),
    (r"^(\S+): PROBE_GUARD nach „(.*)“ einfügen \((.*)\)$", r"\1: insert PROBE_GUARD after “\2” (\3)"),
    (r"^PROBE_GUARD aus (\S+) entfernt$", r"PROBE_GUARD removed from \1"),
]

# single words only replaced as whole values at the end of a line
WORDS = {"fehlt": "missing", "vorhanden": "present", "nein": "no", "keine": "none"}


def tr(text):
    if LANG != "en" or not isinstance(text, str):
        return text
    for rx, rep in RULES:
        text = re.sub(rx, rep, text)
    for de, en in PHRASES:
        if de in text:
            text = text.replace(de, en)
    text = re.sub(r"(?<=: )(fehlt|vorhanden|nein)$|^(keine)$",
                  lambda m: WORDS[m.group(1) or m.group(2)], text)
    return text


def default_lang():
    for var in ("DOCKPROBE_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v:
            return "de" if v.lower().startswith("de") else "en"
    return "en"
