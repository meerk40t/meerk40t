"""
Helper routine for operation info: provides information about op name and associated icon
"""
import wx
from typing import Any, Callable, Dict, Tuple
from meerk40t.gui.icons import (
    icons8_laser_beam,
    icons8_direction,
    icons8_image,
    icons8_laserbeam_weak,
    icon_points,
    icon_effect_hatch,
    icon_effect_wobble,
    icon_distort,
    icons8_home_filled,
    icons8_console,
    icon_timer,
    icon_return,
    icon_external,
    icon_internal,
)

_ = wx.GetTranslation

def get_operation_info() -> Dict[str, Tuple[str, Any, int]]:
    return {
        "op cut": (_("Cut"), icons8_laser_beam, 0),
        "op raster": (_("Raster"), icons8_direction, 0),
        "op image": (_("Image"), icons8_image, 0),
        "op engrave": (_("Engrave"), icons8_laserbeam_weak, 0),
        "op dots": (_("Dots"), icon_points, 0),
        "effect hatch": (_("Hatch"), icon_effect_hatch, 0),
        "effect wobble": (_("Wobble"), icon_effect_wobble, 0),
        "effect warp": (_("Warp"), icon_distort, 0),
        "place current": (_("Jobstart current"), icons8_home_filled, 0),
        "place point": (_("Jobstart at point"), icons8_home_filled, 0),
        "util wait": (_("Wait"), icon_timer, 0),
        "util home": (_("Home"), icons8_home_filled, 0),
        "util goto": (_("Goto"), icon_return, 0),
        "util output": (_("Output"), icon_external, 0),
        "util input": (_("Input"), icon_internal, 0),
        "util console": (_("Command"), icons8_console, 0),
        "generic": (_("Generic"), icons8_console, 0),
    }

