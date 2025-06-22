"""
This widget draws the machine origin as well as the X and Y directions for the coordinate system being used.

The machine origin is actually the position of the 0,0 location for the device being used, whereas the coordinate
system is the user display space.
"""

import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import DRAW_MODE_ORIGIN
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_HIT,
    HITCHAIN_PRIORITY_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.scene.widget import Widget

_ = wx.GetTranslation


class RotaryAxisWidget(Widget):
    """
    Rotary Axis Widget
    """

    def __init__(self, scene, name=None):
        Widget.__init__(self, scene, all=True)
        self.name = name
        self.brush = wx.Brush(
            colour=wx.Colour(255, 0, 0, alpha=127), style=wx.BRUSHSTYLE_SOLID
        )
        self.x_axis_pen = wx.Pen(colour=wx.Colour(255, 0, 0))
        self.x_axis_pen.SetWidth(1000)
        self.y_axis_pen = wx.Pen(colour=wx.Colour(0, 255, 0))
        self.y_axis_pen.SetWidth(1000)
        self.active = False
        self.offset = 0
        self.axis = 0  # 0 for X, 1 for Y
        self.zero_pos = 0
        self.rotary_mode = 0

    def hit(self):
        # return HITCHAIN_HIT
        return HITCHAIN_PRIORITY_HIT

    def done(self):
        """
        Called when the widget is done with its operation.
        """
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.active = False
        self.scene.request_refresh()

    def hit_test(self, space_pos):
        """
        Hit test for the rotary axis widget.
        This checks if the space position is within the bounds of the rotary axis.
        """
        if self.rotary_mode == 0:
            return False
        self.update_parameters()
        space = self.scene.context.device.view
        if self.axis == 0:
            # X axis
            sx = self.zero_pos
            sy = 0
            dy = float(Length("2.5%", relative_length=space.unit_height))
            dx = 2 * dy
            rx = sx - dx / 2
            ry = sy - dy
        else:
            # Y axis
            sx = 0
            sy = self.zero_pos
            dx = float(Length("2.5%", relative_length=space.unit_width))
            dy = 2 * dx
            rx = sx - dx
            ry = sy - dy / 2
        if space_pos is None:
            # If no space position is given, we cannot hit test
            return False
        return not (
            space_pos[0] < rx
            or space_pos[0] > rx + dx
            or space_pos[1] < ry
            or space_pos[1] > ry + dy
        )

    def set_new_position(self, space_pos):
        """
        Set the new position of the rotary axis based on the space position.
        This updates the zero position based on the current mouse position.
        """
        if self.axis == 0:
            pos = space_pos[0] / self.scene.context.device.view.unit_width
        else:
            pos = space_pos[1] / self.scene.context.device.view.unit_height
        pos = max(0, min(1, pos))
        if self.rotary_mode == 1:
            # Roller mode
            self.scene.context.device.rotary.set_roller_center(pos)
        else:
            # Chuck mode
            self.scene.context.device.rotary.set_chuck_center(pos)
        self.update_parameters()
        self.inform_about_updates()
        self.scene.request_refresh()

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        # if event_type in ("leftdown", "move", "leftup", "lost", "key_up"):
        #     print(f"RotaryAxisWidget.event: {event_type} {modifiers} {space_pos} - state: {self.active} rotary_mode: {self.rotary_mode}")
        if self.rotary_mode == 0:
            # Rotary mode is not active, so we don't handle events
            return RESPONSE_CHAIN
        if event_type == "leftdown":
            if self.hit_test(space_pos):
                self.scene.pane.tool_active = True
                self.scene.pane.modif_active = True
                self.active = True
                return RESPONSE_CONSUME
            return RESPONSE_CHAIN
        if event_type == "move":
            if "m_middle" in modifiers or not self.active:
                return RESPONSE_CHAIN
            self.set_new_position(space_pos)
            return RESPONSE_CONSUME
        if event_type == "leftup":
            if self.active:
                self.set_new_position(space_pos)
                self.done()
                return RESPONSE_CONSUME
            return RESPONSE_CHAIN
        if event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.active:
                self.done()
                return RESPONSE_CONSUME
            return RESPONSE_CHAIN
        if event_type == "rightdown":
            if self.hit_test(space_pos):
                # Right click on the rotary axis, we will show a menu
                def set_rotation_center(pos):
                    pos = max(0, min(1, pos))  # Clamp to [0, 1]
                    if self.rotary_mode == 1:
                        self.scene.context.device.rotary.set_roller_center(pos)
                    else:
                        self.scene.context.device.rotary.set_chuck_center(pos)
                    self.update_parameters()
                    self.inform_about_updates()
                    self.scene.request_refresh()

                def swap_axis(event):
                    new_axis = 1 - self.axis
                    self.axis = new_axis
                    if self.rotary_mode == 1:
                        self.scene.context.device.rotary.set_roller_alignment_axis(
                            new_axis
                        )
                    else:
                        self.scene.context.device.rotary.set_chuck_alignment_axis(
                            new_axis
                        )
                    self.update_parameters()
                    self.inform_about_updates()
                    self.scene.request_refresh()

                def set_to_left_edge(event):
                    set_rotation_center(0)

                def set_to_bed_center(event):
                    set_rotation_center(0.5)

                def set_to_right_edge(event):
                    set_rotation_center(1)

                def set_to_selection_center(event):
                    bbox = self.scene.context.elements.selected_area()
                    if bbox is None:
                        return
                    cx = (bbox[0] + bbox[2]) / 2
                    cy = (bbox[1] + bbox[3]) / 2
                    if self.axis == 0:
                        set_rotation_center(
                            cx / self.scene.context.device.view.unit_width
                        )
                    else:
                        set_rotation_center(
                            cy / self.scene.context.device.view.unit_height
                        )

                def set_to_lower_edge(event):
                    bbox = self.scene.context.elements.selected_area()
                    if bbox is None:
                        return
                    cx = bbox[0]
                    cy = bbox[1]
                    if self.axis == 0:
                        set_rotation_center(
                            cx / self.scene.context.device.view.unit_width
                        )
                    else:
                        set_rotation_center(
                            cy / self.scene.context.device.view.unit_height
                        )

                def set_to_upper_edge(event):
                    bbox = self.scene.context.elements.selected_area()
                    if bbox is None:
                        return
                    cx = bbox[2]
                    cy = bbox[3]
                    if self.axis == 0:
                        set_rotation_center(
                            cx / self.scene.context.device.view.unit_width
                        )
                    else:
                        set_rotation_center(
                            cy / self.scene.context.device.view.unit_height
                        )

                menu = wx.Menu()
                if self.axis == 0:
                    title_left = _("Set to left edge of bed")
                    title_right = _("Set to right edge of bed")
                else:
                    title_left = _("Set to upper edge of bed")
                    title_right = _("Set to lower edge of bed")
                item = menu.Append(wx.ID_ANY, title_left)
                self.scene.gui.Bind(wx.EVT_MENU, set_to_left_edge, item)
                item = menu.Append(wx.ID_ANY, _("Set to bed center"))
                self.scene.gui.Bind(wx.EVT_MENU, set_to_bed_center, item)
                item = menu.Append(wx.ID_ANY, title_right)
                self.scene.gui.Bind(wx.EVT_MENU, set_to_right_edge, item)
                if self.scene.context.elements.has_emphasis():
                    if self.axis == 0:
                        t_lower = _("Set to left edge of selection")
                        t_upper = _("Set to right edge of selection")
                    else:
                        t_lower = _("Set to upper edge of selection")
                        t_upper = _("Set to lower edge of selection")
                    item = menu.Append(wx.ID_ANY, t_lower)
                    self.scene.gui.Bind(wx.EVT_MENU, set_to_lower_edge, item)
                    item = menu.Append(wx.ID_ANY, _("Set to center of selection"))
                    self.scene.gui.Bind(wx.EVT_MENU, set_to_selection_center, item)
                    item = menu.Append(wx.ID_ANY, t_upper)
                    self.scene.gui.Bind(wx.EVT_MENU, set_to_upper_edge, item)
                item = menu.AppendSeparator()
                item = menu.Append(wx.ID_ANY, _("Swap X/Y Axis"))
                self.scene.gui.Bind(wx.EVT_MENU, swap_axis, item)
                self.scene.gui.PopupMenu(menu, window_pos[0], window_pos[1])
                menu.Destroy()
                return RESPONSE_CONSUME
            return RESPONSE_CHAIN
        return RESPONSE_CHAIN

    def update_parameters(self):
        rotary = self.scene.context.device.rotary
        # print (
        #     f"Rotary Axis Widget: active_chuck={rotary.rotary_active_chuck}, active_roller={rotary.rotary_active_roller}\n"
        #     f"rotary_chuck_alignment_axis={rotary.rotary_chuck_alignment_axis}, rotary_chuck_offset={rotary.rotary_chuck_offset}\n"
        #     f"rotary_roller_alignment_axis={rotary.rotary_roller_alignment_axis}, rotary_roller_offset={rotary.rotary_roller_offset}"
        #     )
        if rotary.rotary_active_chuck:
            self.rotary_mode = 2  # Chuck mode
            self.axis = rotary.rotary_chuck_alignment_axis
            self.offset = rotary.rotary_chuck_offset
        elif rotary.rotary_active_roller:
            self.rotary_mode = 1  # Roller mode
            self.axis = rotary.rotary_roller_alignment_axis
            self.offset = rotary.rotary_roller_offset
        else:
            self.rotary_mode = 0  # No rotary mode
        self.zero_pos = Length(
            f"{self.offset * 100}%",
            relative_length=self.scene.context.device.view.unit_width
            if self.axis == 0
            else self.scene.context.device.view.unit_height,
        )
        # print (f"Rotary Axis Widget: mode={self.rotary_mode}, axis={self.axis}, offset={self.offset}, zero_pos={self.zero_pos}")

    def inform_about_updates(self):
        rotary = self.scene.context.device.rotary
        if rotary.rotary_active_chuck:
            self.scene.context.signal("rotary_chuck_alignment_axis", self.axis)
            self.scene.context.signal("rotary_chuck_offset", self.offset)
        elif rotary.rotary_active_roller:
            self.scene.context.signal("rotary_roller_alignment_axis", self.axis)
            self.scene.context.signal("rotary_roller_offset", self.offset)

    def process_draw(self, gc):
        """
        Draws the rotary axis origin
        """
        if self.scene.context.draw_mode & DRAW_MODE_ORIGIN != 0:
            return
        gcmat = gc.GetTransform()
        mat_param = gcmat.Get()
        if mat_param[0] == 1 and mat_param[3] == 1:
            # We were called without a matrix applied, that's plain wrong
            return
        rotary = self.scene.context.device.rotary
        if rotary is None:
            # No rotary axis, so we don't draw anything
            return
        self.update_parameters()
        if self.rotary_mode == 0:
            # No rotary mode active, so we don't draw anything
            return
        # print(f"Rotary position: {offset*100:.1f}% ({zero_pos.length_mm})")
        space = self.scene.context.device.view
        if self.axis == 0:
            # X axis
            sx, sy = space.scene_position(self.zero_pos, 0)
            ex, ey = space.scene_position(self.zero_pos, space.unit_height)
            dy = (ey - sy) / 40
            dx = 2 * dy
            rx = sx - dx / 2
            ry = sy - dy
        else:
            # Y axis
            sx, sy = space.scene_position(0, self.zero_pos)
            ex, ey = space.scene_position(space.unit_width, self.zero_pos)
            dx = (ex - sx) / 40
            dy = 2 * dx
            rx = sx - dx
            ry = sy - dy / 2
        gc.SetBrush(wx.NullBrush)
        # gc.DrawLines will draw a polygon according to the documentation!
        # While the windows implementation of wxPython does not care
        # and draws a polyline, the Linux implementation does and closes the
        # polygon!
        if self.axis == 0:
            gc.SetPen(self.x_axis_pen)
        else:
            gc.SetPen(self.y_axis_pen)
        axis_line = gc.CreatePath()
        axis_line.MoveToPoint((sx, sy))
        axis_line.AddLineToPoint((ex, ey))
        gc.DrawPath(axis_line)

        rotary_symbol = gc.CreatePath()
        rotary_symbol.AddEllipse(rx, ry, dx, dy)
        md = min(dx, dy)
        if self.axis == 0:
            cx = rx + dx / 2
            cy = ry

            rotary_symbol.MoveToPoint(cx + md / 4, cy - md / 4)
            rotary_symbol.AddLineToPoint(cx, cy)
            rotary_symbol.AddLineToPoint(cx + md / 4, cy + md / 4)
        else:
            cx = rx
            cy = ry + dy / 2

            rotary_symbol.MoveToPoint(cx - md / 4, cy - md / 4)
            rotary_symbol.AddLineToPoint(cx, cy)
            rotary_symbol.AddLineToPoint(cx + md / 4, cy - md / 4)

        gc.DrawPath(rotary_symbol)
