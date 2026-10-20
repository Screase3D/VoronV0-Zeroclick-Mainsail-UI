#!/usr/bin/env python3
"""voron0-dockprobe – Analyse, Installation und Deinstallation.

Wird über ./install.sh aufgerufen. Benötigt nur die Python-Standardbibliothek.
"""
import argparse
import datetime
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from string import Template

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n  # noqa: E402
from i18n import tr  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
LOGIC_SRC = REPO_DIR / "klipper" / "probe_dock.cfg"
SETTINGS_TPL = REPO_DIR / "klipper" / "probe_dock_settings.cfg.tpl"
WEB_DIR = REPO_DIR / "web"

LOGIC_NAME = "probe_dock.cfg"
SETTINGS_NAME = "probe_dock_settings.cfg"
OWN_FILES = {LOGIC_NAME, SETTINGS_NAME}
MARK = "#dockprobe# "
NGINX_SNIPPET = os.environ.get("DOCKPROBE_NGINX_SNIPPET", "/etc/nginx/snippets/dockprobe.conf")
NGINX_TAG = "# dockprobe"
NAVI_HREF = "/probe/"
UM_SECTION = "update_manager voron0-dockprobe"
MOONRAKER = os.environ.get("DOCKPROBE_MOONRAKER", "http://127.0.0.1:7125")

CONFLICT_SECTIONS = {"probe", "bed_mesh", "screws_tilt_adjust"}
CONFLICT_MACROS = {
    "attach_probe", "detach_probe", "dock_probe", "bed_mesh_calibrate",
    "screws_tilt_calculate", "probe_calibrate", "probe_accuracy",
    "measure_probe_offset", "calibrate_z_endstop", "calibrate_all",
    "probe_status", "_probe_vars", "_probe_state",
}

# Düsenpositionen über den Schrauben (Voron V0.2 mit Kirigami, gemessen)
DEFAULT_SCREWS = [
    (58.5, 4.0, "vorne mittig"),
    (4.5, 112.0, "hinten links"),
    (113.5, 112.0, "hinten rechts"),
]

NAVI_ICON = ("M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8M3.05,13H1V11H3.05"
             "C3.5,6.83 6.83,3.5 11,3.05V1H13V3.05C17.17,3.5 20.5,6.83 20.95,11H23V13H20.95"
             "C20.5,17.17 17.17,20.5 13,20.95V23H11V20.95C6.83,20.5 3.5,17.17 3.05,13"
             "M12,5A7,7 0 0,0 5,12A7,7 0 0,0 12,19A7,7 0 0,0 19,12A7,7 0 0,0 12,5Z")

SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*(?:[#;].*)?$")
OPTION_RE = re.compile(r"^([A-Za-z0-9_]+)\s*[:=]\s*(.*?)\s*$")


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------
USE_COLOR = sys.stdout.isatty()


def c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def head(text):
    print("\n" + c("1;36", f"== {tr(text)} =="))


def ok(text):
    print("  " + c("32", "✔ ") + tr(text))


def warn(text):
    print("  " + c("33", "! ") + tr(text))


def err(text):
    print("  " + c("31", "✘ ") + tr(text))


def info(text):
    print("  " + tr(text))


def fmt(v):
    """Zahl ohne überflüssige Nachkommastellen."""
    if isinstance(v, bool):
        return str(v)
    v = round(float(v), 3)
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def num(s):
    return float(str(s).strip().replace(",", "."))


# ---------------------------------------------------------------------------
# Klipper-Config lesen
# ---------------------------------------------------------------------------
class Section:
    def __init__(self, name, file, start):
        self.name = name
        self.file = file
        self.start = start
        self.end = None
        self.options = {}

    @property
    def lname(self):
        return self.name.lower()

    @property
    def basename(self):
        return os.path.basename(self.file)


def strip_comment(v):
    return re.split(r"\s[#;]", v, maxsplit=1)[0].strip()


def parse_config(printer_cfg):
    ctx = {"sections": [], "autosave": {}, "includes": [], "files": [],
           "seen": set(), "warnings": [], "meta": {}}
    _parse_file(str(printer_cfg), ctx, main=True)
    return ctx


def _parse_file(path, ctx, depth=0, main=False):
    real = os.path.realpath(path)
    if real in ctx["seen"] or depth > 12:
        return
    ctx["seen"].add(real)
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        ctx["warnings"].append(f"Datei nicht lesbar: {path} ({e})")
        return
    ctx["files"].append(path)
    cur = None
    as_cur = None
    in_autosave = False
    for i, line in enumerate(lines):
        if line.startswith("#*#"):
            if not in_autosave:
                in_autosave = True
                if cur:
                    cur.end = i
                    cur = None
            if main:
                body = line[3:].strip()
                m = SECTION_RE.match(body)
                if m:
                    as_cur = m.group(1).strip().lower()
                    ctx["autosave"].setdefault(as_cur, {})
                elif as_cur:
                    om = OPTION_RE.match(body)
                    if om:
                        ctx["autosave"][as_cur][om.group(1).lower()] = om.group(2)
            continue
        if in_autosave:
            continue
        if line.startswith("#@") and os.path.basename(path) == SETTINGS_NAME:
            parts = line[2:].split(None, 1)
            if parts:
                ctx["meta"].setdefault(parts[0], []).append(parts[1] if len(parts) > 1 else "")
            continue
        m = SECTION_RE.match(line)
        if m:
            if cur:
                cur.end = i
                cur = None
            name = m.group(1).strip()
            if name.lower().startswith("include "):
                pattern = name[8:].strip()
                full = os.path.join(os.path.dirname(path), pattern)
                matches = sorted(glob.glob(full))
                if not matches and not any(ch in pattern for ch in "*?["):
                    ctx["warnings"].append(f"Include nicht gefunden: {pattern} (in {path})")
                ctx["includes"].append({"file": path, "line": i, "pattern": pattern, "matches": matches})
                for mf in matches:
                    _parse_file(mf, ctx, depth + 1)
                continue
            cur = Section(name, path, i)
            ctx["sections"].append(cur)
            continue
        if cur and line and not line[0].isspace():
            om = OPTION_RE.match(line)
            if om:
                cur.options[om.group(1).lower()] = strip_comment(om.group(2))
    if cur:
        cur.end = len(lines)


def merged(ctx, name, only=None):
    """Optionen einer Section über alle Vorkommen (spätere gewinnen)."""
    out = {}
    for s in ctx["sections"]:
        if s.lname == name.lower() and (only is None or only(s)):
            out.update(s.options)
    return out


def has_section(ctx, name):
    return any(s.lname == name.lower() for s in ctx["sections"])


# ---------------------------------------------------------------------------
# Umgebung erkennen
# ---------------------------------------------------------------------------
def detect(args):
    home = Path.home()
    env = {"home": home}
    if args.config_dir:
        cfg = Path(args.config_dir).expanduser().resolve()
    else:
        cfg = next((p for p in (home / "printer_data/config", home / "klipper_config")
                    if (p / "printer.cfg").exists()), None)
    env["cfg"] = cfg
    env["printer_cfg"] = cfg / "printer.cfg" if cfg else None
    env["moonraker_conf"] = cfg / "moonraker.conf" if cfg and (cfg / "moonraker.conf").exists() else None
    env["klipper_dir"] = home / "klipper" if (home / "klipper").is_dir() else None
    env["mainsail_dir"] = home / "mainsail" if (home / "mainsail").is_dir() else None
    if args.nginx_site:
        env["nginx_site"] = Path(args.nginx_site)
    else:
        site = None
        for p in ("/etc/nginx/sites-available/mainsail", "/etc/nginx/sites-enabled/mainsail"):
            if os.path.exists(p):
                site = Path(os.path.realpath(p))
                break
        env["nginx_site"] = site
    env["nginx_bin"] = shutil.which("nginx") or ("/usr/sbin/nginx" if os.path.exists("/usr/sbin/nginx") else None)
    env["systemctl"] = shutil.which("systemctl")
    return env


def service_state(env, name):
    if not env["systemctl"]:
        return "?"
    r = subprocess.run([env["systemctl"], "is-active", name], capture_output=True, text=True)
    return r.stdout.strip() or "?"


def klipper_version(env):
    if not env["klipper_dir"]:
        return None
    r = subprocess.run(["git", "-C", str(env["klipper_dir"]), "describe", "--always", "--tags"],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def klipper_has_adaptive(env):
    if not env["klipper_dir"]:
        return None
    p = env["klipper_dir"] / "klippy/extras/bed_mesh.py"
    try:
        return "ADAPTIVE" in p.read_text(errors="replace")
    except OSError:
        return None


def git_origin():
    r = subprocess.run(["git", "-C", str(REPO_DIR), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def git_branch():
    r = subprocess.run(["git", "-C", str(REPO_DIR), "rev-parse", "--abbrev-ref", "HEAD"],
                       capture_output=True, text=True)
    b = r.stdout.strip()
    return b if r.returncode == 0 and b and b != "HEAD" else "main"


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------
def analyze(env):
    cfg = env["cfg"]
    ctx = parse_config(env["printer_cfg"])
    A = {"ctx": ctx}

    logic_path = cfg / LOGIC_NAME
    A["logic_is_link"] = logic_path.is_symlink()
    A["legacy_logic"] = logic_path.exists() and not logic_path.is_symlink()
    A["settings_exists"] = (cfg / SETTINGS_NAME).exists()

    own = lambda s: s.basename in OWN_FILES  # noqa: E731

    # Konflikte: Sections/Makros in fremden Dateien
    conflicts = []
    for s in ctx["sections"]:
        if own(s):
            continue
        ln = s.lname
        if ln in CONFLICT_SECTIONS or (ln.startswith("gcode_macro ") and ln[12:].strip() in CONFLICT_MACROS):
            conflicts.append(s)
    # KAMP Adaptive Meshing: wird über die Include-Zeile deaktiviert, nicht in der KAMP-Datei
    A["kamp_adaptive"] = [inc for inc in ctx["includes"] if "adaptive_meshing" in inc["pattern"].lower()]
    kamp_files = {os.path.realpath(f) for inc in A["kamp_adaptive"] for f in inc["matches"]}
    A["conflicts"] = [s for s in conflicts if os.path.realpath(s.file) not in kamp_files]

    # Includes unseres Pakets in printer.cfg
    pc_lines = env["printer_cfg"].read_text(errors="replace").splitlines()
    A["has_inc_logic"] = any(re.match(rf"^\[include\s+{re.escape(LOGIC_NAME)}\s*\]", l) for l in pc_lines)
    A["has_inc_settings"] = any(re.match(rf"^\[include\s+{re.escape(SETTINGS_NAME)}\s*\]", l) for l in pc_lines)

    # Mechanik
    sx, sy, sz = merged(ctx, "stepper_x"), merged(ctx, "stepper_y"), merged(ctx, "stepper_z")

    def rng(st, default_max):
        try:
            lo = num(st.get("position_min", "0"))
        except ValueError:
            lo = 0.0
        try:
            hi = num(st.get("position_max", default_max))
        except ValueError:
            hi = float(default_max)
        return lo, hi

    A["x_range"] = rng(sx, 120)
    A["y_range"] = rng(sy, 120)
    try:
        z_end = num(sz.get("position_endstop", ctx["autosave"].get("stepper_z", {}).get("position_endstop", "nan")))
        z_max = num(sz.get("position_max", "nan"))
        A["z_endstop_max"] = not math.isnan(z_end) and not math.isnan(z_max) and z_end > z_max / 2
    except ValueError:
        A["z_endstop_max"] = None
    A["exclude_object"] = has_section(ctx, "exclude_object")

    # Probe-Werte (alle Quellen, eigene Dateien zuletzt = höchste Priorität)
    probe = merged(ctx, "probe")
    A["probe"] = probe
    A["autosave"] = ctx["autosave"]
    A["vars"] = merged(ctx, "gcode_macro _PROBE_VARS")
    A["bed_mesh"] = merged(ctx, "bed_mesh")
    A["screws_cfg"] = merged(ctx, "screws_tilt_adjust")
    A["meta"] = ctx["meta"]

    # Web / nginx / navi / update_manager
    site = env["nginx_site"]
    try:
        A["nginx_has_include"] = bool(site) and NGINX_SNIPPET in site.read_text(errors="replace")
    except OSError:
        A["nginx_has_include"] = None
    navi = cfg / ".theme" / "navi.json"
    A["navi_has_entry"] = False
    if navi.exists():
        try:
            A["navi_has_entry"] = any(e.get("href") == NAVI_HREF for e in json.loads(navi.read_text()))
        except (ValueError, AttributeError):
            A["navi_has_entry"] = None
    mc = env["moonraker_conf"]
    A["um_present"] = bool(mc) and f"[{UM_SECTION}]" in mc.read_text(errors="replace")
    return A


def report(env, A):
    ctx = A["ctx"]
    head("Umgebung")
    info(f"Config-Ordner:   {env['cfg']}")
    info(f"Repo:            {REPO_DIR}")
    info(f"Klipper:         {env['klipper_dir'] or 'nicht gefunden'}"
         + (f"  ({klipper_version(env)})" if env['klipper_dir'] else ""))
    info(f"Mainsail:        {env['mainsail_dir'] or 'nicht gefunden'}")
    info(f"nginx-Site:      {env['nginx_site'] or 'nicht gefunden'}")
    info(f"moonraker.conf:  {env['moonraker_conf'] or 'nicht gefunden'}")
    for svc in ("klipper", "moonraker", "nginx"):
        st = service_state(env, svc)
        (ok if st == "active" else warn)(f"Dienst {svc}: {st}")

    head("Drucker")
    info(f"Verfahrbereich X {fmt(A['x_range'][0])}..{fmt(A['x_range'][1])}, "
         f"Y {fmt(A['y_range'][0])}..{fmt(A['y_range'][1])}")
    if A["z_endstop_max"] is True:
        ok("Z-Endstop unten (Homing nach Z-max) – Z=0 kommt vom Endstop")
    elif A["z_endstop_max"] is False:
        warn("Z-Endstop scheint oben zu sitzen – das Paket ist für den V0.2-Endstop unten ausgelegt")
    ad = klipper_has_adaptive(env)
    if ad is True:
        ok("Klipper unterstützt BED_MESH_CALIBRATE ADAPTIVE=1")
    elif ad is False:
        warn("Klipper zu alt für ADAPTIVE=1 – Klipper aktualisieren")
    (ok if A["exclude_object"] else warn)(
        "[exclude_object] " + ("vorhanden" if A["exclude_object"] else "fehlt (nötig für ADAPTIVE=1)"))

    head("Probe")
    p = A["probe"]
    if p:
        info(f"Pin: {p.get('pin', '-')}   Offsets: x={p.get('x_offset', '-')} y={p.get('y_offset', '-')} "
             f"z={p.get('z_offset', '-')}")
    else:
        warn("Keine [probe]-Section gefunden")
    if "z_offset" in A["autosave"].get("probe", {}):
        info(f"z_offset im SAVE_CONFIG-Block: {A['autosave']['probe']['z_offset']}")

    head("Installationsstand")
    (ok if A["logic_is_link"] else info)(f"{LOGIC_NAME}: " + (
        "Symlink aufs Repo" if A["logic_is_link"] else
        "alte Einzeldatei (wird ersetzt, Werte werden übernommen)" if A["legacy_logic"] else "fehlt"))
    (ok if A["settings_exists"] else info)(f"{SETTINGS_NAME}: " + ("vorhanden" if A["settings_exists"] else "fehlt"))
    (ok if A["has_inc_logic"] and A["has_inc_settings"] else info)(
        "Includes in printer.cfg: " + ("vollständig" if A["has_inc_logic"] and A["has_inc_settings"] else "unvollständig"))
    (ok if A["nginx_has_include"] else info)("Web-Oberfläche in nginx: " + ("eingebunden" if A["nginx_has_include"] else "nein"))
    (ok if A["navi_has_entry"] else info)("Menüeintrag in Mainsail: " + ("vorhanden" if A["navi_has_entry"] else "nein"))
    (ok if A["um_present"] else info)("Update-Manager: " + ("eingetragen" if A["um_present"] else "nein"))

    head("Konflikte")
    if not A["conflicts"] and not A["kamp_adaptive"]:
        ok("keine")
    for s in A["conflicts"]:
        warn(f"[{s.name}] in {s.file}:{s.start + 1}")
    for inc in A["kamp_adaptive"]:
        warn(f"KAMP Adaptive_Meshing eingebunden in {inc['file']}:{inc['line'] + 1}")
    for w in ctx["warnings"]:
        warn(w)


# ---------------------------------------------------------------------------
# Werte abfragen und berechnen
# ---------------------------------------------------------------------------
class Asker:
    def __init__(self, yes):
        self.interactive = not yes and sys.stdin.isatty()

    def ask(self, prompt, default, kind="float"):
        prompt = tr(prompt)
        if kind == "bool":
            yes, no = ("j", "n") if i18n.LANG == "de" else ("y", "n")
            shown = yes if default else no
        else:
            shown = "" if default is None else (fmt(default) if kind == "float" else str(default))
        if not self.interactive:
            if default is None:
                raise SystemExit(tr(f"Kein Wert für '{prompt}' – interaktiv ausführen oder Wert in der Config setzen."))
            info(f"{prompt}: {shown}")
            return default
        while True:
            raw = input(f"  {prompt} [{shown}]: ").strip()
            if not raw:
                if default is None:
                    print("    " + tr("Wert erforderlich."))
                    continue
                return default
            if kind == "float":
                try:
                    return num(raw)
                except ValueError:
                    print("    " + tr("Bitte eine Zahl eingeben."))
                    continue
            if kind == "bool":
                return raw.lower() in ("j", "ja", "y", "yes", "1", "true")
            return raw

    def confirm(self, prompt, default=True):
        if not self.interactive:
            return default
        yes = "J" if i18n.LANG == "de" else "Y"
        d = f"{yes}/n" if default else f"{yes.lower()}/N"
        raw = input(f"  {tr(prompt)} [{d}]: ").strip().lower()
        if not raw:
            return default
        return raw in ("j", "ja", "y", "yes")


def opt_num(d, key, default):
    try:
        return num(d[key]) if key in d else default
    except ValueError:
        return default


def gather(env, A, asker, reconfigure):
    """Fragt die Werte ab. Vorgaben kommen aus der bestehenden Config."""
    p, v, au = A["probe"], A["vars"], A["autosave"].get("probe", {})
    head("Einstellungen")
    info("Enter übernimmt den Vorschlag in [Klammern]. Dezimal mit Punkt oder Komma.")

    V = {}
    V["pin"] = asker.ask("Probe-Pin (z. B. ^PG15, NC-Schalter meist ohne !)", p.get("pin"), kind="str")
    V["x_offset"] = asker.ask("Probe x_offset (links der Düse = negativ)", opt_num(p, "x_offset", -18.0))
    V["y_offset"] = asker.ask("Probe y_offset (hinter der Düse = positiv)", opt_num(p, "y_offset", 15.0))
    if "z_offset" in au:
        V["z_offset"] = opt_num(au, "z_offset", 0.0)
        info(f"Probe z_offset: {fmt(V['z_offset'])} (aus SAVE_CONFIG-Block, bleibt dort)")
    else:
        V["z_offset"] = asker.ask("Probe z_offset (Auslösehöhe, per MEASURE_PROBE_OFFSET)", opt_num(p, "z_offset", 9.0))
    V["probe_speed"] = asker.ask("Probe-Geschwindigkeit mm/s", opt_num(p, "speed", 2.0))

    info("")
    info("Dock (Andocken: von rechts nach links, Lösen: in Y wegfahren)")
    V["dock_x"] = asker.ask("Dock X (Düsenposition beim Andocken)", opt_num(v, "variable_dock_x", 1.0))
    V["dock_y"] = asker.ask("Dock Y", opt_num(v, "variable_dock_y", 119.0))
    V["approach_dx"] = asker.ask("Anfahrweg rechts vom Dock (mm)", opt_num(v, "variable_approach_dx", 20.0))
    V["staging_y"] = asker.ask("Y-Bahn vor dem Dock / Löse-Richtung", opt_num(v, "variable_staging_y", 100.0))
    V["safe_z"] = asker.ask("Z-Höhe für Dock-Fahrten", opt_num(v, "variable_safe_z", max(14.0, math.ceil(V["z_offset"]) + 5)))
    V["travel_f"] = asker.ask("Verfahrgeschwindigkeit mm/min", opt_num(v, "variable_travel_f", 4000.0))
    V["dock_f"] = asker.ask("Dock-Geschwindigkeit mm/min", opt_num(v, "variable_dock_f", 4000.0))
    V["verify"] = asker.ask("Andock-Status per Probe-Pin prüfen",
                            str(v.get("variable_verify", "True")).lower() != "false", kind="bool")

    info("")
    info("Bettschrauben: Düsenposition, wenn die Düse genau über der Schraube steht")
    screws = []
    meta_screws = A["meta"].get("screw", [])
    defaults = []
    for line in meta_screws:
        parts = line.split(None, 2)
        try:
            defaults.append((num(parts[0]), num(parts[1]), parts[2] if len(parts) > 2 else ""))
        except (ValueError, IndexError):
            pass
    if not defaults:
        defaults = DEFAULT_SCREWS
    count = int(asker.ask("Anzahl Schrauben", float(len(defaults))))
    for i in range(count):
        d = defaults[i] if i < len(defaults) else (60.0, 60.0, f"Schraube {i + 1}")
        name = asker.ask(f"Schraube {i + 1} Name", d[2] or f"Schraube {i + 1}", kind="str")
        sx = asker.ask(f"  {name}: Düse X", d[0])
        sy = asker.ask(f"  {name}: Düse Y", d[1])
        screws.append((sx, sy, name))
    V["screws"] = screws
    V["screw_thread"] = asker.ask("Gewinde (CW-M3 / CCW-M3)", A["screws_cfg"].get("screw_thread", "CW-M3"), kind="str")
    margin_default = num(A["meta"]["mesh_margin"][0]) if A["meta"].get("mesh_margin") else 3.0
    V["mesh_margin"] = asker.ask("Randabstand fürs Mesh (mm)", margin_default)
    lang = str(v.get("variable_lang", i18n.LANG)).strip("'\"").lower()
    V["lang"] = asker.ask("Sprache der Klipper-Meldungen (de/en)", lang if lang in ("de", "en") else i18n.LANG, kind="str").lower()
    if V["lang"] not in ("de", "en"):
        V["lang"] = i18n.LANG
    return V


def compute(V, A):
    """Mesh-Grenzen, Schrauben-Düsenpositionen und Referenzpunkt berechnen."""
    (xmin, xmax), (ymin, ymax) = A["x_range"], A["y_range"]
    xo, yo, m = V["x_offset"], V["y_offset"], V["mesh_margin"]
    warnings = []

    # Bereich, den die Probe auf dem Bett erreicht (Bett = Verfahrbereich)
    pxl, pxh = max(xmin, xmin + xo), min(xmax, xmax + xo)
    pyl, pyh = max(ymin, ymin + yo), min(ymax, ymax + yo)
    mesh_min = (round(pxl + m, 1), round(pyl + m, 1))
    mesh_max = (round(pxh - m, 1), round(pyh - m, 1))
    if mesh_min[0] >= mesh_max[0] or mesh_min[1] >= mesh_max[1]:
        raise SystemExit(tr("Mesh-Bereich ist leer – Offsets oder Randabstand prüfen."))

    # Düsenbereich, der beim Mesh abgedeckt wird
    nxl, nxh = mesh_min[0] - xo, mesh_max[0] - xo
    nyl, nyh = mesh_min[1] - yo, mesh_max[1] - yo
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    safe_x = round(min(max(cx, nxl), nxh), 1)
    safe_y = round(min(max(cy, nyl), nyh), 1)

    screws = []
    for sx, sy, name in V["screws"]:
        nx, ny = sx - xo, sy - yo
        cnx, cny = min(max(nx, xmin), xmax), min(max(ny, ymin), ymax)
        dist = math.hypot(nx - cnx, ny - cny)
        screws.append({"name": name, "x": round(cnx, 2), "y": round(cny, 2), "dist": dist, "sx": sx, "sy": sy})
        if dist > 15:
            warnings.append(f"Schraube '{name}': Probe misst {dist:.0f} mm neben der Schraube")

    hmz = max(10.0, math.ceil(V["z_offset"] + 4))
    if V["safe_z"] < V["z_offset"] + 3:
        warnings.append(f"Dock-Höhe {fmt(V['safe_z'])} ist knapp über der Probe-Spitze ({fmt(V['z_offset'])}) – Kollisionsgefahr")
    if V["dock_x"] + V["approach_dx"] > xmax:
        warnings.append("Anfahrpunkt rechts vom Dock liegt außerhalb des Verfahrbereichs")
    for nm, val, lo, hi in (("Dock X", V["dock_x"], xmin, xmax), ("Dock Y", V["dock_y"], ymin, ymax),
                            ("Y-Bahn", V["staging_y"], ymin, ymax)):
        if not lo <= val <= hi:
            warnings.append(f"{nm} {fmt(val)} liegt außerhalb des Verfahrbereichs ({fmt(lo)}..{fmt(hi)})")

    return {"mesh_min": mesh_min, "mesh_max": mesh_max, "safe": (safe_x, safe_y),
            "screws": screws, "hmz": hmz, "warnings": warnings,
            "nozzle_cover": ((nxl, nxh), (nyl, nyh))}


def render_settings(V, R, A):
    tpl = Template(SETTINGS_TPL.read_text())
    screws_block = []
    meta = []
    for i, s in enumerate(R["screws"], 1):
        note = "  # " + (tr("Probe direkt über der Schraube") if s["dist"] < 0.5 else tr("Probe {d} mm neben der Schraube").format(d=f"{s['dist']:.0f}"))
        screws_block.append(f"screw{i}: {fmt(s['x'])}, {fmt(s['y'])}{note}")
        screws_block.append(f"screw{i}_name: {s['name']}")
        meta.append(f"#@screw {fmt(s['sx'])} {fmt(s['sy'])} {s['name']}")
    text = tpl.substitute(
        date=datetime.date.today().isoformat(),
        mesh_margin=fmt(V["mesh_margin"]),
        screw_meta="\n".join(meta),
        dock_x=fmt(V["dock_x"]), dock_y=fmt(V["dock_y"]), approach_dx=fmt(V["approach_dx"]),
        staging_y=fmt(V["staging_y"]), safe_x=fmt(R["safe"][0]), safe_y=fmt(R["safe"][1]),
        safe_z=fmt(V["safe_z"]), travel_f=fmt(V["travel_f"]), dock_f=fmt(V["dock_f"]),
        verify="True" if V["verify"] else "False",
        pin=V["pin"], x_offset=fmt(V["x_offset"]), y_offset=fmt(V["y_offset"]),
        z_offset=fmt(V["z_offset"]), probe_speed=fmt(V["probe_speed"]),
        hmz=fmt(R["hmz"]),
        mesh_min=f"{fmt(R['mesh_min'][0])}, {fmt(R['mesh_min'][1])}",
        mesh_max=f"{fmt(R['mesh_max'][0])}, {fmt(R['mesh_max'][1])}",
        zref=f"{fmt(R['safe'][0])}, {fmt(R['safe'][1])}",
        screws_block="\n".join(screws_block),
        screw_thread=V["screw_thread"],
        lang=V["lang"],
    )
    # Nur Kommentare übersetzen, nie Werte (z. B. Schraubennamen)
    tl = []
    for line in text.splitlines():
        if (line.startswith("#") and not line.startswith("#@")) or line.startswith("description:"):
            line = tr(line)
        elif "action_respond_info" in line or " # " in line:
            head_, sep, tail = line.partition(" # ")
            line = tr(head_) + sep + tr(tail) if "action_respond_info" in line else head_ + sep + tr(tail)
        tl.append(line)
    text = "\n".join(tl) + "\n"
    # Optionen, die im SAVE_CONFIG-Block stehen, dürfen nicht zusätzlich in einer
    # eingebundenen Datei stehen – sonst schlägt jedes SAVE_CONFIG fehl.
    out, sect = [], None
    for line in text.splitlines():
        m = SECTION_RE.match(line)
        if m:
            sect = m.group(1).strip().lower()
        else:
            om = OPTION_RE.match(line)
            if om and sect and om.group(1).lower() in A["autosave"].get(sect, {}):
                line = f"# {line}   " + tr("(steht im SAVE_CONFIG-Block von printer.cfg)")
        out.append(line)
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Datei-Operationen
# ---------------------------------------------------------------------------
class Ops:
    def __init__(self, dry, use_sudo=True):
        self.dry = dry
        self.use_sudo = use_sudo

    def write(self, path, content, root=False):
        path = Path(path)
        if self.dry:
            info(c("2", f"[dry-run] schreibe {path}"))
            return
        if root and not self._writable(path):
            subprocess.run(["sudo", "tee", str(path)], input=content, text=True,
                           stdout=subprocess.DEVNULL, check=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def remove(self, path, root=False):
        path = Path(path)
        if not (path.exists() or path.is_symlink()):
            return
        if self.dry:
            info(c("2", f"[dry-run] entferne {path}"))
            return
        if root and not os.access(path.parent, os.W_OK):
            subprocess.run(["sudo", "rm", "-f", str(path)], check=True)
        else:
            path.unlink()

    def run_root(self, cmd):
        if self.dry:
            info(c("2", "[dry-run] " + " ".join(cmd)))
            return subprocess.CompletedProcess(cmd, 0, "", "")
        full = cmd if os.geteuid() == 0 or not self.use_sudo else ["sudo"] + cmd
        return subprocess.run(full, capture_output=True, text=True)

    @staticmethod
    def _writable(path):
        if path.exists():
            return os.access(path, os.W_OK)
        return os.access(path.parent, os.W_OK) if path.parent.exists() else False


def backup(env, ops):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = env["home"] / "dockprobe-backups"
    target = bdir / f"config-{ts}.tar.gz"
    if ops.dry:
        info(c("2", f"[dry-run] Backup nach {target}"))
        return target
    bdir.mkdir(exist_ok=True)
    with tarfile.open(target, "w:gz") as tar:
        tar.add(env["cfg"], arcname="config",
                filter=lambda ti: None if ti.name.endswith((".gcode", ".zip")) else ti)
    site = env["nginx_site"]
    if site and site.exists():
        try:
            shutil.copy2(site, bdir / f"nginx-{site.name}-{ts}")
        except OSError:
            pass
    return target


def comment_sections(sections, ops):
    """Sections in ihrer Datei mit MARK auskommentieren (Zeilenzahl bleibt gleich)."""
    by_file = {}
    for s in sections:
        by_file.setdefault(s.file, []).append(s)
    for f, secs in by_file.items():
        lines = Path(f).read_text(errors="replace").split("\n")
        for s in secs:
            for i in range(s.start, s.end):
                if not lines[i].startswith(MARK) and not lines[i].startswith("#*#"):
                    lines[i] = MARK + lines[i]
        ops.write(f, "\n".join(lines))
        for s in secs:
            ok(f"[{s.name}] in {os.path.basename(f)} auskommentiert")


def comment_line(path, idx, ops):
    lines = Path(path).read_text(errors="replace").split("\n")
    if not lines[idx].startswith(MARK):
        lines[idx] = MARK + lines[idx]
        ops.write(path, "\n".join(lines))


def uncomment_all(cfg, ops):
    n = 0
    for f in sorted(set(glob.glob(str(cfg / "**/*.cfg"), recursive=True))):
        if os.path.islink(f):
            continue
        text = Path(f).read_text(errors="replace")
        if MARK not in text:
            continue
        lines = [l[len(MARK):] if l.startswith(MARK) else l for l in text.split("\n")]
        ops.write(f, "\n".join(lines))
        n += 1
        ok(f"Auskommentierte Zeilen in {os.path.basename(f)} wiederhergestellt")
    return n


def add_includes(printer_cfg, A, ops):
    lines = printer_cfg.read_text(errors="replace").split("\n")
    new = []
    if not A["has_inc_settings"]:
        new.append(f"[include {SETTINGS_NAME}]")
    if not A["has_inc_logic"]:
        new.append(f"[include {LOGIC_NAME}]")
    if not new:
        return
    idx = next((i for i, l in enumerate(lines) if l.startswith("[")), len(lines))
    lines[idx:idx] = new + [""]
    ops.write(printer_cfg, "\n".join(lines))
    ok("Includes in printer.cfg eingetragen")


def remove_includes(printer_cfg, ops):
    lines = printer_cfg.read_text(errors="replace").split("\n")
    pat = re.compile(rf"^\[include\s+({re.escape(LOGIC_NAME)}|{re.escape(SETTINGS_NAME)})\s*\]")
    kept = [l for l in lines if not pat.match(l)]
    if len(kept) != len(lines):
        ops.write(printer_cfg, "\n".join(kept))
        ok("Includes aus printer.cfg entfernt")


# ---- nginx ----------------------------------------------------------------
def nginx_snippet():
    return (f"# voron0-dockprobe – Kalibrier-Oberfläche (automatisch erzeugt)\n"
            f"location = /probe {{ return 301 /probe/; }}\n"
            f"location ^~ /probe/ {{\n"
            f"    alias {WEB_DIR}/;\n"
            f"    index index.html;\n"
            f"    add_header Cache-Control \"no-cache\";\n"
            f"}}\n")


def nginx_install(env, ops):
    site = env["nginx_site"]
    if not site or not site.exists():
        warn("nginx-Site von Mainsail nicht gefunden – Web-Oberfläche übersprungen")
        return False
    snip_dir = os.path.dirname(NGINX_SNIPPET)
    if not os.path.isdir(snip_dir):
        ops.run_root(["mkdir", "-p", snip_dir])
    ops.write(NGINX_SNIPPET, nginx_snippet(), root=True)
    text = site.read_text(errors="replace")
    if NGINX_SNIPPET not in text:
        lines = text.split("\n")
        idx = next((i for i, l in enumerate(lines) if re.match(r"^\s*server\s*\{", l)), None)
        if idx is None:
            warn(f"Kein server-Block in {site} – bitte 'include {NGINX_SNIPPET};' manuell eintragen")
            return False
        lines.insert(idx + 1, f"    include {NGINX_SNIPPET};  {NGINX_TAG}")
        ops.write(site, "\n".join(lines), root=True)
    if not env["nginx_bin"]:
        warn("nginx-Binary nicht gefunden – Test und Reload übersprungen")
        return True
    r = ops.run_root([env["nginx_bin"], "-t"])
    if r.returncode != 0:
        err("nginx-Test fehlgeschlagen, Änderung wird zurückgenommen:\n" + (r.stderr or r.stdout))
        ops.write(site, text, root=True)
        ops.remove(NGINX_SNIPPET, root=True)
        return False
    ops.run_root(["systemctl", "reload", "nginx"])
    ok("Web-Oberfläche in nginx eingebunden (/probe/)")
    home_mode = env["home"].stat().st_mode
    if not home_mode & 0o001:
        warn(f"{env['home']} ist für nginx nicht betretbar – ggf. 'chmod o+x {env['home']}'")
    return True


def nginx_remove(env, ops):
    site = env["nginx_site"]
    if site and site.exists():
        text = site.read_text(errors="replace")
        if NGINX_SNIPPET in text:
            lines = [l for l in text.split("\n") if NGINX_SNIPPET not in l]
            ops.write(site, "\n".join(lines), root=True)
    ops.remove(NGINX_SNIPPET, root=True)
    if env["nginx_bin"]:
        r = ops.run_root([env["nginx_bin"], "-t"])
        if r.returncode == 0:
            ops.run_root(["systemctl", "reload", "nginx"])
    ok("nginx-Eintrag entfernt")


# ---- Mainsail-Menü ------------------------------------------------------------
def navi_install(env, ops):
    navi = env["cfg"] / ".theme" / "navi.json"
    entries = []
    if navi.exists():
        try:
            entries = json.loads(navi.read_text())
            if not isinstance(entries, list):
                raise ValueError
        except ValueError:
            warn(f"{navi} ist kein gültiges JSON-Array – Menüeintrag übersprungen")
            return
    entries = [e for e in entries if e.get("href") != NAVI_HREF]
    entries.append({"title": "Probe", "href": NAVI_HREF, "target": "_self",
                    "position": 45, "icon": NAVI_ICON})
    ops.write(navi, json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    ok("Menüeintrag 'Probe' in Mainsail angelegt (Browser neu laden)")


def navi_remove(env, ops):
    navi = env["cfg"] / ".theme" / "navi.json"
    if not navi.exists():
        return
    try:
        entries = json.loads(navi.read_text())
    except ValueError:
        return
    rest = [e for e in entries if e.get("href") != NAVI_HREF]
    if len(rest) == len(entries):
        return
    if rest:
        ops.write(navi, json.dumps(rest, indent=2, ensure_ascii=False) + "\n")
    else:
        ops.remove(navi)
    ok("Menüeintrag entfernt")


# ---- Moonraker update_manager ------------------------------------------------
def um_install(env, ops):
    mc = env["moonraker_conf"]
    origin = git_origin()
    if not mc:
        warn("moonraker.conf nicht gefunden – Update-Manager übersprungen")
        return False
    if not origin:
        warn("Repo hat keinen git-origin (nicht per git clone installiert) – Update-Manager übersprungen")
        return False
    text = mc.read_text(errors="replace")
    if f"[{UM_SECTION}]" in text:
        return False
    block = (f"\n[{UM_SECTION}]\n"
             f"type: git_repo\n"
             f"channel: dev\n"
             f"path: {REPO_DIR}\n"
             f"origin: {origin}\n"
             f"primary_branch: {git_branch()}\n"
             f"managed_services: klipper\n"
             f"info_tags:\n"
             f"    desc=ZeroClick Dock-Probe (Voron V0.2)\n")
    ops.write(mc, text.rstrip("\n") + "\n" + block)
    ok("Update-Manager in moonraker.conf eingetragen")
    return True


def um_remove(env, ops):
    mc = env["moonraker_conf"]
    if not mc:
        return False
    lines = mc.read_text(errors="replace").split("\n")
    out, skip, changed = [], False, False
    for l in lines:
        m = SECTION_RE.match(l)
        if m:
            skip = m.group(1).strip() == UM_SECTION
            changed |= skip
        if not skip:
            out.append(l)
    if changed:
        ops.write(mc, "\n".join(out))
        ok("Update-Manager-Eintrag entfernt")
    return changed


# ---- Moonraker-API ----------------------------------------------------------------
def api(method, path, timeout=5):
    req = urllib.request.Request(MOONRAKER + path, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def printer_busy():
    try:
        st = api("GET", "/printer/objects/query?print_stats")["result"]["status"]["print_stats"]["state"]
        return st in ("printing", "paused")
    except (urllib.error.URLError, KeyError, ValueError, OSError):
        return None


def restart_services(restart_moonraker, ops):
    if ops.dry:
        info(c("2", "[dry-run] Klipper-Neustart"))
        return
    busy = printer_busy()
    if busy:
        warn("Es läuft ein Druck – Neustart übersprungen. Danach RESTART ausführen.")
        return
    if busy is None:
        warn("Moonraker nicht erreichbar – bitte Klipper manuell neu starten (RESTART)")
        return
    if restart_moonraker:
        try:
            api("POST", "/machine/services/restart?service=moonraker")
            ok("Moonraker wird neu gestartet")
            time.sleep(8)
        except (urllib.error.URLError, OSError):
            warn("Moonraker-Neustart fehlgeschlagen – bitte manuell neu starten")
    try:
        api("POST", "/printer/restart")
    except (urllib.error.URLError, OSError):
        warn("Klipper-Neustart über Moonraker fehlgeschlagen – bitte RESTART ausführen")
        return
    info("Warte auf Klipper ...")
    for _ in range(30):
        time.sleep(1)
        try:
            res = api("GET", "/printer/info")["result"]
        except (urllib.error.URLError, KeyError, ValueError, OSError):
            continue
        if res.get("state") == "ready":
            ok("Klipper ist bereit")
            return
        if res.get("state") == "error":
            err("Klipper meldet einen Fehler:\n" + res.get("state_message", ""))
            return
    warn("Klipper ist nach 30 s noch nicht bereit – Status in Mainsail prüfen")


# ---------------------------------------------------------------------------
# Abläufe
# ---------------------------------------------------------------------------
def do_install(env, A, args, ops, asker):
    cfg = env["cfg"]

    # Bestehende Einstellungen behalten?
    write_settings = True
    if A["settings_exists"] and not args.reconfigure:
        write_settings = asker.confirm(f"{SETTINGS_NAME} existiert – Werte neu abfragen und Datei neu erzeugen?", False)

    V = R = None
    if write_settings:
        V = gather(env, A, asker, args.reconfigure)
        R = compute(V, A)
        head("Berechnet")
        info(f"Mesh (Probe-Koordinaten): {fmt(R['mesh_min'][0])},{fmt(R['mesh_min'][1])} bis "
             f"{fmt(R['mesh_max'][0])},{fmt(R['mesh_max'][1])}")
        (nxl, nxh), (nyl, nyh) = R["nozzle_cover"]
        info(f"Düse fährt dabei X {fmt(nxl)}..{fmt(nxh)}, Y {fmt(nyl)}..{fmt(nyh)}")
        info(f"Referenz-/Parkposition (zero_reference, Papiertest): {fmt(R['safe'][0])}, {fmt(R['safe'][1])}")
        info(f"horizontal_move_z: {fmt(R['hmz'])}")
        for s in R["screws"]:
            info(f"Schraube {s['name']}: Düse {fmt(s['x'])}, {fmt(s['y'])}"
                 + ("" if s["dist"] < 0.5 else f"  (Probe {s['dist']:.0f} mm neben der Schraube)"))
        for w in R["warnings"]:
            warn(w)

    web = not args.no_web
    head("Geplante Änderungen")
    info("Backup des Config-Ordners nach ~/dockprobe-backups/")
    if A["legacy_logic"]:
        info(f"alte {LOGIC_NAME} umbenennen in {LOGIC_NAME}.old")
    info(f"{LOGIC_NAME} als Symlink aufs Repo anlegen")
    if write_settings:
        info(f"{SETTINGS_NAME} " + ("neu erzeugen" if A["settings_exists"] else "anlegen"))
    for s in A["conflicts"]:
        inside = os.path.realpath(s.file).startswith(str(cfg) + os.sep)
        info(f"[{s.name}] in {os.path.basename(s.file)} auskommentieren" if inside
             else f"[{s.name}] in {s.file} – liegt außerhalb des Config-Ordners, bitte manuell entfernen")
    for inc in A["kamp_adaptive"]:
        info(f"KAMP Adaptive_Meshing-Include in {os.path.basename(inc['file'])} auskommentieren")
    info("Includes in printer.cfg ergänzen")
    if web:
        info("Web-Oberfläche in nginx einbinden und Menüeintrag in Mainsail anlegen")
    info("Update-Manager in moonraker.conf eintragen (falls per git clone installiert)")
    if not args.no_restart:
        info("Klipper neu starten")

    if not asker.confirm("Fortfahren?", True):
        raise SystemExit(tr("Abgebrochen."))

    head("Installation")
    b = backup(env, ops)
    ok(f"Backup: {b}")

    if A["legacy_logic"]:
        target = cfg / f"{LOGIC_NAME}.old"
        if ops.dry:
            info(c("2", f"[dry-run] {LOGIC_NAME} -> {target.name}"))
        else:
            os.replace(cfg / LOGIC_NAME, target)
        ok(f"alte {LOGIC_NAME} gesichert als {target.name}")

    link = cfg / LOGIC_NAME
    if ops.dry:
        info(c("2", f"[dry-run] Symlink {link} -> {LOGIC_SRC}"))
    else:
        if link.is_symlink():
            link.unlink()
        link.symlink_to(LOGIC_SRC)
    ok(f"{LOGIC_NAME} verlinkt")

    if write_settings:
        ops.write(cfg / SETTINGS_NAME, render_settings(V, R, A))
        ok(f"{SETTINGS_NAME} geschrieben")

    # Konflikte (nur innerhalb des Config-Ordners anfassen)
    inside = [s for s in A["conflicts"] if os.path.realpath(s.file).startswith(str(cfg) + os.sep)]
    outside = [s for s in A["conflicts"] if s not in inside]
    if inside:
        comment_sections(inside, ops)
    for s in outside:
        warn(f"[{s.name}] in {s.file} bitte manuell entfernen")
    for inc in A["kamp_adaptive"]:
        comment_line(inc["file"], inc["line"], ops)
        ok(f"KAMP Adaptive_Meshing in {os.path.basename(inc['file'])} deaktiviert")

    add_includes(env["printer_cfg"], A, ops)

    if web:
        if nginx_install(env, ops):
            navi_install(env, ops)
    um_changed = um_install(env, ops)

    if not args.no_restart:
        restart_services(um_changed, ops)

    head("Fertig")
    info("Nächste Schritte (in Mainsail unter 'Probe' oder in der Konsole):")
    info("  1. PROBE_STATUS            – Probe im Dock muss TRIGGERED melden")
    info("  2. CALIBRATE_Z_ENDSTOP     – Papiertest, ACCEPT, SAVE_CONFIG")
    info("  3. MEASURE_PROBE_OFFSET    – Ergebnis ~0, sonst z_offset anpassen")
    info("  4. PROBE_ACCURACY SAMPLES=10")
    info("  5. CALIBRATE_ALL BED=60 SOAK=10")
    info(f"Bei Problemen: Backup liegt in {b}, Deinstallation mit ./uninstall.sh")


def do_uninstall(env, A, args, ops, asker):
    head("Deinstallation")
    if not asker.confirm("voron0-dockprobe entfernen?", True):
        raise SystemExit("Abgebrochen.")
    b = backup(env, ops)
    ok(f"Backup: {b}")
    cfg = env["cfg"]
    remove_includes(env["printer_cfg"], ops)
    link = cfg / LOGIC_NAME
    if link.is_symlink():
        ops.remove(link)
        ok(f"{LOGIC_NAME}-Symlink entfernt")
    if (cfg / SETTINGS_NAME).exists():
        if asker.confirm(f"{SETTINGS_NAME} löschen? (Nein = behalten für spätere Neuinstallation)", False):
            ops.remove(cfg / SETTINGS_NAME)
            ok(f"{SETTINGS_NAME} gelöscht")
    if asker.confirm("Vom Installer auskommentierte Sections wiederherstellen?", True):
        uncomment_all(cfg, ops)
    nginx_remove(env, ops)
    navi_remove(env, ops)
    um_changed = um_remove(env, ops)
    if not args.no_restart:
        restart_services(um_changed, ops)
    head("Fertig")


def main():
    ap = argparse.ArgumentParser(description="voron0-dockprobe – Installer (de/en)")
    ap.add_argument("--analyze", action="store_true", help="nur analysieren / analyse only")
    ap.add_argument("--uninstall", action="store_true", help="Paket entfernen / uninstall")
    ap.add_argument("--reconfigure", action="store_true", help="Einstellungen neu abfragen / ask for settings again")
    ap.add_argument("--yes", "-y", action="store_true", help="Vorschläge übernehmen / accept all suggestions")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen / show what would happen")
    ap.add_argument("--no-web", action="store_true", help="ohne Web-Oberfläche / without web UI")
    ap.add_argument("--no-restart", action="store_true", help="Klipper nicht neu starten / do not restart Klipper")
    ap.add_argument("--config-dir", help="Config-Ordner / config folder (~/printer_data/config)")
    ap.add_argument("--nginx-site", help="nginx-Site von Mainsail / Mainsail nginx site file")
    ap.add_argument("--lang", choices=("de", "en"), help="Sprache der Ausgaben und Meldungen / language")
    args = ap.parse_args()

    i18n.LANG = args.lang or i18n.default_lang()
    if not args.lang and not args.yes and sys.stdin.isatty():
        raw = input(f"Sprache / Language [de/en] ({i18n.LANG}): ").strip().lower()
        if raw in ("de", "en"):
            i18n.LANG = raw
    print(c("1", tr("voron0-dockprobe – Dock-Probe-Kit für Voron V0.2")))
    env = detect(args)
    if not env["cfg"] or not env["printer_cfg"].exists():
        raise SystemExit(tr("printer.cfg nicht gefunden – mit --config-dir angeben."))

    A = analyze(env)
    report(env, A)
    if args.analyze:
        return

    ops = Ops(args.dry_run)
    asker = Asker(args.yes)
    if args.uninstall:
        do_uninstall(env, A, args, ops, asker)
    else:
        do_install(env, A, args, ops, asker)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + tr("Abgebrochen."))
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        err(f"Befehl fehlgeschlagen: {e}")
        err("Installation unvollständig – Backup liegt in ~/dockprobe-backups/")
        sys.exit(1)
