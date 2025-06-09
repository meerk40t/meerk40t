from time import time

import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Color

_ = wx.GetTranslation


class LineTextTool(ToolWidget):
    """
    Linetext Creation Tool.

    Adds a linetext, first point click then Text-Entry
    Obsolete, no longer needed. To make it fully usable we would need to translate 
    the usual editing keystrokes like cursor movements, delete etc. As of now 
    the only editing characters supported are backspace and some other 
    editing characters to introduce linebreaks
    """

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.p1 = None
        self.node = None
        self.color = None
        self.tsize = 0
        self.vtext = ""
        self.anim_count = 0
        self.last_anim = 0
        self.scene.context.setting(float, "last_font_size", float(Length("20px")))

    def process_draw(self, gc: wx.GraphicsContext):
        # We just draw a cursor rectangle...
        if self.p1 is not None:
            cursorwidth = float(Length("1mm"))
            cursorheight = float(Length("8mm"))
            offsetx = 0
            offsety = 0
            x0 = self.p1.real + offsetx
            y0 = self.p1.imag - cursorheight
            elements = self.scene.context.elements

            if self.node is None or self.node.bounds is None:
                # if self.node is not None:
                #     if hasattr(self.node, "mkfont"):
                #         fname = self.node.mkfont
                #         if fname.lower().endswith(".jhf"):
                #             offsety = 0.5 * cursorheight

                if elements.default_stroke is None:
                    self.color = Color("black")
                else:
                    self.color = elements.default_stroke
                if elements.default_stroke is None:
                    self.pen.SetColour(wx.BLUE)
                else:
                    self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
            else:
                self.color = self.node.stroke
                if (
                    hasattr(self.node, "_line_information")
                    and len(self.node._line_information) > 0
                ):
                    # This is a list of tuples with (startx, starty, length, height per line)
                    (
                        line_x,
                        line_y,
                        unscaled_w,
                        line_w,
                        line_h,
                    ) = self.node._line_information[-1]
                    # print (line_x, line_y, line_w, line_h)
                    line_x_end = line_x + line_w
                    line_y_end = line_y + line_h
                    p_start = self.node.matrix.point_in_matrix_space((line_x, -line_y))
                    p_end = self.node.matrix.point_in_matrix_space(
                        (line_x_end, -line_y_end)
                    )
                    # print (f"x0={p_start.x:.0f}, y0={p_start.y:.0f}, b0.x={self.node.bounds[0]:.0f}, b0.y={self.node.bounds[1]:.0f}")
                    # print (f"x1={p_end.x:.0f}, y1={p_end.y:.0f}, b1.x={self.node.bounds[2]:.0f}, b1.y={self.node.bounds[3]:.0f}")
                    x0 = p_end.x
                    y0 = p_start.y
                    cursorheight = (p_end.y - p_start.y) * 0.75
                else:
                    # offsetx = self.node.bounds[2] - self.node.bounds[0]
                    cursorheight = self.node.bounds[3] - self.node.bounds[1]
                    x0 = self.node.bounds[2]
                    y0 = self.node.bounds[1]
                # if hasattr(self.node, "mkfont"):
                #     fname = self.node.mkfont
                #     if fname.lower().endswith(".jhf"):
                #         offsety = 0.5 * cursorheight
                self.pen.SetColour(wx.Colour(swizzlecolor(self.node.stroke)))

            mycol = wx.Colour(swizzlecolor(self.color))
            self.pen.SetColour(mycol)
            gc.SetPen(self.pen)
            if self.anim_count == 0:
                self.anim_count = 1
                gc.SetBrush(wx.Brush(mycol, wx.BRUSHSTYLE_SOLID))
            else:
                self.anim_count = 0
                gc.SetBrush(wx.Brush(mycol, wx.BRUSHSTYLE_TRANSPARENT))
            gc.DrawRectangle(x0, y0, cursorwidth, cursorheight)

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        keycode=None,
        **kwargs,
    ):
        def done():
            self.p1 = None
            if self.node is not None:
                self.node.stroke = self.color
                self.node.altered()
                self.node.focus()
                self.scene.pane.tool_active = False
                self.scene.context.signal("element_property_update", [self.node])
                self.scene.request_refresh()
                self.scene.context.setting(float, "last_font_size")
                self.scene.context.last_font_size = self.node.mkfontsize
            self.node = None
            self.scene.context("tool none\n")
            self.scene.context("window close HersheyFontSelector\n")
            self.scene.context.signal("statusmsg", "")

        response = RESPONSE_CHAIN
        # if event_type == "key_up":
        #     print (f"Event {event_type}, Key: {keycode}, Modifiers: {modifiers}, text so far: {self.vtext}")
        if event_type == "leftdown":
            if self.p1 is None:
                self.scene.pane.tool_active = True
                self.scene.animate(self)
                elements = self.scene.context.elements
                if elements.default_stroke is None:
                    self.color = Color("black")
                else:
                    self.color = elements.default_stroke
                if nearest_snap is None:
                    sx, sy = self.scene.get_snap_point(
                        space_pos[0], space_pos[1], modifiers
                    )
                    self.p1 = complex(sx, sy)
                else:
                    self.p1 = complex(nearest_snap[0], nearest_snap[1])
                x = self.p1.real
                y = self.p1.imag
                self.vtext = "Text"
                fsize = self.scene.context.last_font_size
                self.node = self.scene.context.fonts.create_linetext_node(
                    x, y, self.vtext, font_size=fsize
                )
                if self.node is not None:
                    self.node.stroke = self.color
                    # _("Create text")
                    with elements.undoscope("Create text"):
                        elements.elem_branch.add_node(self.node)
                        self.scene.context.signal("element_added", self.node)
                        self.scene.context.signal(
                            "statusmsg",
                            _("Complete text-entry by pressing either Enter or Escape"),
                        )
                        if elements.classify_new:
                            elements.classify([self.node])
                    self.notify_created(self.node)
                    self.node.emphasized = False
                    self.scene.context("window open HersheyFontSelector\n")
                    # Refocus, to allow typing...
                    self.scene.gui.scene_panel.SetFocus()
                else:
                    # Node creation failed!
                    done()

            response = RESPONSE_CONSUME
        elif event_type == "doubleclick":
            done()
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            done()
            response = RESPONSE_CONSUME
        elif event_type == "key_up" and modifiers == "escape":
            if self.scene.pane.tool_active:
                done()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        elif event_type == "key_up" and modifiers == "return":
            if self.scene.pane.tool_active:
                done()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        elif event_type == "key_up":
            if self.scene.pane.tool_active:
                response = RESPONSE_CONSUME
                to_add = ""
                if keycode is not None:
                    to_add = keycode
                if modifiers == "ctrl+alt+l":
                    self.node.mkalign = "start"
                    to_add = ""
                if modifiers == "ctrl+alt+r":
                    self.node.mkalign = "end"
                    to_add = ""
                if modifiers == "ctrl+alt+c":
                    self.node.mkalign = "middle"
                    to_add = ""
                if modifiers == "ctrl+alt+b":
                    self.node.mkfontsize *= 1.2
                    to_add = ""
                if modifiers == "ctrl+alt+s":
                    self.node.mkfontsize /= 1.2
                    to_add = ""
                if modifiers == "ctrl+return":
                    to_add = "\n"
                if modifiers == "back":
                    to_add = ""
                    if len(self.vtext) > 0:
                        self.vtext = self.vtext[:-1]
                if len(to_add) > 0:
                    self.vtext += to_add
                # print(f"Keyup: {keycode} - {modifiers}: '{self.vtext}'")
                if self.node is None:
                    x = self.p1.real
                    y = self.p1.imag
                    fsize = self.scene.context.last_font_size
                    self.node = self.scene.context.fonts.create_linetext_node(
                        x,
                        y,
                        self.vtext,
                        font_size=fsize,
                    )
                    if self.node is not None:
                        self.node.emphasized = False

                    self.scene.request_refresh()
                else:
                    self.node.mktext = self.vtext
                    self.scene.context.signal("linetext", "text")
                # self.node.stroke = self.color
                # self.node.modified()
            else:
                response = RESPONSE_CHAIN
        return response

    # Animation logic
    def tick(self):
        if self.p1 is None:
            return False
        t = time()
        if t - self.last_anim > 0.5:
            self.last_anim = t
            self.scene.request_refresh_for_animation()

        return True

    def signal(self, signal, *args, **kwargs):
        def update_node():
            self.scene.context.fonts.update_linetext(self.node, self.node.mktext)
            self.node.emphasized = False
            self.scene.request_refresh()
            self.scene.gui.scene_panel.SetFocus()

        if self.node is None:
            return
        if signal == "linetext" and args[0] == "bigger":
            self.node.mkfontsize *= 1.2
            update_node()
        elif signal == "linetext" and args[0] == "smaller":
            self.node.mkfontsize /= 1.2
            update_node()
        elif signal == "linetext" and args[0] == "align":
            if len(args) > 1:
                align = args[1]
                self.node.mkalign = align
            update_node()
        elif signal == "linetext" and args[0] == "font":
            if len(args) > 1:
                font = args[1]
                from os.path import basename

                self.node.mkfont = basename(font)
            update_node()
        elif signal == "linetext" and args[0] == "text":
            self.scene.context.fonts.update_linetext(self.node, self.node.mktext)
            update_node()
