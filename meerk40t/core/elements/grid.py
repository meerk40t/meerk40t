"""
This module provides a set of console commands for managing grid and radial operations within the application.
Users can create grids, radial patterns, and circular copies of elements, allowing for efficient arrangement and manipulation of graphical objects.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up grid commands.
- init_commands(kernel): Initializes the grid commands and defines the associated operations.
- element_grid(command, channel, _, c: int, r: int, x: str, y: str, origin=None, relative=None, data=None, post=None, **kwargs): Creates a grid of elements based on specified rows, columns, and distances.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    c: The number of columns in the grid.
    r: The number of rows in the grid.
    x: The distance between columns.
    y: The distance between rows.
    origin: The origin point for the grid.
    relative: A flag indicating whether distances are relative.
    data: The elements to arrange in the grid.
    post: Additional processing information.
  Returns:
    A tuple containing the type of elements and the created grid elements.
- element_radial(command, channel, _, repeats: int, radius=None, startangle=None, endangle=None, rotate=None, deltaangle=None, data=None, post=None, **kwargs): Creates a radial arrangement of elements based on specified parameters.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    repeats: The number of copies to create.
    radius: The radius of the radial arrangement.
    startangle: The starting angle for the arrangement.
    endangle: The ending angle for the arrangement.
    rotate: A flag indicating whether to rotate copies towards the center.
    deltaangle: The angle increment for each copy.
    data: The elements to arrange radially.
    post: Additional processing information.
  Returns:
    A tuple containing the type of elements and the created radial elements.
- element_circularcopies(command, channel, _, copies: int, radius=None, startangle=None, endangle=None, rotate=None, deltaangle=None, data=None, post=None, **kwargs): Creates circular copies of elements based on specified parameters.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    copies: The number of copies to create.
    radius: The radius of the circular arrangement.
    startangle: The starting angle for the arrangement.
    endangle: The ending angle for the arrangement.
    rotate: A flag indicating whether to rotate copies towards the center.
    deltaangle: The angle increment for each copy.
    data: The elements to arrange circularly.
    post: Additional processing information.
  Returns:
    A tuple containing the type of elements and the created circular elements.
- element_subpath(data=None, post=None, **kwargs): Breaks elements into subpaths, creating separate nodes for each.
  Args:
    data: The elements to break into subpaths.
    post: Additional processing information.
  Returns:
    A tuple containing the type of elements and the created subpath elements.
- operation_empty(channel, _, data=None, data_type=None, **kwargs): Removes all elements from the specified operations.
  Args:
    channel: The communication channel for messages.
    data: The operations to clear.
    data_type: The type of data being processed.
  Returns:
    A tuple containing the type of data and the cleared operations.
- operation_list(command, channel, _, data=None, **kwargs): Lists information about the specified operations.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    data: The operations to list.
  Returns:
    A tuple containing the type of data and the listed operations.
- e_lock(data=None, **kwargs): Locks the specified elements to prevent manipulation.
  Args:
    data: The elements to lock.
  Returns:
    A tuple containing the type of data and the locked elements.
- e_unlock(data=None, **kwargs): Unlocks the specified elements to allow manipulation.
  Args:
    data: The elements to unlock.
  Returns:
    A tuple containing the type of data and the unlocked elements.
- e_copy(data=None, data_type=None, post=None, dx=None, dy=None, copies=None, **kwargs): Duplicates the specified elements a given number of times with optional offsets.
  Args:
    data: The elements to copy.
    data_type: The type of data being processed.
    post: Additional processing information.
    dx: The x-offset for the copies.
    dy: The y-offset for the copies.
    copies: The number of copies to create.
  Returns:
    A tuple containing the type of data and the copied elements.
- e_delete(command, channel, _, data=None, data_type=None, **kwargs): Deletes the specified elements or operations.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    data: The elements or operations to delete.
    data_type: The type of data being processed.
  Returns:
    A tuple containing the type of data and the deleted elements.
"""

from copy import copy
from math import cos, sin, tau

from meerk40t.core.node.node import Node
from meerk40t.core.units import Angle, Length
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import Matrix


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    # ==========
    # GRID SUBTYPE
    # ==========

    @self.console_argument("columns", type=int, help=_("Number of columns"), default=2,)
    @self.console_argument("rows", type=int, help=_("Number of rows"), default=2,)
    @self.console_argument("x_distance", type=str, help=_("x distance"), default="100%")
    @self.console_argument("y_distance", type=str, help=_("y distance"), default="100%")
    @self.console_option(
        "origin",
        "o",
        type=int,
        nargs=2,
        default = (1, 1),
        help=_("Position of original in matrix (e.g '2,2' or '4,3')"),
    )
    @self.console_option(
        "relative",
        "r",
        type=bool,
        action="store_true",
        help=_("Distance not absolute but as relative gap"),
    )
    @self.console_command(
        "grid",
        help=_("grid <columns> <rows> <x_distance> <y_distance> <origin>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_grid(
        command,
        channel,
        _,
        columns: int,
        rows: int,
        x_distance: str,
        y_distance: str,
        origin=None,
        relative=None,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        The grid command wil take the selection and create copies orienting them in a rectangular grid like fashion.
        You can define the amount of rows/columns and how the grid should be orientated around the original elements
        """
        if rows is None:
            raise CommandSyntaxError
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0:
            channel(_("No item selected."))
            return
        if relative is None:
            relative = False
        try:
            bounds = Node.union_bounds(data)
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
        except TypeError:
            raise CommandSyntaxError
        if x_distance is None:
            x_distance = "100%"
        if y_distance is None:
            y_distance = "100%"
        try:
            x_distance = float(Length(x_distance, relative_length=Length(amount=width).length_mm))
            y_distance = float(Length(y_distance, relative_length=Length(amount=height).length_mm))
        except ValueError:
            raise CommandSyntaxError("Length could not be parsed.")
        counted = 0
        # _("Create grid")
        with self.undoscope("Create grid"):
            if relative:
                x_distance += width
                y_distance += height
            if origin is None:
                origin = (1, 1)
            if isinstance(origin, (tuple, list)) and isinstance(origin[0], (tuple, list)):
                origin = origin[0]
            try:
                cx, cy = origin
            except ValueError:
                cx = 1
                cy = 1
            
            data_out = list(data)
            if cx is None:
                cx = 1
            if cy is None:
                cy = 1
            start_x = -1 * x_distance * (cx - 1)
            start_y = -1 * y_distance * (cy - 1)
            y_pos = start_y
            for j in range(rows):
                x_pos = start_x
                for k in range(columns):
                    if j != (cy - 1) or k != (cx - 1):
                        add_elem = list(map(copy, data))
                        for e in add_elem:
                            e.matrix *= Matrix.translate(x_pos, y_pos)
                            self.elem_branch.add_node(e)
                        data_out.extend(add_elem)
                        counted += 1
                    x_pos += x_distance
                y_pos += y_distance
            channel(f"{counted} copies created")
            # Newly created! Classification needed?
            post.append(classify_new(data_out))
            self.signal("refresh_scene", "Scene")
        return "elements", data_out

    @self.console_argument("repeats", type=int, help=_("Number of repeats"), default=3)
    @self.console_argument("radius", type=self.length, help=_("Radius"), default="2cm")
    @self.console_argument("startangle", type=Angle, help=_("Start-Angle"), default="0deg")
    @self.console_argument("endangle", type=Angle, help=_("End-Angle"), default="360deg")
    @self.console_option(
        "unrotated",
        "u",
        type=bool,
        action="store_true",
        help=_("Leave copies unrotated?"),
    )
    @self.console_option(
        "deltaangle",
        "d",
        type=Angle,
        help=_("Delta-Angle (if omitted will take (end-start)/repeats )"),
    )
    @self.console_command(
        "radial",
        help=_("radial <repeats> <radius> <startangle> <endangle> <rotate>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_radial(
        command,
        channel,
        _,
        repeats: int,
        radius=None,
        startangle=None,
        endangle=None,
        unrotated=None,
        deltaangle=None,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Radial copy takes some parameters to create (potentially rotated) copies on a circular arc around a defined center
        Notabene: While circ_copy is creating copies around the original elements, radial is creating all the copies 
        around a center just -1*radius to the left. So the original elements will be part of the circle.
        """
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0 and self._emphasized_bounds is None:
            channel(_("No item selected."))
            return
        if unrotated is None:
            unrotated = False
        rotate = not unrotated
        if repeats is None:
            raise CommandSyntaxError
        if repeats <= 1:
            raise CommandSyntaxError(_("repeats should be greater or equal to 2"))
        if radius is None:
            radius = 0

        if startangle is None:
            startangle = Angle("0deg")
        if endangle is None:
            endangle = Angle("360deg")
        if rotate is None:
            rotate = False

        # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
        bounds = Node.union_bounds(data)
        if bounds is None:
            return
        data_out = list(data)

        segment_len = (endangle - startangle) / repeats if deltaangle is None else deltaangle
        channel(f"Angle per step: {segment_len.angle_degrees}")

        # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
        # the perceived angle travel is CCW (which is counter-intuitive)
        center_x = (bounds[2] + bounds[0]) / 2.0 - radius
        center_y = (bounds[3] + bounds[1]) / 2.0

        # print (f"repeats: {repeats}, Radius: {radius}")
        # print (f"Center: ({center_x}, {center_y})")
        # print (f"Startangle, Endangle, segment_len: {startangle.angle_degrees}, {endangle.angle_degrees}, {segment_len.angle_degrees}")
        images = []
        counted = 0
        # _("Create radial")
        with self.undoscope("Create radial"):
            currentangle = Angle(segment_len)
            for cc in range(1, repeats):
                # print (f"Angle: {currentangle.angle_degrees}")
                add_elem = list(map(copy, data))
                for e in add_elem:
                    if hasattr(e, "as_image"):
                        images.append(e)
                    if rotate:
                        # x_pos = -1 * radius
                        # y_pos = 0
                        # e *= "translate(%f, %f)" % (x_pos, y_pos)
                        e.matrix *= f"rotate({currentangle.angle_preferred}, {center_x}, {center_y})"
                    else:
                        x_pos = -1 * radius + radius * cos(currentangle)
                        y_pos = radius * sin(currentangle)
                        e.matrix *= f"translate({x_pos}, {y_pos})"
                    self.elem_branch.add_node(e)

                counted += 1
                data_out.extend(add_elem)

                currentangle += segment_len
                while (currentangle.angle >= tau):
                    currentangle.angle -= tau
                while (currentangle.angle <= -tau):
                    currentangle.angle += tau
            for e in images:
                self.do_image_update(e)

        channel(f"{counted} copies created")
        # Newly created! Classification needed?
        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    @self.console_argument("copies", type=int, help=_("Number of copies"), default=1)
    @self.console_argument("radius", type=self.length, help=_("Radius"), default="2cm")
    @self.console_argument("startangle", type=Angle, help=_("Start-Angle"), default="0deg")
    @self.console_argument("endangle", type=Angle, help=_("End-Angle"), default="360deg")
    @self.console_option(
        "rotate",
        "r",
        type=bool,
        action="store_true",
        help=_("Rotate copies towards center?"),
        default=False,
    )
    @self.console_option(
        "deltaangle",
        "d",
        type=Angle,
        help=_("Delta-Angle (if omitted will take (end-start)/copies )"),
    )
    @self.console_command(
        "circ_copy",
        help=_("circ_copy <copies> <radius> <startangle> <endangle> <rotate>"),
        input_type=(None, "elements"),
        output_type="elements",
    )
    def element_circularcopies(
        command,
        channel,
        _,
        copies: int,
        radius=None,
        startangle=None,
        endangle=None,
        rotate=None,
        deltaangle=None,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Circular copy takes some parameters to create (potentially rotated) copies on a circular arc around the orginal element(s)
        Notabene: While circ_copy is creating copies around the original elements, radial is creating all the copies 
        around a center just -1*radius to the left. So the original elements will be part of the circle.
        """
        if data is None:
            data = list(self.elems(emphasized=True))
        if len(data) == 0 and self._emphasized_bounds is None:
            channel(_("No item selected."))
            return

        if copies is None:
            raise CommandSyntaxError
        if copies <= 0:
            copies = 1
        if radius is None:
            radius = 0

        if startangle is None:
            startangle = Angle("0deg")
        if endangle is None:
            endangle = Angle("360deg")
        if rotate is None:
            rotate = False

        # print ("Segment to cover: %f - %f" % (startangle.as_degrees, endangle.as_degrees))
        bounds = Node.union_bounds(data)
        if bounds is None:
            return
        # width = bounds[2] - bounds[0]

        data_out = list(data)
        if deltaangle is None:
            segment_len = (endangle - startangle) / copies
        else:
            segment_len = deltaangle
        # Notabene: we are following the cartesian system here, but as the Y-Axis is top screen to bottom screen,
        # the perceived angle travel is CCW (which is counter-intuitive)
        currentangle = Angle(startangle)
        # bounds = self._emphasized_bounds
        center_x = (bounds[2] + bounds[0]) / 2.0
        center_y = (bounds[3] + bounds[1]) / 2.0
        images = []
        counted = 0
        # _("Create circular copy")
        with self.undoscope("Create circular copy"):
            for cc in range(copies):
                # print ("Angle: %f rad = %f deg" % (currentangle, currentangle/pi * 180))
                add_elem = list(map(copy, data))
                for e in add_elem:
                    if hasattr(e, "as_image"):
                        images.append(e)
                    if rotate:
                        x_pos = radius
                        y_pos = 0
                        e.matrix *= f"translate({x_pos}, {y_pos})"
                        e.matrix *= f"rotate({currentangle.angle_preferred}, {center_x}, {center_y})"
                        e.modified()
                        if hasattr(e, "update"):
                            images.append(e)
                    else:
                        x_pos = radius * cos(currentangle)
                        y_pos = radius * sin(currentangle)
                        e.matrix *= f"translate({x_pos}, {y_pos})"
                        e.translated(x_pos, y_pos)
                    self.elem_branch.add_node(e)
                counted += 1
                data_out.extend(add_elem)
                currentangle += segment_len
                while (currentangle.angle >= tau):
                    currentangle.angle -= tau
                while (currentangle.angle <= -tau):
                    currentangle.angle += tau
            for e in images:
                self.do_image_update(e)
        channel(f"{counted} copies created")

        post.append(classify_new(data_out))
        self.signal("refresh_scene", "Scene")
        return "elements", data_out

    # --------------------------- END COMMANDS ------------------------------
