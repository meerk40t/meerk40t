# GRBL Driver Firmware Support

## Overview

The MeerK40t GRBL driver supports multiple firmware implementations through a command translation system. This allows the same driver code to work with different controller firmware by translating logical command names to firmware-specific G-code or control strings.

## Supported Firmware Types

### 1. GRBL 1.1 (`grbl`)

**Description**: Standard GRBL 1.1 CNC controller firmware

**Target Hardware**: 
- Arduino-based controllers (Uno, Nano, etc.)
- grbl-Mega (AVR Mega2560)
- grbl-ESP32 (ESP32-based)
- FluidNC (ESP32 with WiFi)

**Command Set**:
- **Basic G-codes**: G0, G1, G4, G20, G21, G28, G90, G91, G92, G94, G93
- **Spindle/Laser**: M3 (on), M4 (laser mode), M5 (off)
- **Coolant Control**: M7 (mist on), M8 (flood on), M9 (all off)
- **Realtime Commands** (single-byte):
  - `!` - Feed hold (pause)
  - `~` - Cycle start (resume)
  - `\x18` (Ctrl-X) - Soft reset
  - `?` - Status report query
- **System Commands**:
  - `$H` - Run homing cycle
  - `$X` - Kill alarm lock / unlock
  - `$J=` - Jogging mode prefix (e.g., `$J=G91G21X10F1000`)
- **Query Commands**:
  - `$` - View help
  - `$$` - View all settings
  - `$G` - View parser state (modal commands)
  - `$#` - View work coordinate parameters
  - `$I` - View build info
  - `$N` - View startup blocks

**Use When**: Running standard GRBL 1.1 firmware, or GRBL-compatible firmware like FluidNC or grbl-ESP32.

---

### 2. grblHAL (`grblhal`)

**Description**: Modern GRBL evolution with extensive extensions for ARM/ESP32 controllers

**Target Hardware**:
- ESP32-based controllers
- ARM processors (STM32, iMXRT1062, etc.)
- Teensy 4.x boards
- Various 32-bit MCU platforms

**Command Set**: 
- **100% GRBL 1.1 Compatible** - All standard GRBL commands work
- **Extended G-codes**:
  - G33 - Threading cycles
  - G73, G81-G89 - Canned cycles
  - G96/G97 - CSS (Constant Surface Speed) spindle modes
  - G50/G51 - Scaling
  - G43/G49 - Tool length offset
- **Coolant Control**: M7 (mist), M8 (flood), M9 (off) - Full support
- **Extended M-codes**:
  - M62-M68 - Auxiliary I/O control
  - M70-M73 - Modal state save/restore
  - M201-M204 - Acceleration/jerk control
  - M280 - Servo control
  - M356 - RGB lighting
- **Plugin System**: Extensive plugin support for additional features

**Use When**: Running grblHAL firmware on 32-bit controllers. grblHAL is recommended for modern hardware due to its enhanced features and active development.

**Notes**: 
- Fully backward compatible with GRBL 1.1
- Supports advanced features like tool changers, coolant control, and complex kinematics
- Active development with regular updates

---

### 3. Marlin (`marlin`)

**Description**: 3D printer firmware adapted for CNC/laser use

**Target Hardware**:
- 3D printer control boards (RAMPS, SKR, etc.)
- Controllers originally designed for FDM 3D printing

**Command Set**:
- **Basic G-codes**: Same as GRBL (G0, G1, G4, G20, G21, G28, G90, G91, G92, G94, G93)
- **Coolant Control**: 
  - M7 - Mist coolant ON (requires COOLANT_MIST enabled)
  - M8 - Flood coolant / Air Assist ON (requires COOLANT_FLOOD or AIR_ASSIST enabled)
  - M9 - All coolant / Air Assist OFF
- **Spindle/Laser**: M3, M4, M5 (same as GRBL)
- **Realtime Commands**: !, ~, \x18, ? (compatible with GRBL)
- **System Commands**:
  - `G28` - Homing (replaces GRBL's `$H`)
  - `M999` - Software reset/restart (replaces GRBL's `$X`)
  - `G0` - Jogging (Marlin doesn't have `$J` command)
- **Query Commands** (use M-codes instead of $-commands):
  - `M115` - Firmware info (replaces `$`, `$I`)
  - `M503` - Report settings (replaces `$$`)
  - `M114` - Report position (replaces `$#`)

**Key Differences from GRBL**:
- No `$`-style system commands
- Uses M-codes for queries instead of $ syntax
- G28 for homing instead of $H
- M999 for unlock instead of $X (M410 is only a quick-stop)
- No dedicated jogging command (uses G0 with space-separated parameters)
- GRBL hardware-config UI is suppressed (uses $-commands that Marlin does not support)

**Use When**: Running Marlin firmware on a 3D printer board adapted for laser/CNC use.

---

### 4. Smoothieware (`smoothieware`)

**Description**: Smoothieboard firmware with GRBL-compatible mode

**Target Hardware**:
- Smoothieboard (LPC1769-based)
- Other ARM Cortex-M3 controllers
Coolant Control**: M7 (mist), M8 (flood), M9 (off)
- **
**Command Set**:
- **Basic G-codes**: Same as GRBL
- **Spindle/Laser**: M3, M4, M5 (same as GRBL)
- **Realtime Commands**: Compatible with GRBL (!, ~, \x18, ?) in grbl_mode
- **System Commands**:
  - `G28` - Homing (replaces GRBL's `$H`)
  - `$X` - Alarm unlock (same as GRBL)
  - `G0` - Jogging (no `$J` command)
- **Query Commands**: Supports GRBL-style queries in grbl_mode
  - `$`, `$$`, `$G`, `$#`, `$I`, `$N` - All work in GRBL compatibility mode

**Key Differences from GRBL**:
- G28 for homing instead of $H
- No $J jogging command (uses G0)
- Requires grbl_mode configuration for full GRBL compatibility

**Use When**: Running Smoothieware firmware on Smoothieboard or compatible ARM controllers.

**Notes**: 
- Enable `grbl_mode` in config for best GRBL compatibility
- Supports most GRBL query commands when in grbl_mode
- Realtime feed/power overrides (0x9x codes) are not advertised/guaranteed; treat as unsupported.

---

### 5. Custom (`custom`)

**Description**: User-configurable firmware with customizable commands

**Command Set**: Defaults to GRBL 1.1 commands but can be overridden per-command via MeerK40t settings.

**Configuration**: Commands can be customized through settings with the following keys:
- `custom_command_laser_on` - Default: "M3"
- `custom_command_laser_off` - Default: "M5"
- `custom_command_laser_mode` - Default: "M4"
- `custom_command_move_rapid` - Default: "G0"
- `custom_command_move_linear` - Default: "G1"
- `custom_command_dwell` - Default: "G4"
- `custom_command_units_mm` - Default: "G21"
- `custom_command_units_inches` - Default: "G20"
- `custom_command_absolute_mode` - Default: "G90"
- `custom_command_relative_mode` - Default: "G91"
- `custom_command_feedrate_mode` - Default: "G94"
- `custom_command_feedrate_inverse` - Default: "G93"
- `custom_command_home` - Default: "G28"
- `custom_command_coolant_mist_on` - Default: "M7"
- `custom_command_coolant_flood_on` - Default: "M8"
- `custom_command_coolant_off` - Default: "M9"
- `custom_command_set_position` - Default: "G92"
- `custom_command_pause` - Default: "!"
- `custom_command_resume` - Default: "~"
- `custom_command_reset` - Default: "\x18"
- `custom_command_status_query` - Default: "?"
- `custom_command_home_cycle` - Default: "$H"
- `custom_command_unlock` - Default: "$X"
- `custom_command_jog` - Default: "$J="
- `custom_command_query_help` - Default: "$"
- `custom_command_query_settings` - Default: "$$"
- `custom_command_query_parser` - Default: "$G"
- `custom_command_query_params` - Default: "$#"
- `custom_command_query_build` - Default: "$I"
- `custom_command_query_startup` - Default: "$N"

**Use When**: 
- Running custom/modified firmware
- Firmware with non-standard command syntax
- Testing new firmware implementations
- Need to override specific commands without changing code

**Example Configuration**:
```python
# In MeerK40t settings/console
kernel.device.setting(str, "firmware_type", "custom")
kernel.device.setting(str, "custom_command_home_cycle", "G28 X Y")
kernel.device.setting(str, "custom_command_unlock", "M999")
```

---

## Firmware Selection Guide

### Choose `grbl` if:
- Running standard GRBL 1.1 on Arduino/AVR
- Using grbl-Mega on Arduino Mega2560
- Using grbl-ESP32 on ESP32
- Using FluidNC on ESP32
- Want maximum compatibility with GRBL ecosystem

### Choose `grblhal` if:
- Running grblHAL firmware
- Using 32-bit ARM/ESP32 controllers
- Need advanced features (plugins, tool changers, multiple spindles)
- Want modern, actively developed GRBL fork

### Choose `marlin` if:
- Running Marlin firmware on 3D printer board
- Converting 3D printer to laser/CNC
- Have RAMPS, SKR, or similar 3D printer controller

### Choose `smoothieware` if:
- Using Smoothieboard controller
- Running Smoothieware firmware
- Have grbl_mode enabled in Smoothieware config

### Choose `custom` if:
- Running unknown/custom firmware
- Need to override specific commands
- Testing new firmware implementations
- Firmware doesn't match standard profiles

---

## Command Translation System

### How It Works

The driver translates logical command names to firmware-specific strings:

```python
# Instead of hardcoding:
self.out("$H\n")  # GRBL-specific

# Use translation:
self.out(f"{self.translate_command('home_cycle')}{self.line_end}")
# Returns "$H" for GRBL, "G28" for Marlin, etc.
```

### Benefits

1. **Single Codebase**: One driver supports multiple firmware types
2. **Maintainability**: Changes to commands in one place
3. **Extensibility**: Easy to add new firmware types
4. **User Control**: Custom firmware allows per-command overrides

---

## Jogging Commands

Jogging has special handling due to syntax differences:

### GRBL/grblHAL Format:
```
$J=G91G21X10F1000
```
- Compact format
- Parameters concatenated

### Marlin/Smoothieware Format:
```
G0 G91 G21 X10 F1000
```
- Space-separated parameters
- Uses G0 instead of $J

The `jog_command()` method automatically handles this conversion.

---

## Implementation Notes

### Realtime Commands
- Single-byte commands (!, ~, ?, \x18) work identically across all firmware
- Sent directly to controller without buffering
- Highest priority

### System Commands
- Main differences between firmware types
- GRBL uses $ prefix, Marlin uses M/G codes
- Always use translate_command() for system commands

### Query Commands
- GRBL/grblHAL use $ prefix
- Marlin uses M-codes (M115, M503, M114)
- Smoothieware supports $ queries in grbl_mode

###7/M8/M9 coolant commands work across all firmware (may require enabling in Marlin)
- M Modal Commands
- Basic G-codes (G0, G1, G20, G21, G90, G91, etc.) are universal
- M3/M4/M5 spindle commands work across all firmware
- Mode persistence handled by firmware

---

## Testing

When adding or modifying firmware support:

1. Test basic operations (move, home, reset)
2. Test realtime commands (pause, resume)
3. Test jogging in both directions
4. Test query commands
5. Test alarm/unlock sequence
6. Verify Z-axis commands (if applicable)

---

## Future Firmware Support

To add new firmware type:

1. Add entry to `command_translations` dictionary in `driver.py`
2. Map all command keys to firmware-specific strings
3. Test all operations
4. Update this documentation
5. Update GUI firmware selection dropdown (if needed)

---

## References

- **GRBL 1.1 Wiki**: https://github.com/gnea/grbl/wiki
- **grblHAL Documentation**: https://github.com/grblHAL/core/wiki
- **Marlin Documentation**: https://marlinfw.org/docs/gcode/
- **Smoothieware Documentation**: https://smoothieware.org/
- **FluidNC Documentation**: https://github.com/bdring/FluidNC

---

## Version History

  - Initial documentation with support for grbl, grblhal, marlin, smoothieware, and custom firmware
  - Added coolant control commands (M7, M8, M9) to all firmware types
- **2026-01-24**: Initial documentation with support for grbl, grblhal, marlin, smoothieware, and custom firmware
