"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""

from meerk40t.core.units import Angle as UAngle
from meerk40t.core.units import Length


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    # ==========
    # PLACEMENTS
    # ==========

    @self.console_option("rotation", "r", type=UAngle, help=_("placement rotation"), default=0)
    @self.console_option("corner", "c", type=int, help=_("placement corner (0=TL, 1=TR, 2=BR, 3=BL, 4=center)"), default=-1)
    @self.console_argument("x", type=Length, help=_("x coord"))
    @self.console_argument("y", type=Length, help=_("y coord"))
    @self.console_command(
        "placement",
        help=_("points *"),
        input_type=None,
        output_type="ops",
        all_arguments_required=True,
    )
    def place_points(command, channel, _, x, y, rotation, corner, **kwargs):
        added = []
        node = self.op_branch.add(x=x, y=y, rotation=rotation.radians, corner=corner, type="place point")
        added.append(node)
        self.set_emphasis(added)
        return "ops", added

    @self.console_command(
        "current_position",
        help=_("adds a current position placement"),
        input_type=None,
        output_type="ops",
        all_arguments_required=True,
    )
    def place_current(command, channel, _, **kwargs):
        node = self.op_branch.add(type="place current")
        added = [node]
        self.set_emphasis(added)
        return "ops", added

    # --------------------------- END COMMANDS ------------------------------
