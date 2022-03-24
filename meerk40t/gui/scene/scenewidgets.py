import math

import wx

from meerk40t.gui.laserrender import (
    DRAW_MODE_BACKGROUND,
    DRAW_MODE_GRID,
    DRAW_MODE_GUIDES,
    DRAW_MODE_LASERPATH,
    DRAW_MODE_RETICLE,
    DRAW_MODE_SELECTION,
    swizzlecolor,
)
from meerk40t.gui.scene.scene import Widget
from meerk40t.gui.wxutils import create_menu
from meerk40t.svgelements import Color

MILS_IN_MM = 39.3701

HITCHAIN_HIT = 0
HITCHAIN_DELEGATE = 1
HITCHAIN_HIT_AND_DELEGATE = 2
HITCHAIN_DELEGATE_AND_HIT = 3

RESPONSE_CONSUME = 0
RESPONSE_ABORT = 1
RESPONSE_CHAIN = 2
RESPONSE_DROP = 3

ORIENTATION_MODE_MASK = 0b00001111110000
ORIENTATION_DIM_MASK = 0b00000000001111
ORIENTATION_MASK = ORIENTATION_MODE_MASK | ORIENTATION_DIM_MASK
ORIENTATION_RELATIVE = 0b00000000000000
ORIENTATION_ABSOLUTE = 0b00000000010000
ORIENTATION_CENTERED = 0b00000000100000
ORIENTATION_HORIZONTAL = 0b00000001000000
ORIENTATION_VERTICAL = 0b00000010000000
ORIENTATION_GRID = 0b00000100000000
ORIENTATION_NO_BUFFER = 0b00001000000000
BUFFER = 10.0


class ElementsWidget(Widget):
    """
    The ElementsWidget is tasked with drawing the elements within the scene. It also
    server to process leftclick in order to emphasize the given object.
    """

    def __init__(self, scene, renderer):
        Widget.__init__(self, scene, all=True)
        self.renderer = renderer

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc):
        context = self.scene.context
        matrix = self.scene.widget_root.scene_widget.matrix
        scale_x = matrix.value_scale_x()
        try:
            zoom_scale = 1 / scale_x
        except ZeroDivisionError:
            matrix.reset()
            zoom_scale = 1
        if zoom_scale < 1:
            zoom_scale = 1
        self.renderer.render(
            context.elements.elems_nodes(),
            gc,
            self.renderer.context.draw_mode,
            zoomscale=zoom_scale,
        )

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftclick":
            elements = self.scene.context.elements
            elements.set_emphasized_by_position(space_pos)
            self.scene.context.signal("select_emphasized_tree", 0)
            return RESPONSE_CONSUME
        return RESPONSE_DROP


class SelectionWidget(Widget):
    """
    Selection Widget it tasked with drawing the selection box and managing the events
    dealing with moving, resizing and altering the selected object.
    """

    # Size of rotation indicator area - will be multiplied by selbox_wx / selbox_wy respectively
    rot_area = 2
    use_handle_rotate = True
    use_handle_skew = True
    use_handle_size = True
    selbox_wx = None
    selbox_wy = None
    rotate_cx = None
    rotate_cy = None
    rotated_angle = 0

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.elements = scene.context.elements
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(wx.Colour(0xA0, 0x7F, 0xA0))
        self.selection_pen.SetStyle(wx.PENSTYLE_DOT)
        self.save_width = None
        self.save_height = None
        self.tool = self.tool_translate
        self.cursor = None
        self.uniform = True
        self.total_delta_x = 0
        self.total_delta_y = 0
        self.tool_running = False
        self.arcsegment = None

    def hit(self):
        elements = self.elements
        bounds = elements.selected_area()
        if bounds is not None:
            self.left = bounds[0]
            self.top = bounds[1]
            self.right = bounds[2]
            self.bottom = bounds[3]

            # Adjust boundaries to ensure a minimum height / width so that
            # dots and horizontal / vertical lines get a move icon
            width = self.right - self.left
            height = self.bottom - self.top
            matrix = self.parent.matrix
            # Twice size of equivalent in event:hover
            try:
                xmin = 10 / matrix.value_scale_x()
                ymin = 10 / matrix.value_scale_y()
            except ZeroDivisionError:
                matrix.reset()
                ymin = 10
                xmin = 10
            if width < xmin:
                width = (xmin - width) / 2
                self.left -= width
                self.right += width
            if height < ymin:
                height = (ymin - height) / 2
                self.top -= height
                self.bottom += height

            self.clear()
            return HITCHAIN_HIT
        else:
            self.left = float("inf")
            self.top = float("inf")
            self.right = -float("inf")
            self.bottom = -float("inf")
            self.clear()
            return HITCHAIN_DELEGATE

    def contains(self, x, y=None):
        """
        Query as to whether the current point is contained within the current widget.
        Overloaded routine to allow for selection rectangle size
        """
        valu = False
        if y is None:
            y = x.y
            x = x.x
        if self.selbox_wx is None:
            matrix = self.parent.matrix
            self.selbox_wx = 10.0 / matrix.value_scale_x()
            self.selbox_wy = 10.0 / matrix.value_scale_y()

        checks = [[self.left, self.top, self.right, self.bottom]]
        # The 4 side handles
        if self.use_handle_size:
            checks.append(
                [
                    self.left - self.selbox_wx / 2,
                    (self.top + self.bottom) / 2 - self.selbox_wy / 2,
                    self.left,
                    (self.top + self.bottom) / 2 + self.selbox_wy / 2,
                ]
            )
            checks.append(
                [
                    self.right,
                    (self.top + self.bottom) / 2 - self.selbox_wy / 2,
                    self.right + self.selbox_wx / 2,
                    (self.top + self.bottom) / 2 + self.selbox_wy / 2,
                ]
            )
            checks.append(
                [
                    (self.left + self.right) / 2 - self.selbox_wx / 2,
                    self.top - self.selbox_wy / 2,
                    (self.left + self.right) / 2 + self.selbox_wx / 2,
                    self.top,
                ]
            )
            checks.append(
                [
                    (self.left + self.right) / 2 - self.selbox_wx / 2,
                    self.bottom,
                    (self.left + self.right) / 2 + self.selbox_wx / 2,
                    self.bottom + self.selbox_wy / 2,
                ]
            )

        # The 4 corner handles incl. rotation indicator
        if self.use_handle_rotate:
            h_factor = self.rot_area
        else:
            h_factor = 0.5
        checks.append(
            [
                self.left - h_factor * self.selbox_wx,
                self.top - h_factor * self.selbox_wy,
                self.left + h_factor * self.selbox_wx,
                self.top + h_factor * self.selbox_wy,
            ]
        )
        checks.append(
            [
                self.right - h_factor * self.selbox_wx,
                self.top - h_factor * self.selbox_wy,
                self.right + h_factor * self.selbox_wx,
                self.top + h_factor * self.selbox_wy,
            ]
        )
        checks.append(
            [
                self.left - h_factor * self.selbox_wx,
                self.bottom - h_factor * self.selbox_wy,
                self.left + h_factor * self.selbox_wx,
                self.bottom + h_factor * self.selbox_wy,
            ]
        )
        checks.append(
            [
                self.right - h_factor * self.selbox_wx,
                self.bottom - h_factor * self.selbox_wy,
                self.right + h_factor * self.selbox_wx,
                self.bottom + h_factor * self.selbox_wy,
            ]
        )
        if self.use_handle_skew:
            # The two skew handles
            checks.append(
                [
                    self.left
                    + 3 / 4 * (self.right - self.left)
                    - 1 / 3 * self.selbox_wx,
                    self.bottom - 1 / 3 * self.selbox_wy,
                    self.left
                    + 3 / 4 * (self.right - self.left)
                    + 1 / 3 * self.selbox_wx,
                    self.bottom + 1 / 3 * self.selbox_wy,
                ]
            )
            checks.append(
                [
                    self.right - 1 / 3 * self.selbox_wx,
                    self.top
                    + 1 / 4 * (self.bottom - self.top)
                    - 1 / 3 * self.selbox_wy,
                    self.right + 1 / 3 * self.selbox_wx,
                    self.top
                    + 1 / 4 * (self.bottom - self.top)
                    + 1 / 3 * self.selbox_wy,
                ]
            )

        # Check whether the given point lie within one of the relevant rectangles
        for crn in checks:
            if crn[0] <= x <= crn[2] and crn[1] <= y <= crn[3]:
                valu = True
                break
        return valu

    key_shift_pressed = False
    key_control_pressed = False
    key_alt_pressed = False
    was_lb_raised = False
    hovering = False
    # debug_msg = ""

    def stillinside(self, space_pos=None):
        res = False
        matrix = self.parent.matrix
        if not space_pos is None:
            sx = space_pos[0]
            sy = space_pos[1]
            # print ("left=%f, right=%f, top=%f, bottom=%f, x=%f, y=%f" % (self.left, self.right, self.top, self.bottom, sx, sy))

            if self.contains(sx, sy):
                # print ("inside")
                res = True
        return res

    store_last_msg = ""

    def update_statusmsg(self, value):
        if value != self.store_last_msg:
            self.store_last_msg = value
            self.scene.context.signal("statusmsg", value)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        _ = self.scene.context._

        elements = self.elements

        # sdbg = event_type
        # if sdbg in ("hover_start", "hover_end", "hover"):
        #    sdbg = "hover"
        # if sdbg != self.debug_msg:
        #    self.debug_msg = sdbg
        #    print(
        #        "Selection-Event: %s (current state: %s)"
        #        % (event_type, self.was_lb_raised)
        #    )
        if event_type == "kb_shift_release":
            if self.key_shift_pressed:
                self.key_shift_pressed = False
                if not self.tool_running and self.stillinside(space_pos):
                    self.scene.cursor("sizing")
                    self.hovering = True
                    self.tool = self.tool_translate
            return RESPONSE_CHAIN
        elif event_type == "kb_shift_press":
            if not self.key_shift_pressed:
                self.key_shift_pressed = True
            # Are we hovering ? If yes reset cursor
            if not self.tool_running and self.hovering:
                self.hovering = False
                self.scene.cursor("arrow")
            return RESPONSE_CHAIN
        elif event_type == "kb_ctrl_release":
            if self.key_control_pressed:
                self.key_control_pressed = False
                if not self.tool_running and self.stillinside(space_pos):
                    self.scene.cursor("sizing")
                    self.hovering = True
                    self.tool = self.tool_translate
            return RESPONSE_CHAIN
        elif event_type == "kb_ctrl_press":
            if not self.key_control_pressed:
                self.key_control_pressed = True
            # Are we hovering ? If yes reset cursor
            if not self.tool_running and self.hovering:
                self.hovering = False
                self.scene.cursor("arrow")
            return RESPONSE_CHAIN
        elif event_type == "kb_alt_release":
            if self.key_alt_pressed:
                self.key_alt_pressed = False
            return RESPONSE_CHAIN
        elif event_type == "kb_alt_press":
            if not self.key_alt_pressed:
                self.key_alt_pressed = True
            return RESPONSE_CHAIN
        elif event_type == "hover_start":
            self.scene.cursor("sizing")
            self.hovering = True
            return RESPONSE_CHAIN
        elif event_type == "hover_end" or event_type == "lost":
            self.scene.cursor("arrow")
            self.hovering = False
            self.update_statusmsg(_("Status"))

            return RESPONSE_CHAIN
        elif event_type == "hover":
            if self.hovering:
                matrix = self.parent.matrix

                # No need for a minimum coverage check as we are testing for (a rather big) are in the center first, so if the handles overlap then move has priority
                xmin = self.left
                xmax = self.right
                ymin = self.top
                ymax = self.bottom
                xin = space_pos[0]
                yin = space_pos[1]

                # If there is at least on element in the selection with a lock status, then the only manipulation we allow is a move operation
                for e in elements.elems(emphasized=True):
                    try:
                        if e.lock:
                            self.scene.cursor("sizing")
                            self.tool = self.tool_translate
                            return RESPONSE_CHAIN
                    except (ValueError, AttributeError):
                        pass

                if (self.width < 3 * self.selbox_wx) or (
                    self.height < 3 * self.selbox_wy
                ):
                    center_size = 1
                elif (self.width < 5 * self.selbox_wx) or (
                    self.height < 5 * self.selbox_wy
                ):
                    center_size = 2
                else:
                    center_size = 3
                # print("Ratio-Y: %.1f, X: %.1f, cs=%d" % (self.width / self.selbox_wx, self.height / self.selbox_wy, center_size))
                # The centre for moving
                checks = [
                    [
                        (xmin + xmax) / 2 - center_size * self.selbox_wx,
                        (ymin + ymax) / 2 - center_size * self.selbox_wy,
                        (xmin + xmax) / 2 + center_size * self.selbox_wx,
                        (ymin + ymax) / 2 + center_size * self.selbox_wy,
                        "move",
                    ]
                ]
                # The 4 side handles for resizing
                checks.append(
                    [
                        xmin - self.selbox_wx / 2,
                        (ymin + ymax) / 2 - self.selbox_wy / 2,
                        xmin + self.selbox_wx / 2,
                        (ymin + ymax) / 2 + self.selbox_wy / 2,
                        "size_l",
                    ]
                )
                checks.append(
                    [
                        xmax - self.selbox_wx / 2,
                        (ymin + ymax) / 2 - self.selbox_wy / 2,
                        xmax + self.selbox_wx / 2,
                        (ymin + ymax) / 2 + self.selbox_wy / 2,
                        "size_r",
                    ]
                )
                checks.append(
                    [
                        (xmin + xmax) / 2 - self.selbox_wx / 2,
                        ymin - self.selbox_wy / 2,
                        (xmin + xmax) / 2 + self.selbox_wx / 2,
                        ymin + self.selbox_wy / 2,
                        "size_t",
                    ]
                )
                checks.append(
                    [
                        (xmin + xmax) / 2 - self.selbox_wx / 2,
                        ymax - self.selbox_wy / 2,
                        (xmin + xmax) / 2 + self.selbox_wx / 2,
                        ymax + self.selbox_wy / 2,
                        "size_b",
                    ]
                )
                # The 4 corner handles (need to come before rotation)
                checks.append(
                    [
                        xmin - self.selbox_wx / 2,
                        ymin - self.selbox_wy / 2,
                        xmin + self.selbox_wx / 2,
                        ymin + self.selbox_wy / 2,
                        "size_tl",
                    ]
                )
                checks.append(
                    [
                        xmax - self.selbox_wx / 2,
                        ymin - self.selbox_wy / 2,
                        xmax + self.selbox_wx / 2,
                        ymin + self.selbox_wy / 2,
                        "size_tr",
                    ]
                )
                checks.append(
                    [
                        xmin - self.selbox_wx / 2,
                        ymax - self.selbox_wy / 2,
                        xmin + self.selbox_wx / 2,
                        ymax + self.selbox_wy / 2,
                        "size_bl",
                    ]
                )
                checks.append(
                    [
                        xmax - self.selbox_wx / 2,
                        ymax - self.selbox_wy / 2,
                        xmax + self.selbox_wx / 2,
                        ymax + self.selbox_wy / 2,
                        "size_br",
                    ]
                )

                if self.use_handle_rotate:
                    # The 4 rotation areas for inner coverage first
                    checks.append(
                        [
                            xmin,
                            ymin,
                            xmin + self.rot_area * self.selbox_wx,
                            ymin + self.rot_area * self.selbox_wy,
                            "rotate_inner_tl",
                        ]
                    )
                    checks.append(
                        [
                            xmax - self.rot_area * self.selbox_wx,
                            ymin,
                            xmax,
                            ymin + self.rot_area * self.selbox_wy,
                            "rotate_inner_tr",
                        ]
                    )
                    checks.append(
                        [
                            xmin,
                            ymax - self.rot_area * self.selbox_wy,
                            xmin + self.rot_area * self.selbox_wx,
                            ymax,
                            "rotate_inner_bl",
                        ]
                    )
                    checks.append(
                        [
                            xmax - self.rot_area * self.selbox_wx,
                            ymax - self.rot_area * self.selbox_wy,
                            xmax,
                            ymax,
                            "rotate_inner_br",
                        ]
                    )
                    # The 4 wider areas around the corner handles incl. rotation indicator
                    checks.append(
                        [
                            xmin - self.rot_area * self.selbox_wx,
                            ymin - self.rot_area * self.selbox_wy,
                            xmin + self.rot_area * self.selbox_wx,
                            ymin + self.rot_area * self.selbox_wy,
                            "rotate_outer_tl",
                        ]
                    )
                    checks.append(
                        [
                            xmax - self.rot_area * self.selbox_wx,
                            ymin - self.rot_area * self.selbox_wy,
                            xmax + self.rot_area * self.selbox_wx,
                            ymin + self.rot_area * self.selbox_wy,
                            "rotate_outer_tr",
                        ]
                    )
                    checks.append(
                        [
                            xmin - self.rot_area * self.selbox_wx,
                            ymax - self.rot_area * self.selbox_wy,
                            xmin + self.rot_area * self.selbox_wx,
                            ymax + self.rot_area * self.selbox_wy,
                            "rotate_outer_bl",
                        ]
                    )
                    checks.append(
                        [
                            xmax - self.rot_area * self.selbox_wx,
                            ymax - self.rot_area * self.selbox_wy,
                            xmax + self.rot_area * self.selbox_wx,
                            ymax + self.rot_area * self.selbox_wy,
                            "rotate_outer_br",
                        ]
                    )
                if self.use_handle_skew:
                    # The two skew handles
                    checks.append(
                        [
                            xmin + 3 / 4 * (xmax - xmin) - 1 / 3 * self.selbox_wx,
                            ymax - 1 / 3 * self.selbox_wy,
                            xmin + 3 / 4 * (xmax - xmin) + 1 / 3 * self.selbox_wx,
                            ymax + 1 / 3 * self.selbox_wy,
                            "skew_x",
                        ]
                    )
                    checks.append(
                        [
                            xmax - 1 / 3 * self.selbox_wx,
                            ymin + 1 / 4 * (ymax - ymin) - 1 / 3 * self.selbox_wy,
                            xmax + 1 / 3 * self.selbox_wx,
                            ymin + 1 / 4 * (ymax - ymin) + 1 / 3 * self.selbox_wy,
                            "skew_y",
                        ]
                    )

                method = ""
                # Check whether the given point lies within one of the relevant rectangles
                for crn in checks:
                    # print("Checking method: %s for (%.1f, %.1f) vs (%.1f, %.1f, %.1f, %.1f)" % ( crn[4], xin, yin, crn[0], crn[1], crn[2], crn[3]))
                    if crn[0] <= xin <= crn[2] and crn[1] <= yin <= crn[3]:
                        method = crn[4]
                        break
                # print ("Method found: %s" % method)
                if method == "move":
                    self.scene.cursor("sizing")
                    self.tool = self.tool_translate
                    self.update_statusmsg(_("Move element"))
                elif method == "size_tl":
                    self.scene.cursor("size_nw")
                    self.tool = self.tool_scalexy_nw
                    self.update_statusmsg(_("Scale element"))
                elif method == "size_tr":
                    self.scene.cursor("size_ne")
                    self.tool = self.tool_scalexy_ne
                    self.update_statusmsg(_("Scale element"))
                elif method == "size_bl":
                    self.scene.cursor("size_sw")
                    self.tool = self.tool_scalexy_sw
                    self.update_statusmsg(_("Scale element"))
                elif method == "size_br":
                    self.scene.cursor("size_se")
                    self.tool = self.tool_scalexy_se
                    self.update_statusmsg(_("Scale element"))
                elif method == "size_l":
                    self.scene.cursor("size_w")
                    self.tool = self.tool_scalex_w
                    self.update_statusmsg(_("Scale element in X-direction"))
                elif method == "size_r":
                    self.scene.cursor("size_e")
                    self.tool = self.tool_scalex_e
                    self.update_statusmsg(_("Scale element in X-direction"))
                elif method == "size_b":
                    self.scene.cursor("size_s")
                    self.tool = self.tool_scaley_s
                    self.update_statusmsg(_("Scale element in Y-direction"))
                elif method == "size_t":
                    self.scene.cursor("size_n")
                    self.tool = self.tool_scaley_n
                    self.update_statusmsg(_("Scale element in Y-direction"))
                elif method == "skew_x":
                    self.scene.cursor("size_ew")
                    self.tool = self.tool_skew_x
                    self.update_statusmsg(_("Skew element in X-direction"))
                elif method == "skew_y":
                    self.scene.cursor("size_ns")
                    self.tool = self.tool_skew_y
                    self.update_statusmsg(_("Skew element in Y-direction"))
                elif method == "rotate_outer_tl":
                    self.rotate_cx = (self.right + self.left) / 2
                    self.rotate_cy = (self.top + self.bottom) / 2
                    self.scene.cursor("rotate1")
                    self.tool = self.tool_rotate
                    self.update_statusmsg(_("Rotate around center"))
                elif method == "rotate_outer_tr":
                    self.rotate_cx = (self.right + self.left) / 2
                    self.rotate_cy = (self.top + self.bottom) / 2
                    self.scene.cursor("rotate1")
                    self.tool = self.tool_rotate
                    self.update_statusmsg(_("Rotate around center"))
                elif method == "rotate_outer_bl":
                    self.rotate_cx = (self.right + self.left) / 2
                    self.rotate_cy = (self.top + self.bottom) / 2
                    self.scene.cursor("rotate1")
                    self.tool = self.tool_rotate
                    self.update_statusmsg(_("Rotate around center"))
                elif method == "rotate_outer_br":
                    self.rotate_cx = (self.right + self.left) / 2
                    self.rotate_cy = (self.top + self.bottom) / 2
                    self.scene.cursor("rotate1")
                    self.tool = self.tool_rotate
                    self.update_statusmsg(_("Rotate around center"))
                elif method == "rotate_inner_tl":
                    self.rotate_cx = self.right
                    self.rotate_cy = self.bottom
                    self.scene.cursor("rotate2")
                    self.tool = self.tool_rotate
                    self.update_statusmsg(_("Rotate around bottom-right-corner"))
                elif method == "rotate_inner_tr":
                    self.rotate_cx = self.left
                    self.rotate_cy = self.bottom
                    self.scene.cursor("rotate2")
                    self.tool = self.tool_rotate
                    self.update_statusmsg(_("Rotate around bottom-left-corner"))
                elif method == "rotate_inner_bl":
                    self.rotate_cx = self.right
                    self.rotate_cy = self.top
                    self.scene.cursor("rotate2")
                    self.tool = self.tool_rotate
                    self.update_statusmsg(_("Rotate around top-right-corner"))
                elif method == "rotate_inner_br":
                    # opposing corner
                    self.rotate_cx = self.left
                    self.rotate_cy = self.top
                    self.scene.cursor("rotate2")
                    self.tool = self.tool_rotate
                    self.update_statusmsg(_("Rotate around top-left-corner"))
                else:
                    self.scene.cursor("arrow")
                    self.tool = self.tool_none
                    self.update_statusmsg(_("Status"))

            return RESPONSE_CHAIN
        dx = space_pos[4]
        dy = space_pos[5]

        if event_type == "rightdown":
            elements.set_emphasized_by_position(space_pos)
            if not elements.has_emphasis():
                return RESPONSE_CONSUME
            create_menu(
                self.scene.context.gui, elements.top_element(emphasized=True), elements
            )
            self.scene.request_refresh()
            return RESPONSE_CONSUME
        elif event_type == "doubleclick":
            elements.set_emphasized_by_position(space_pos)
            self.scene.context.signal("activate_selected_nodes", 0)
            return RESPONSE_CONSUME
        elif event_type == "leftdown":
            # Lets'check if the Ctrl or Shift Keys are pressed, if yes ignore the event, as they belong to the selection rectangle
            if not (self.key_control_pressed or self.key_shift_pressed):
                self.was_lb_raised = True
                self.save_width = self.width
                self.save_height = self.height
                self.total_delta_x = dx
                self.total_delta_y = dy
                self.uniform = True
                if (
                    self.key_alt_pressed
                ):  # Duplicate the selection in the background and start moving
                    self.create_duplicate()
                self.tool_running = True
                self.tool(space_pos, dx, dy, -1)
                return RESPONSE_CONSUME
        elif event_type == "middledown":
            self.was_lb_raised = False
            self.save_width = self.width
            self.save_height = self.height
            self.total_delta_x = dx
            self.total_delta_y = dy
            self.uniform = False
            self.tool_running = True
            self.tool(space_pos, dx, dy, -1)
            return RESPONSE_CONSUME
        elif event_type == "leftup":
            if self.was_lb_raised:
                self.tool_running = False
                self.tool(space_pos, dx, dy, 1)
                self.elements.ensure_positive_bounds()
                self.was_lb_raised = False
                return RESPONSE_CONSUME
        elif event_type in ("middleup", "lost"):
            if self.was_lb_raised:
                self.was_lb_raised = False
                self.tool(space_pos, dx, dy, 1)
                self.elements.ensure_positive_bounds()
                return RESPONSE_CONSUME
        elif event_type == "move":
            if self.was_lb_raised:
                if not elements.has_emphasis():
                    return RESPONSE_CONSUME
                if self.save_width is None or self.save_height is None:
                    self.save_width = self.width
                    self.save_height = self.height
                self.total_delta_x += dx
                self.total_delta_y += dy
                self.tool(space_pos, dx, dy, 0)
                return RESPONSE_CONSUME
        return RESPONSE_CHAIN

    def tool_none(self, position, dx, dy, event=0):
        return

    def tool_scalexy_se(self, position, dx, dy, event=0):
        """
        Change scale vs the bottom right corner.
        """
        self.tool_scale_general("se", position, dx, dy, event)

    def tool_scalexy_nw(self, position, dx, dy, event=0):
        """
        Change scale from the top left corner.
        """
        self.tool_scale_general("nw", position, dx, dy, event)

    def tool_scalexy_ne(self, position, dx, dy, event=0):
        """
        Change scale from the top right corner.
        """
        self.tool_scale_general("ne", position, dx, dy, event)

    def tool_scalexy_sw(self, position, dx, dy, event=0):
        """
        Change scale from the bottom left corner.
        """
        self.tool_scale_general("sw", position, dx, dy, event)

    def tool_scalex_e(self, position, dx, dy, event=0):
        """
        Change scale from the right side.
        """
        self.tool_scale_general("e", position, dx, dy, event)

    def tool_scalex_w(self, position, dx, dy, event=0):
        """
        Change scale from the left side.
        """
        self.tool_scale_general("w", position, dx, dy, event)

    def tool_scaley_s(self, position, dx, dy, event=0):
        """
        Change scale from the bottom side.
        """
        self.tool_scale_general("s", position, dx, dy, event)

    def tool_scaley_n(self, position, dx, dy, event=0):
        """
        Change scale from the top side.
        """
        self.tool_scale_general("n", position, dx, dy, event)

    def tool_scale_general(self, method, position, dx, dy, event=0):
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
        if event == 0:
            # Establish origin
            if "n" in method:
                orgy = self.bottom
            else:
                orgy = self.top

            if "e" in method:
                orgx = self.right
            else:
                orgx = self.left

            # Establish scales
            scalex = 1
            scaley = 1
            if "n" in method:
                scaley = (self.bottom - position[1]) / self.save_height
            elif "s" in method:
                scaley = (position[1] - self.top) / self.save_height

            if "w" in method:
                scalex = (self.right - position[0]) / self.save_width
            elif "e" in method:
                scalex = (position[0] - self.left) / self.save_width

            if len(method) > 1 and self.uniform:  # from corner
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale

            self.save_width *= scalex
            self.save_height *= scaley

            # b = elements.selected_area()
            b = elements._emphasized_bounds
            if "n" in method:
                orgy = self.bottom
            else:
                orgy = self.top

            if "w" in method:
                orgx = self.right
            else:
                orgx = self.left

            if "n" in method:
                b[1] = b[3] - self.save_height
            elif "s" in method:
                b[3] = b[1] + self.save_height

            if "e" in method:
                b[2] = b[0] + self.save_width
            elif "w" in method:
                b[0] = b[2] - self.save_width

            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, scaley, orgx, orgy)
                # We leave that to the end
                # try:
                #    obj.node.modified()
                # except AttributeError:
                #    pass
            for e in elements.flat(types=("group", "file")):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            elements.update_bounds([b[0], b[1], b[2], b[3]])
            self.scene.request_refresh()

    def tool_translate(self, position, dx, dy, event=0):
        """
        Change the position of the selected elements.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass

        if event == 0:
            # b = elements.selected_area()
            b = elements._emphasized_bounds
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.transform.post_translate(dx, dy)
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            for e in elements.flat(types=("group", "file")):
                obj = e.object
                # We leave that to the end
                # try:
                #    obj.node.modified()
                # except AttributeError:
                #    pass
            self.translate(dx, dy)
            elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()

    def tool_skew_x(self, position, dx, dy, event=0):
        """
        Change the skew of the selected elements.
        """
        elements = self.scene.context.elements
        if event == 1:
            self.rotated_angle = 0
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
        if event == 0:
            this_side = self.total_delta_x
            other_side = self.height
            skew_tan = this_side / other_side
            self.rotated_angle = math.atan(skew_tan)

            b = elements.selected_area()
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                mat = obj.transform
                mat[2] = skew_tan
                obj.transform = mat
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            for e in elements.flat(types=("group", "file")):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            # elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()

    def tool_skew_y(self, position, dx, dy, event=0):
        """
        Change the skew of the selected elements.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            self.rotated_angle = 0
        if event == 0:

            this_side = self.total_delta_y
            other_side = self.width
            skew_tan = this_side / other_side
            self.rotated_angle = math.atan(skew_tan)

            b = elements.selected_area()
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                mat = obj.transform
                mat[1] = skew_tan
                obj.transform = mat
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            for e in elements.flat(types=("group", "file")):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            # elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()

    def tool_rotate(self, position, dx, dy, event=0):
        """
        Change the rotation of the selected elements.
        """
        rot_angle = 0
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            self.rotated_angle = 0
        if event == 0:
            if self.rotate_cx is None:
                self.rotate_cx = (self.right + self.left) / 2
            if self.rotate_cy is None:
                self.rotate_cy = (self.top + self.bottom) / 2

            # Okay lets figure out whether the direction of travel was more CW or CCW
            # Lets focus on the bigger movement
            d_left = position[0] < self.rotate_cx
            d_top = position[1] < self.rotate_cy
            if abs(dx) > abs(dy):
                if d_left and d_top:  # LT
                    cw = dx > 0
                elif d_left and not d_top:  # LB
                    cw = dx < 0
                elif not d_left and not d_top:  # RB
                    cw = dx < 0
                elif not d_left and d_top:  # TR
                    cw = dx > 0
            else:
                if d_left and d_top:  # LT
                    cw = dy < 0
                elif d_left and not d_top:  # LB
                    cw = dy < 0
                elif not d_left and not d_top:  # RB
                    cw = dy > 0
                elif not d_left and d_top:  # TR
                    cw = dy > 0

            if self.key_alt_pressed:
                delta = 45
            else:
                delta = 1
                if not self.key_shift_pressed:
                    dd = abs(dx) if abs(dx) > abs(dy) else abs(dy)
                    pxl = dd * self.matrix.value_scale_x()
                    # print ("Delta=%.1f, Pxl=%.1f" % ( dd, pxl))
                    if 10 < pxl <= 20:
                        delta = 2
                    elif 20 < pxl <= 30:
                        delta = 5
                    elif pxl > 30:
                        delta = 10
            if cw:
                rot_angle = +1 * delta * math.tau / 360
            else:
                rot_angle = -1 * delta * math.tau / 360

            # Update Rotation angle...
            self.rotated_angle += rot_angle
            # Bring back to 'regular' radians
            while self.rotated_angle >= 1 * math.tau:
                self.rotated_angle -= 1 * math.tau
            while self.rotated_angle <= -1 * math.tau:
                self.rotated_angle += 1 * math.tau

            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.transform.post_rotate(rot_angle, self.rotate_cx, self.rotate_cy)
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            for e in elements.flat(types=("group", "file")):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            # elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()

    def draw_rotation_corners(self, gc, wdx, wdy, x0, y0, x1, y1):
        # Compute only once....
        if self.arcsegment is None:
            signx = +1
            signy = +1
            xx = 0
            yy = 0
            self.arcsegment = []
            # Start arrow
            x = xx + signx * 0.5 * wdx - signx * self.rot_area * wdx
            y = yy + signy * 0.5 * wdy
            self.arcsegment += [
                (
                    x - signx * self.rot_area * 1 / 4 * wdx,
                    y - signy * self.rot_area * 1 / 4 * wdy,
                )
            ]
            self.arcsegment += [(x, y)]
            self.arcsegment += [
                (
                    x + signx * self.rot_area * 1 / 4 * wdx,
                    y - signy * self.rot_area * 1 / 4 * wdy,
                )
            ]
            self.arcsegment += [(x, y)]

            # Arc-Segment
            numpts = 8
            for k in range(numpts + 1):
                radi = k * math.pi / (2 * numpts)
                sy = math.sin(radi)
                sx = math.cos(radi)
                x = xx + signx * 0.5 * wdx - signx * sx * self.rot_area * wdx
                y = yy + signy * 0.5 * wdy - signy * sy * self.rot_area * wdy
                # print ("Radian=%.1f (%.1f°), sx=%.1f, sy=%.1f, x=%.1f, y=%.1f" % (radi, (radi/math.pi*180), sy, sy, x, y))
                self.arcsegment += [(x, y)]

            # End Arrow
            x = xx + signx * 0.5 * wdx
            y = yy + signy * 0.5 * wdy - signy * self.rot_area * wdy
            self.arcsegment += [
                (
                    x - signx * self.rot_area * 1 / 4 * wdx,
                    y - signy * self.rot_area * 1 / 4 * wdy,
                )
            ]
            self.arcsegment += [(x, y)]
            self.arcsegment += [
                (
                    x - signx * self.rot_area * 1 / 4 * wdx,
                    y + signy * self.rot_area * 1 / 4 * wdy,
                )
            ]

        if self.use_handle_rotate:
            for i in range(2):
                for j in range(2):
                    if i == 0:
                        signx = +1
                        xx = x0
                    else:
                        signx = -1
                        xx = x1
                    if j == 0:
                        signy = +1
                        yy = y0
                    else:
                        signy = -1
                        yy = y1

                    segment = []
                    for idx in range(len(self.arcsegment)):
                        x = xx + signx * self.arcsegment[idx][0]
                        y = yy + signy * self.arcsegment[idx][1]
                        segment += [(x, y)]
                    pen = wx.Pen(wx.Colour(0x7F, 0x7F, 0x7F), 2, wx.SOLID)
                    pen.SetWidth(0.75 * self.selection_pen.GetWidth())
                    pen.SetStyle(wx.PENSTYLE_SOLID)
                    gc.StrokeLines(segment)

    def draw_handles(self, gc, wdx, wdy, x0, y0, x1, y1):
        corners = []
        if self.use_handle_size:
            corners += [
                # corners
                [x0 - wdx / 2, y0 - wdy / 2, wdx, wdy],
                [x1 - wdx / 2, y0 - wdy / 2, wdx, wdy],
                [x0 - wdx / 2, y1 - wdy / 2, wdx, wdy],
                [x1 - wdx / 2, y1 - wdy / 2, wdx, wdy],
                # Middle of sides
                [x0 - wdx / 2, (y1 + y0) / 2 - wdy / 2, wdx, wdy],
                [x1 - wdx / 2, (y1 + y0) / 2 - wdy / 2, wdx, wdy],
                [(x0 + x1) / 2 - wdx / 2, y0 - wdy / 2, wdx, wdy],
                [(x0 + x1) / 2 - wdx / 2, y1 - wdy / 2, wdx, wdy],
                # Center
                [(x0 + x1) / 2 - wdx / 2, (y1 + y0) / 2 - wdy / 2, wdx, wdy],
            ]
        # Skew
        if self.use_handle_skew:
            corners.append(
                [
                    x0 + 3 / 4 * (x1 - x0) - wdx / 3,
                    y1 - wdy / 3,
                    2 / 3 * wdx,
                    2 / 3 * wdy,
                ]
            )  # skew x
            corners.append(
                [
                    x1 - wdx / 3,
                    y0 + 1 / 4 * (y1 - y0) - wdy / 3,
                    2 / 3 * wdx,
                    2 / 3 * wdy,
                ]
            )  # skew y

        if len(corners) > 0:
            pen = wx.Pen(wx.Colour(0x7F, 0x7F, 0x7F), 1, wx.SOLID)
            pen.SetStyle(wx.PENSTYLE_SOLID)
            brush = wx.Brush(wx.Colour(0x7F, 0x7F, 0x7F), wx.SOLID)
            gc.SetPen(pen)
            gc.SetBrush(brush)

            for corn in corners:
                gc.DrawRectangle(corn[0], corn[1], corn[2], corn[3])

    def process_draw(self, gc):
        """
        Draw routine for drawing the selection box.
        """
        if self.scene.context.draw_mode & DRAW_MODE_SELECTION != 0:
            return
        context = self.scene.context
        draw_mode = context.draw_mode
        elements = self.scene.context.elements
        bounds = elements.selected_area()
        matrix = self.parent.matrix
        # get infos whether to draw handles or not
        try:
            self.use_handle_rotate = context.enable_sel_rotate
            self.use_handle_skew = context.enable_sel_skew
            self.use_handle_size = context.enable_sel_handle
            # print("Handle-Handling: H=%s, R=%s, S=%s" % (self.use_handle_size, self.use_handle_rotate, self.use_handle_skew))
        except AttributeError:
            # Stuff has not yet been defined...
            pass

        if bounds is not None:
            # Make sure the checkboxes are shown
            try:
                linewidth = 2.0 / matrix.value_scale_x()
                font_size = 14.0 / matrix.value_scale_x()
            except ZeroDivisionError:
                matrix.reset()
                return
            try:
                self.selection_pen.SetWidth(linewidth)
            except TypeError:
                self.selection_pen.SetWidth(int(linewidth))
            if font_size < 1.0:
                font_size = 1.0  # Mac does not allow values lower than 1.
            try:
                font = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
            except TypeError:
                font = wx.Font(int(font_size), wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, wx.Colour(0x7F, 0x7F, 0x7F))
            gc.SetPen(self.selection_pen)
            x0, y0, x1, y1 = bounds
            center_x = (x0 + x1) / 2.0
            center_y = (y0 + y1) / 2.0
            gc.StrokeLine(center_x, 0, center_x, y0)
            gc.StrokeLine(0, center_y, x0, center_y)
            gc.StrokeLine(x0, y0, x1, y0)
            gc.StrokeLine(x1, y0, x1, y1)
            gc.StrokeLine(x1, y1, x0, y1)
            gc.StrokeLine(x0, y1, x0, y0)

            if draw_mode & DRAW_MODE_SELECTION == 0:
                p = self.scene.context
                conversion, name, marks, index = (
                    p.units_convert,
                    p.units_name,
                    p.units_marks,
                    p.units_index,
                )
                gc.DrawText("%.1f%s" % (y0 / conversion, name), center_x, y0 / 2.0)
                gc.DrawText("%.1f%s" % (x0 / conversion, name), x0 / 2.0, center_y)
                gc.DrawText("%.1f%s" % ((y1 - y0) / conversion, name), x1, center_y)
                gc.DrawText("%.1f%s" % ((x1 - x0) / conversion, name), center_x, y1)

            self.selbox_wx = 5 * linewidth  # 10.0 / matrix.value_scale_x()
            self.selbox_wy = 5 * linewidth  # 10.0 / matrix.value_scale_y()
            # print("Selbox-width=(%.1f, %.1f) - linewidth=%.1f" % (self.selbox_wx, self.selbox_wy, self.selection_pen.GetWidth()))
            if not self.tool_running:
                self.draw_handles(gc, self.selbox_wx, self.selbox_wy, x0, y0, x1, y1)
                self.draw_rotation_corners(
                    gc, self.selbox_wx, self.selbox_wy, x0, y0, x1, y1
                )
            if abs(self.rotated_angle) > 0.001:
                gc.DrawText(
                    "%.0f°" % (360 * self.rotated_angle / math.tau), center_x, center_y
                )

    def create_duplicate(self):
        from copy import copy

        self.duplicated_elements = True
        # Iterate through list of selected elements, duplicate them

        context = self.scene.context
        elements = context.elements
        adding_elements = [copy(e) for e in list(elements.elems(emphasized=True))]
        elements.add_elems(adding_elements)
        elements.classify(adding_elements)

    # Just to make sure weh have these
    def init(self, context):
        pass

    def final(self, context):
        pass


class RectSelectWidget(Widget):
    """
    SceneWidget

    Rectangle Selection Widget, draws the selection rectangle if left-clicked and dragged
    """

    # selection_method = 1 = hit, 2 = cross, 3 = enclose
    SELECTION_TOUCH = 1
    SELECTION_CROSS = 2
    SELECTION_ENCLOSE = 3
    # Color for selection rectangle (hit, cross, enclose)
    selection_style = [
        (
            wx.RED,
            wx.PENSTYLE_DOT_DASH,
            "Select all elements the selection rectangle touches.",
        ),
        (
            wx.GREEN,
            wx.PENSTYLE_DOT,
            "Select all elements the selection rectangle crosses.",
        ),
        (
            wx.BLUE,
            wx.PENSTYLE_SHORT_DASH,
            "Select all elements the selection rectangle encloses.",
        ),
    ]
    selection_text_shift = " Previously selected remain selected!"
    selection_text_control = " Invert selection state of elements!"

    # 2 | 1        Define Selection method per sector, movement of mouse from point of origin into that sector...
    # - + -
    # 3 | 0
    #
    selection_method = [
        SELECTION_ENCLOSE,
        SELECTION_ENCLOSE,
        SELECTION_TOUCH,
        SELECTION_TOUCH,
    ]  # Selection rectangle to the right: enclose, to the left: touch

    key_shift_pressed = False
    key_control_pressed = False
    key_alt_pressed = False
    was_lb_raised = False

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(self.selection_style[0][0])
        self.selection_pen.SetWidth(25)
        self.selection_pen.SetStyle(self.selection_style[0][1])
        self.start_location = None
        self.end_location = None

    def hit(self):
        return HITCHAIN_HIT

    store_last_msg = ""

    def update_statusmsg(self, value):
        if value != self.store_last_msg:
            self.store_last_msg = value
            self.scene.context.signal("statusmsg", value)

    # debug_msg = ""

    def event(self, window_pos=None, space_pos=None, event_type=None):
        # sdbg = event_type
        # if sdbg in ("hover_start", "hover_end", "hover"):
        #    sdbg = "hover"
        # if sdbg != self.debug_msg:
        #    self.debug_msg = sdbg
        #    print(
        #        "SelRect-Event: %s (current state: %s)"
        #        % (event_type, self.was_lb_raised)
        #    )

        elements = self.scene.context.elements
        if event_type == "leftdown":
            self.start_location = space_pos
            self.end_location = space_pos
            return RESPONSE_CONSUME
        elif event_type == "leftclick":
            self.start_location = None
            self.end_location = None
            return RESPONSE_DROP
        elif event_type == "kb_shift_release":
            if self.key_shift_pressed:
                self.key_shift_pressed = False
                if self.start_location is None:
                    return RESPONSE_CHAIN
                else:
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "kb_shift_press":
            if not self.key_shift_pressed:
                self.key_shift_pressed = True
                if self.start_location is None:
                    return RESPONSE_CHAIN
                else:
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "kb_ctrl_release":
            if self.key_control_pressed:
                self.key_control_pressed = False
                if self.start_location is None:
                    return RESPONSE_CHAIN
                else:
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "kb_ctrl_press":
            if not self.key_control_pressed:
                self.key_control_pressed = True
                if self.start_location is None:
                    return RESPONSE_CHAIN
                else:
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "kb_alt_release":
            if self.key_alt_pressed:
                self.key_alt_pressed = False
                if self.start_location is None:
                    return RESPONSE_CHAIN
                else:
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "kb_alt_press":
            if not self.key_alt_pressed:
                self.key_alt_pressed = True
                if self.start_location is None:
                    return RESPONSE_CHAIN
                else:
                    self.scene.request_refresh()
                    return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN

        elif event_type == "leftup":
            _ = self.scene.context._
            self.update_statusmsg(_("Status"))
            elements.validate_selected_area()
            sx = self.start_location[0]
            sy = self.start_location[1]
            ex = self.end_location[0]
            ey = self.end_location[1]
            if sx <= ex:
                if sy <= ey:
                    sector = 0
                else:
                    sector = 1
            else:
                if sy <= ey:
                    sector = 3
                else:
                    sector = 2

            sx = min(self.start_location[0], self.end_location[0])
            sy = min(self.start_location[1], self.end_location[1])
            ex = max(self.start_location[0], self.end_location[0])
            ey = max(self.start_location[1], self.end_location[1])
            # print(
            #    "Selection_box: (%f,%f)-(%f,%f) - Method=%f"
            #    % (sx, sy, ex, ey, self.selection_method[sector])
            # )
            for obj in elements.elems():
                try:
                    q = obj.bbox(True)
                except AttributeError:
                    continue  # This element has no bounds.
                if q is None:
                    continue
                xmin = q[0]
                ymin = q[1]
                xmax = q[2]
                ymax = q[3]
                # no hit
                cover = 0
                # Check Hit
                # The rectangles don't overlap if
                # one rectangle's minimum in some dimension
                # is greater than the other's maximum in
                # that dimension.
                if not ((sx > xmax) or (xmin > ex) or (sy > ymax) or (ymin > ey)):
                    cover = self.SELECTION_TOUCH
                    # If selection rect is fullly inside an object then ignore
                    if sx > xmin and ex < xmax and sy > ymin and ey < ymax:
                        cover = 0

                # Check Cross
                if (
                    ((sx <= xmin) and (xmax <= ex))
                    and not ((sy > ymax) or (ey < ymin))
                    or ((sy <= ymin) and (ymax <= ey))
                    and not ((sx > xmax) or (ex < xmin))
                ):
                    cover = self.SELECTION_CROSS
                # Check contain
                if ((sx <= xmin) and (xmax <= ex)) and ((sy <= ymin) and (ymax <= ey)):
                    cover = self.SELECTION_ENCLOSE

                if self.key_shift_pressed:
                    # Add Selection
                    if cover >= self.selection_method[sector]:
                        obj.node.emphasized = True
                elif self.key_control_pressed:
                    # Invert Selection
                    if cover >= self.selection_method[sector]:
                        obj.node.emphasized = not obj.node.emphasized
                else:
                    # Replace Selection
                    if cover >= self.selection_method[sector]:
                        obj.node.emphasized = True
                    else:
                        obj.node.emphasized = False

            self.scene.request_refresh()
            self.start_location = None
            self.end_location = None

            return RESPONSE_CONSUME
        elif event_type == "move":
            self.scene.request_refresh()
            self.end_location = space_pos
            return RESPONSE_CONSUME
        elif event_type == "lost":
            self.start_location = None
            self.end_location = None
            return RESPONSE_CONSUME
        return RESPONSE_DROP

    def draw_rectangle(self, gc, x0, y0, x1, y1, tcolor, tstyle):
        matrix = self.parent.matrix
        self.selection_pen.SetColour(tcolor)
        self.selection_pen.SetStyle(tstyle)
        gc.SetPen(self.selection_pen)

        linewidth = 2.0 / matrix.value_scale_x()
        if linewidth < 1:
            linewidth = 1
        try:
            self.selection_pen.SetWidth(linewidth)
        except TypeError:
            self.selection_pen.SetWidth(int(linewidth))
        gc.SetPen(self.selection_pen)
        gc.StrokeLine(x0, y0, x1, y0)
        gc.StrokeLine(x1, y0, x1, y1)
        gc.StrokeLine(x1, y1, x0, y1)
        gc.StrokeLine(x0, y1, x0, y0)

    def draw_tiny_indicator(self, gc, symbol, x0, y0, x1, y1, tcolor, tstyle):
        matrix = self.parent.matrix
        self.selection_pen.SetColour(tcolor)
        self.selection_pen.SetStyle(tstyle)

        linewidth = 2.0 / matrix.value_scale_x()
        if linewidth < 1:
            linewidth = 1
        try:
            self.selection_pen.SetWidth(linewidth)
        except TypeError:
            self.selection_pen.SetWidth(int(linewidth))
        gc.SetPen(self.selection_pen)
        delta_X = 15.0 / matrix.value_scale_x()
        delta_Y = 15.0 / matrix.value_scale_y()
        if abs(x1 - x0) > delta_X and abs(y1 - y0) > delta_Y:  # Don't draw if too tiny
            # Draw tiny + in Corner in corner of pointer
            x_signum = +1 * delta_X if x0 < x1 else -1 * delta_X
            y_signum = +1 * delta_Y if y0 < y1 else -1 * delta_X
            ax1 = x1 - x_signum
            ay1 = y1 - y_signum

            gc.SetPen(self.selection_pen)
            gc.StrokeLine(ax1, y1, ax1, ay1)
            gc.StrokeLine(ax1, ay1, x1, ay1)
            font_size = 10.0 / matrix.value_scale_x()
            if font_size < 1.0:
                font_size = 1.0
            font = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.NORMAL)

            gc.SetFont(font, tcolor)
            (t_width, t_height) = gc.GetTextExtent(symbol)
            gc.DrawText(
                symbol, (ax1 + x1) / 2 - t_width / 2, (ay1 + y1) / 2 - t_height / 2
            )
            if (
                abs(x1 - x0) > 2 * delta_X and abs(y1 - y0) > 2 * delta_Y
            ):  # Don't draw if too tiny
                # Draw second symbol at origin
                ax1 = x0 + x_signum
                ay1 = y0 + y_signum
                gc.StrokeLine(ax1, y0, ax1, ay1)
                gc.StrokeLine(ax1, ay1, x0, ay1)
                gc.DrawText(
                    symbol, (ax1 + x0) / 2 - t_width / 2, (ay1 + y0) / 2 - t_height / 2
                )

    def process_draw(self, gc):
        """
        Draw the selection rectangle
        """
        if self.start_location is not None and self.end_location is not None:
            x0 = self.start_location[0]
            y0 = self.start_location[1]
            x1 = self.end_location[0]
            y1 = self.end_location[1]
            if x0 <= x1:
                if y0 <= y1:
                    sector = 0
                else:
                    sector = 1
            else:
                if y0 <= y1:
                    sector = 3
                else:
                    sector = 2

            _ = self.scene.context._
            statusmsg = _(self.selection_style[self.selection_method[sector] - 1][2])
            if self.key_shift_pressed:
                statusmsg += _(self.selection_text_shift)
            elif self.key_control_pressed:
                statusmsg += _(self.selection_text_control)

            self.update_statusmsg(statusmsg)
            gcstyle = self.selection_style[self.selection_method[sector] - 1][0]
            gccolor = self.selection_style[self.selection_method[sector] - 1][1]
            self.draw_rectangle(
                gc,
                x0,
                y0,
                x1,
                y1,
                gcstyle,
                gccolor,
            )

            # Determine Colour on selection mode: standard (from left top to right bottom) = Blue, else Green
            # Draw indicator...
            if self.key_shift_pressed:
                self.draw_tiny_indicator(
                    gc,
                    "+",
                    x0,
                    y0,
                    x1,
                    y1,
                    gcstyle,
                    gccolor,
                )

            elif self.key_control_pressed:
                self.draw_tiny_indicator(
                    gc,
                    "^",
                    x0,
                    y0,
                    x1,
                    y1,
                    self.selection_style[self.selection_method[sector] - 1][0],
                    self.selection_style[self.selection_method[sector] - 1][1],
                )


class ReticleWidget(Widget):
    """
    SceneWidget

    Draw the tracking reticles. Each different origin for the driver;position and emulator;position
    gives a new tracking reticle.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.reticles = {}
        self.pen = wx.Pen()

    def init(self, context):
        """
        Listen to driver;position and emulator;position
        """
        context.listen("driver;position", self.on_update_driver)
        context.listen("emulator;position", self.on_update_emulator)

    def final(self, context):
        """
        Unlisten to driver;position and emulator;position
        """
        context.unlisten("driver;position", self.on_update_driver)
        context.unlisten("emulator;position", self.on_update_emulator)

    def on_update_driver(self, origin, pos):
        """
        Update of driver adds and ensures the location of the d+origin position
        """
        self.reticles["d" + origin] = pos[2], pos[3]
        self.scene.request_refresh_for_animation()

    def on_update_emulator(self, origin, pos):
        """
        Update of emulator adds and ensures the location of the e+origin position
        """
        self.reticles["e" + origin] = pos[2], pos[3]

    def process_draw(self, gc):
        """
        Draw all the registered reticles.
        """
        context = self.scene.context
        try:
            if context.draw_mode & DRAW_MODE_RETICLE == 0:
                # Draw Reticles
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
                for index, ret in enumerate(self.reticles):
                    r = self.reticles[ret]
                    self.pen.SetColour(Color.distinct(index + 2).hex)
                    gc.SetPen(self.pen)
                    x = r[0]
                    y = r[1]
                    if x is None or y is None:
                        x = 0
                        y = 0
                    x, y = self.scene.convert_scene_to_window([x, y])
                    gc.DrawEllipse(x - 5, y - 5, 10, 10)
        except AttributeError:
            pass


class LaserPathWidget(Widget):
    """
    Scene Widget.

    Draw the laserpath.

    These are blue lines that track the previous position of the laser-head.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.laserpath = [[0, 0] for _ in range(1000)], [[0, 0] for _ in range(1000)]
        self.laserpath_index = 0

    def init(self, context):
        context.listen("driver;position", self.on_update)
        context.listen("emulator;position", self.on_update)

    def final(self, context):
        context.unlisten("driver;position", self.on_update)
        context.unlisten("emulator;position", self.on_update)

    def on_update(self, origin, pos):
        laserpath = self.laserpath
        index = self.laserpath_index
        laserpath[0][index][0] = pos[0]
        laserpath[0][index][1] = pos[1]
        laserpath[1][index][0] = pos[2]
        laserpath[1][index][1] = pos[3]
        index += 1
        index %= len(laserpath[0])
        self.laserpath_index = index

    def clear_laserpath(self):
        self.laserpath = [[0, 0] for _ in range(1000)], [[0, 0] for _ in range(1000)]
        self.laserpath_index = 0

    def process_draw(self, gc):
        """
        Draw the blue lines of the LaserPath
        """
        context = self.scene.context
        if context.draw_mode & DRAW_MODE_LASERPATH == 0:
            gc.SetPen(wx.BLUE_PEN)
            starts, ends = self.laserpath
            try:
                gc.StrokeLineSegments(starts, ends)
            except OverflowError:
                pass  # I don't actually know why this would happen.


class GridWidget(Widget):
    """
    Interface Widget
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.grid = None
        self.background = None
        self.grid_line_pen = wx.Pen()
        self.grid_line_pen.SetColour(wx.Colour(0xA0, 0xA0, 0xA0))
        self.grid_line_pen.SetWidth(1)

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Capture and deal with the doubleclick event.

        Doubleclick in the grid loads a menu to remove the background.
        """
        if event_type == "hover":
            return RESPONSE_CHAIN
        elif event_type == "doubleclick":
            menu = wx.Menu()
            _ = self.scene.context._
            if self.background is not None:
                item = menu.Append(wx.ID_ANY, _("Remove Background"), "")
                self.scene.gui.Bind(
                    wx.EVT_MENU,
                    lambda e: self.scene.gui.signal("background", None),
                    id=item.GetId(),
                )
                if menu.MenuItemCount != 0:
                    self.scene.gui.PopupMenu(menu)
                    menu.Destroy()
        self.grid = None
        return RESPONSE_CHAIN

    def calculate_grid(self):
        """
        Based on the current matrix calculate the grid within the bed-space.
        """
        context = self.scene.context
        if context is not None:
            bed_dim = context.root
            wmils = bed_dim.bed_width * MILS_IN_MM
            hmils = bed_dim.bed_height * MILS_IN_MM
        else:
            wmils = 310 * MILS_IN_MM
            hmils = 210 * MILS_IN_MM
        kernel_root = context.root
        convert = kernel_root.units_convert
        marks = kernel_root.units_marks
        step = convert * marks
        starts = []
        ends = []
        if step == 0:
            self.grid = None
            return starts, ends
        x = 0.0
        while x < wmils:
            starts.append((x, 0))
            ends.append((x, hmils))
            x += step
        y = 0.0
        while y < hmils:
            starts.append((0, y))
            ends.append((wmils, y))
            y += step
        self.grid = starts, ends

    def process_draw(self, gc):
        """
        Draw the grid on the scene.
        """
        if self.scene.context.draw_mode & DRAW_MODE_BACKGROUND == 0:
            context = self.scene.context
            if context is not None:
                bed_dim = context.root
                wmils = bed_dim.bed_width * MILS_IN_MM
                hmils = bed_dim.bed_height * MILS_IN_MM
            else:
                wmils = 320 * MILS_IN_MM
                hmils = 210 * MILS_IN_MM
            background = self.background
            if background is None:
                gc.SetBrush(wx.WHITE_BRUSH)
                gc.DrawRectangle(0, 0, wmils, hmils)
            elif isinstance(background, int):
                gc.SetBrush(wx.Brush(wx.Colour(swizzlecolor(background))))
                gc.DrawRectangle(0, 0, wmils, hmils)
            else:
                gc.DrawBitmap(background, 0, 0, wmils, hmils)

        if self.scene.context.draw_mode & DRAW_MODE_GRID == 0:
            if self.grid is None:
                self.calculate_grid()
            starts, ends = self.grid
            matrix = self.scene.widget_root.scene_widget.matrix
            try:
                scale_x = matrix.value_scale_x()
                line_width = 1.0 / scale_x
                if line_width < 1:
                    line_width = 1
                try:
                    self.grid_line_pen.SetWidth(line_width)
                except TypeError:
                    self.grid_line_pen.SetWidth(int(line_width))

                gc.SetPen(self.grid_line_pen)
                gc.StrokeLineSegments(starts, ends)
            except (OverflowError, ValueError, ZeroDivisionError):
                matrix.reset()

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed recalculate the lines
        """
        if signal == "grid":
            self.grid = None
        elif signal == "background":
            self.background = args[0]


class GuideWidget(Widget):
    """
    Interface Widget

    Guide lines drawn at along the scene edges.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.scene.context.setting(bool, "show_negative_guide", True)

    def process_draw(self, gc):
        """
        Draw the guide lines
        """
        if self.scene.context.draw_mode & DRAW_MODE_GUIDES != 0:
            return
        gc.SetPen(wx.BLACK_PEN)
        w, h = gc.Size
        p = self.scene.context
        scaled_conversion = (
            p.units_convert * self.scene.widget_root.scene_widget.matrix.value_scale_x()
        )
        if scaled_conversion == 0:
            return
        edge_gap = 5
        wpoints = w / 15.0
        hpoints = h / 15.0
        points = min(wpoints, hpoints)
        # tweak the scaled points into being useful.
        # points = scaled_conversion * round(points / scaled_conversion * 10.0) / 10.0
        points = scaled_conversion * float("{:.1g}".format(points / scaled_conversion))
        sx, sy = self.scene.convert_scene_to_window([0, 0])
        if points == 0:
            return
        offset_x = sx % points
        offset_y = sy % points

        starts = []
        ends = []
        x = offset_x
        length = 20
        font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.BLACK)
        gc.DrawText(p.units_name, edge_gap, edge_gap)
        while x < w:
            if x >= 45:
                mark_point = (x - sx) / scaled_conversion
                if round(mark_point * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if mark_point >= 0 or p.show_negative_guide:
                    starts.append((x, edge_gap))
                    ends.append((x, length + edge_gap))

                    starts.append((x, h - edge_gap))
                    ends.append((x, h - length - edge_gap))

                    # gc.DrawText("%g %s" % (mark_point, p.units_name), x, 0, -tau / 4)
                    gc.DrawText("%g" % mark_point, x, edge_gap, -math.tau / 4)
            x += points

        y = offset_y
        while y < h:
            if y >= 20:
                mark_point = (y - sy) / scaled_conversion
                if round(mark_point * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if mark_point >= 0 or p.show_negative_guide:
                    starts.append((edge_gap, y))
                    ends.append((length + edge_gap, y))

                    starts.append((w - edge_gap, y))
                    ends.append((w - length - edge_gap, y))

                    # gc.DrawText("%g %s" % (mark_point + 0, p.units_name), 0, y + 0)
                    gc.DrawText("%g" % (mark_point + 0), edge_gap, y + 0)
            y += points
        if len(starts) > 0:
            gc.StrokeLineSegments(starts, ends)

    def signal(self, signal, *args, **kwargs):
        """
        Process guide signal to delete the current guide lines and force them to be recalculated.
        """
        if signal == "guide":
            pass
