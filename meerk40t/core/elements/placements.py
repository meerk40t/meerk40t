"""
This module provides a set of console commands for managing placements within the application.
Users can create fixed job start positions, add relative placements,
and manipulate the arrangement of placements in a grid pattern.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up placement commands.
- init_commands(kernel): Initializes the placement commands and defines the associated operations.
- place_points(command, channel, _, x=None, y=None, nx=None, ny=None, dx=None, dy=None, rotation=None, corner=None, loops=None, **kwargs): Adds a placement at a specified position with optional repetitions and gaps.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    x: The x-coordinate for the placement.
    y: The y-coordinate for the placement.
    nx: The number of placements on the x-axis.
    ny: The number of placements on the y-axis.
    dx: The gap in the x-direction.
    dy: The gap in the y-direction.
    rotation: The rotation angle for the placement.
    corner: The corner position for the placement.
    loops: The number of placement repetitions.
  Returns:
    A tuple containing the type of operations and the added placements.
- place_current(command, channel, _, **kwargs): Adds a relative job start position at the current laser position.
  Args:
    command: The command context.
    channel: The communication channel for messages.
  Returns:
    A tuple containing the type of operations and the added placement.
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

    @self.console_option(
        "loops", "l", type=int, help=_("placement repetitions"), default=0
    )
    @self.console_option(
        "rotation", "r", type=UAngle, help=_("placement rotation"), default=0
    )
    @self.console_option(
        "corner",
        "c",
        type=int,
        help=_("placement corner (0=TL, 1=TR, 2=BR, 3=BL, 4=center)"),
        default=-1,
    )
    @self.console_option(
        "nx",
        "s",
        type=int,
        help=_("How many placements on the X-Axis?\n(0 = as many as fit on the bed)"),
    )
    @self.console_option(
        "ny",
        "t",
        type=int,
        help=_("How many placements on the Y-Axis?\n(0 = as many as fit on the bed)"),
    )
    @self.console_option("dx", "m", type=Length, help=_("Gap in x-direction"))
    @self.console_option("dy", "n", type=Length, help=_("Gap in y-direction"))
    @self.console_argument("x", type=Length, help=_("x coord"))
    @self.console_argument("y", type=Length, help=_("y coord"))
    @self.console_command(
        "placement",
        help=_("Adds a placement = a fixed job start position"),
        input_type=None,
        output_type="ops",
        all_arguments_required=True,
    )
    def place_points(
        command,
        channel,
        _,
        x=None,
        y=None,
        nx=None,
        ny=None,
        dx=None,
        dy=None,
        rotation=None,
        corner=None,
        loops=None,
        **kwargs,
    ):
        if loops is None:
            loops = 1
        if corner is None:
            corner = 0
        if rotation is None:
            rotation = 0
        if x is None:
            x = 0
        if y is None:
            y = x
        if nx is None:
            nx = 1
        if ny is None:
            ny = 1
        if dx is None:
            dx = 0
            nx = 1
        if dy is None:
            dy = 0
            ny = 1
        try:
            x = Length(x)
            y = Length(y)
            len_dx = Length(dx)
            dx_val = float(len_dx)
            len_dy = Length(dy)
            dy_val = float(len_dy)
        except ValueError:
            channel(_("Invalid values given"))
            return
        if nx < 0 or ny < 0:
            channel(_("Invalid values for nx/ny provided"))
            return
        try:
            nx = int(nx)
            ny = int(ny)
        except ValueError:
            channel(_("Invalid values for nx/ny provided"))
            return
        added = []
        # print (f"x={x}, y={y}, nx={nx}, ny={ny}, dx={dx}, dy={dy}, rotation={rotation}, corner={corner}, loops={loops}")
        node = self.op_branch.add(
            x=x,
            y=y,
            nx=nx,
            ny=ny,
            dx=dx,
            dy=dy,
            rotation=rotation.radians,
            corner=corner,
            loops=loops,
            type="place point",
        )
        added.append(node)
        self.set_emphasis(added)
        return "ops", added

    @self.console_command(
        "current_position",
        help=_("Adds a relative job start position (at the current laser position)"),
        input_type=None,
        output_type="ops",
        all_arguments_required=True,
    )
    def place_current(command, channel, _, **kwargs):
        node = self.op_branch.add(type="place current")
        added = [node]
        self.set_emphasis(added)
        return "ops", added

    # @self.console_argument("nx", type=int, help=_("How many placements on the X-Axis?\n(0 = as many as fit on the bed)"))
    # @self.console_argument("dx", type=Length, help=_("Gap in x-direction"))
    # @self.console_argument("ny", type=int, help=_("How many placements on the Y-Axis?\n(0 = as many as fit on the bed)"))
    # @self.console_argument("dy", type=Length, help=_("Gap in y-direction"))
    # @self.console_command(
    #     "placement_repeat",
    #     help=_("Repeat placements in a grid orientation"),
    #     input_type=None,
    #     output_type="ops",
    #     all_arguments_required=True,
    # )
    # def place_repeat(command, channel, _, nx=None, dx=None, ny=None, dy=None, **kwargs):
    #     data = []
    #     for n in list(self.ops(selected=True)):
    #         if n.type == "place point":
    #             data.append(n)
    #     if len(data) == 0:
    #         channel(_("No placements selected"))
    #         return
    #     if dx is None or dx == "":
    #         channel(_("No placements selected"))
    #         return
    #     if dy is None or dy == "":
    #         return
    #     try:
    #         len_dx = Length(dx)
    #         dx_val = float(len_dx)
    #         len_dy = Length(dy)
    #         dy_val = float(len_dy)
    #     except ValueError:
    #         channel(_("Invalid values for dx and/or dy"))
    #         return
    #     if nx is None or nx < 0 or ny is None or ny < 0:
    #         channel(_("Invalid values for nx/ny provided"))
    #         return
    #     try:
    #         nx = int(nx)
    #         ny = int(ny)
    #     except ValueError:
    #         channel(_("Invalid values for nx/ny provided"))
    #         return
    #     if nx == 1 and ny == 1:
    #         channel(_("Nothing to do."))
    #         return

    #     ops = []
    #     max_x = self.device.view.width
    #     max_y = self.device.view.height
    #     pos = None
    #     for pnode in data:
    #         corner = pnode.corner
    #         rotation = pnode.rotation
    #         idx_x = 0
    #         idx_y = 0
    #         starty = pnode.y
    #         if ny == 0:
    #             while starty < max_y:
    #                 startx = pnode.x
    #                 idx_x = 0
    #                 if nx == 0:
    #                     while startx < max_x:
    #                         if idx_x != 0 or idx_y != 0:
    #                             op = self.op_branch.add(
    #                                 type="place point",
    #                                 pos=pos,
    #                                 x=startx,
    #                                 y=starty,
    #                                 rotation=rotation,
    #                                 corner=corner,
    #                             )
    #                             ops.append(op)
    #                         startx += dx_val
    #                         idx_x += 1
    #                 else:
    #                     for idx in range(nx):
    #                         if idx_x != 0 or idx_y != 0:
    #                             op = self.op_branch.add(
    #                                 type="place point",
    #                                 pos=pos,
    #                                 x=startx,
    #                                 y=starty,
    #                                 rotation=rotation,
    #                                 corner=corner,
    #                             )
    #                             ops.append(op)
    #                         startx += dx_val
    #                         idx_x += 1
    #         else:
    #             for idx in range(ny):
    #                 startx = pnode.x
    #                 idx_x = 0
    #                 if nx == 0:
    #                     while startx < max_x:
    #                         if idx_x != 0 or idx_y != 0:
    #                             op = self.op_branch.add(
    #                                 type="place point",
    #                                 pos=pos,
    #                                 x=startx,
    #                                 y=starty,
    #                                 rotation=rotation,
    #                                 corner=corner,
    #                             )
    #                             ops.append(op)
    #                         startx += dx_val
    #                         idx_x += 1
    #                 else:
    #                     for idx in range(nx):
    #                         if idx_x != 0 or idx_y != 0:
    #                             op = self.op_branch.add(
    #                                 type="place point",
    #                                 pos=pos,
    #                                 x=startx,
    #                                 y=starty,
    #                                 rotation=rotation,
    #                                 corner=corner,
    #                             )
    #                             ops.append(op)
    #                         startx += dx_val
    #                         idx_x += 1

    #                 starty += dy_val
    #                 idx_y += 1

    #     self.signal("updateop_tree")
    #     self.signal("refresh_scene", "Scene")
    #     return "ops", ops

    # --------------------------- END COMMANDS ------------------------------
