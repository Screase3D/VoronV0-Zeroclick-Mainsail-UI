# =====================================================================
#  voron0-dockprobe – DEINE Einstellungen
#  Erzeugt von install.sh am ${date}.
#  Wird bei Updates NICHT überschrieben. Werte neu berechnen lassen:
#      ./install.sh --reconfigure
#
#  Die Zeilen mit "#@" merkt sich der Installer für --reconfigure.
# =====================================================================
#@schema 2
#@mesh_margin ${mesh_margin}
${screw_meta}

[gcode_macro _PROBE_VARS]
description: Einstellungen für Dock, Wege und Ablauf (voron0-dockprobe)
variable_dock_x:        ${dock_x}
variable_dock_y:        ${dock_y}
variable_approach_dx:   ${approach_dx}
variable_staging_y:     ${staging_y}
variable_safe_x:        ${safe_x}
variable_safe_y:        ${safe_y}
variable_safe_z:        ${safe_z}
variable_travel_f:      ${travel_f}
variable_dock_f:        ${dock_f}
variable_z_f:           600
variable_max_screw_dev: 0.05
# verify: Andock-Status per QUERY_PROBE prüfen
#   Probe im Dock -> TRIGGERED, Probe am Toolhead -> open
variable_verify:        ${verify}
variable_lang:          "${lang}"      # Sprache der Klipper-Meldungen: de / en
gcode:
    {action_respond_info("_PROBE_VARS enthält nur Einstellungen")}

[probe]
pin: ${pin}
x_offset: ${x_offset}
y_offset: ${y_offset}
z_offset: ${z_offset}
speed: ${probe_speed}
lift_speed: 10
samples: 2
samples_result: median
sample_retract_dist: 2
samples_tolerance: 0.01
samples_tolerance_retries: 3

[bed_mesh]
speed: 150
horizontal_move_z: ${hmz}
mesh_min: ${mesh_min}
mesh_max: ${mesh_max}
probe_count: 5, 5
algorithm: bicubic
zero_reference_position: ${zref}

[screws_tilt_adjust]
# Düsenpositionen, an denen die Probe über (bzw. möglichst nah an) der Schraube misst
${screws_block}
horizontal_move_z: ${hmz}
speed: 150
screw_thread: ${screw_thread}
