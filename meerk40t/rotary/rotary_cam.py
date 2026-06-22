"""
Rotary CAM helpers — circumference, steps compensation, and layout math.

Used when the Y motor drives a chuck-style rotary (Y-axis swap on GRBL).
"""

import math

from meerk40t.core.units import Length


def circumference_mm(diameter_mm: float) -> float:
    if diameter_mm <= 0:
        return 0.0
    return math.pi * diameter_mm


def y_steps_factor(flat_y_steps_per_mm: float, rotary_y_steps_per_mm: float) -> float:
    """
    Scale Y coordinates sent to GRBL when firmware $101 still matches the flat-bed
    gantry motor but a different rotary motor is wired to the Y driver.

    y_grbl = y_design * (flat_steps / rotary_steps)
    """
    if rotary_y_steps_per_mm <= 0:
        return 1.0
    if flat_y_steps_per_mm <= 0:
        return 1.0
    return flat_y_steps_per_mm / rotary_y_steps_per_mm


def calibrate_rotary_steps(
    current_steps_per_mm: float, commanded_mm: float, measured_mm: float
) -> float:
    """Adjust rotary steps/mm after a test line (commanded vs measured)."""
    if measured_mm <= 0 or commanded_mm <= 0:
        return current_steps_per_mm
    return current_steps_per_mm * (commanded_mm / measured_mm)


def suggest_rotary_steps_per_mm(
    motor_steps_per_rev: int,
    microsteps: int,
    gear_ratio: float,
    diameter_mm: float,
) -> float:
    """
    Estimate GRBL $101 for a chuck rotary: steps per mm of surface travel
  around the cylinder (one full turn = pi * diameter mm).
    """
    if diameter_mm <= 0 or gear_ratio <= 0:
        return 0.0
    steps_per_rev = motor_steps_per_rev * microsteps * gear_ratio
    circ = circumference_mm(diameter_mm)
    if circ <= 0:
        return 0.0
    return steps_per_rev / circ


def wrap_scale_y(diameter_mm: float, bed_height_mm: float) -> float:
    """Scene bed height -> one object circumference along Y."""
    circ = circumference_mm(diameter_mm)
    if bed_height_mm <= 0 or circ <= 0:
        return 1.0
    return circ / bed_height_mm


def length_scale_x(object_length_mm: float, bed_width_mm: float) -> float:
    """Scene bed width -> usable object length along X."""
    if bed_width_mm <= 0 or object_length_mm <= 0:
        return 1.0
    return object_length_mm / bed_width_mm


def bed_length_mm(service) -> float:
    try:
        return float(Length(service.bedwidth))
    except (AttributeError, ValueError, TypeError):
        return 0.0


def bed_height_mm(service) -> float:
    try:
        return float(Length(service.bedheight))
    except (AttributeError, ValueError, TypeError):
        return 0.0
