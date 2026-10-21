# Third-party notices

voron0-dockprobe is licensed under the GNU General Public License v3.0 or later
(see [LICENSE](LICENSE)). It contains or is derived from the following third-party material.

## Included in this repository

### Material Design Icons
- **What:** SVG path data of the icons used in `web/index.html`
  (taken from the npm package `@mdi/js` 7.4.47)
- **Copyright:** Pictogrammers (https://pictogrammers.com)
- **License:** Apache License 2.0 – full text in [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).
  The Pictogrammers Free License states: *"Icons: Apache 2.0 … Code: MIT"*.
- **Changes:** none – only the path strings of the icons in use are embedded.

### ZeroClick sample macros
- **What:** the attach/detach move sequence in `klipper/probe_dock.cfg` (`ATTACH_PROBE`,
  `DETACH_PROBE`) is based on the sample macros in the ZeroClick README.
  The moves were parameterised and extended (state tracking, pin verification, speed override).
- **Copyright:** Zruncho – https://github.com/zruncho3d/ZeroClick
- **License:** GNU GPL v3.0

### Mainsail component styles
- **What:** a handful of component-scoped layout rules in `web/index.html` (panel toolbar,
  top bar, sidebar item and button group) mirror Mainsail's components so that Mainsail's own
  stylesheet renders the page correctly. They are marked in the source.
- **Copyright:** mainsail-crew – https://github.com/mainsail-crew/mainsail
- **License:** GNU GPL v3.0

## Used at runtime, not included

These projects are required or used on the printer but are **not** distributed with this repository:

| Project | Use | License |
|---|---|---|
| [Klipper](https://github.com/Klipper3d/klipper) | firmware the macros run on | GPL-3.0 |
| [Moonraker](https://github.com/Arksine/moonraker) | API used by the web UI and installer, update manager | GPL-3.0 |
| [Mainsail](https://github.com/mainsail-crew/mainsail) | web interface; its stylesheets (including [Vuetify](https://github.com/vuetifyjs/vuetify), MIT) are loaded from the printer's own Mainsail installation at runtime | GPL-3.0 |
| [nginx](https://nginx.org) | serves the web UI next to Mainsail | BSD-2-Clause |
