# Rotary (Meerkat fork)

Y-motor-swap chuck rotary support for GRBL and other device drivers.

## Features

- **Object size:** outside diameter (mm), usable length (mm)
- **Auto wrap scale:** scene bed height → one full rotation (π × diameter)
- **Y steps calibration:** flat-bed `$101` vs rotary motor steps/mm
- **Software compensation (default):** scales Y in the GRBL driver so EEPROM can stay at gantry `$101`
- **Optional firmware mode:** write `$101` at job start, restore after job
- **Homing:** ignore G28; physical home → X only (`$HX`) when enabled

## Console

| Command | Purpose |
|---------|---------|
| `rotary` | Status (circumference, scales, Y factor) |
| `rotaryfit` | Scale selection to fit length × circumference (or use **Fit selection to rotary** in Rotary-Settings) |
| `rotarycal <measured_mm>` | Calibrate rotary Y steps after test line |
| `rotarysuggest <d_mm> <steps> <microsteps> <ratio>` | Estimate rotary steps/mm |
| `rotaryview` | Toggle stretched scene preview |

## Workflow (Y motor swap)

1. Wire rotary to Y driver; leave rotary mode **off** until ready.
2. Device → **Rotary:** set diameter, length, flat `$101` (159.6), calibrate rotary steps.
3. Enable **Rotary-Mode**; check **Ignore Home** and **Software Y steps compensate**.
4. Import art → `rotaryfit` → classify → simulate → burn.
5. Physical home: **$HX** only. Flat bed: disable rotary, restore Y motor and `$101`.

See `docs/meerk40t/20-rotary-pro.md` in the Meerkat workspace.
