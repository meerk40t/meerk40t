import wx

from meerk40t.core.units import Length
from meerk40t.extra.hershey import create_linetext_node, update_linetext
from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_ABORT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Color


class LineTextTool(ToolWidget):
    """
    Linetext Creation Tool.

    Adds a linetext, first point click then Text-Entry
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.p1 = None
        self.node = None
        self.color = None
        self.tsize = 0
        self.vtext = ""

    def process_draw(self, gc: wx.GraphicsContext):
        # We just draw a cursor rectangle...
        if self.p1 is not None:
            cursorwidth = float(Length("1mm"))
            cursorheight = float(Length("8mm"))
            offsetx = 0
            offsety = 0

            if self.node is None or self.node.bounds is None:
                if self.node is not None:
                    if hasattr(self.node, "font"):
                        fname = self.node.font
                        if fname.lower().endswith(".jhf"):
                            offsety = 0.5 * cursorheight

                if self.scene.context.elements.default_stroke is None:
                    self.color = Color("black")
                else:
                    self.color = self.scene.context.elements.default_stroke
                if self.scene.context.elements.default_stroke is None:
                    self.pen.SetColour(wx.BLUE)
                else:
                    self.pen.SetColour(
                        wx.Colour(
                            swizzlecolor(self.scene.context.elements.default_stroke)
                        )
                    )
            else:
                self.color = self.node.stroke
                offsetx = self.node.bounds[2] - self.node.bounds[0]
                cursorheight = self.node.bounds[3] - self.node.bounds[1]
                if hasattr(self.node, "font"):
                    fname = self.node.font
                    if fname.lower().endswith(".jhf"):
                        offsety = 0.5 * cursorheight
                self.pen.SetColour(wx.Colour(swizzlecolor(self.node.stroke)))

            x0 = self.p1.real + offsetx
            y0 = self.p1.imag - cursorheight + offsety

            mycol = wx.Colour(swizzlecolor(self.color))
            self.pen.SetColour(mycol)
            gc.SetPen(self.pen)
            gc.SetBrush(wx.Brush(mycol, wx.BRUSHSTYLE_SOLID))
            gc.DrawRectangle(x0, y0, cursorwidth, cursorheight)

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        def done():
            self.p1 = None
            if self.node is not None:
                self.node.stroke = self.color
                self.node.altered()
                self.node.focus()
                self.scene.tool_active = False
                self.scene.context.signal("element_property_update", [self.node])
                self.scene.request_refresh()
            self.node = None
            self.scene.context("tool none\n")
            self.scene.context("window close HersheyFontSelector\n")

        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            if self.p1 is None:
                self.scene.tool_active = True
                if self.scene.context.elements.default_stroke is None:
                    self.color = Color("black")
                else:
                    self.color = self.scene.context.elements.default_stroke
                if nearest_snap is None:
                    self.p1 = complex(space_pos[0], space_pos[1])
                else:
                    self.p1 = complex(nearest_snap[0], nearest_snap[1])
                x = self.p1.real
                y = self.p1.imag
                self.vtext = "Text"
                self.node = create_linetext_node(self.scene.context, x, y, self.vtext)
                self.node.stroke = self.color
                self.scene.context.elements.elem_branch.add_node(self.node)
                self.scene.context.signal("element_added", self.node)
                self.node.emphasized = False
                try:
                    curr_win = wx.GetActiveWindow()
                except:
                    curr_win = None
                self.scene.context("window open HersheyFontSelector\n")
                if curr_win is not None:
                    curr_win.SetFocus()

            response = RESPONSE_CONSUME
        elif event_type == "doubleclick":
            done()
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            done()
            response = RESPONSE_CONSUME
        elif event_type == "key_up" and modifiers == "escape":
            if self.scene.tool_active:
                done()
                # print ("Done - escape")
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        elif event_type == "key_up" and modifiers == "return":
            if self.scene.tool_active:
                done()
                # print ("Done - return")
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        elif event_type == "key_up":
            # print (f"down: {modifiers}")
            if self.scene.tool_active:
                response = RESPONSE_CONSUME
                to_add = ""
                if modifiers.startswith("shift+") and modifiers != "shift+":
                    to_add = modifiers[-1].upper()
                elif len(modifiers) == 1:
                    to_add = modifiers
                elif modifiers == "space":
                    to_add = " "
                elif modifiers == "back":
                    if len(self.vtext) > 0:
                        self.vtext = self.vtext[:-1]
                if len(to_add) > 0:
                    self.vtext += to_add
                # print(self.vtext)
                update_linetext(self.scene.context, self.node, self.vtext)
                # self.node.stroke = self.color
                # self.node.modified()
                self.node.emphasized = False

                self.scene.request_refresh()
            else:
                response = RESPONSE_CHAIN
        return response

    def signal(self, signal, *args, **kwargs):
        if self.node is None:
            return
        if signal == "linetext" and args[0] == "bigger":
            self.node.fontsize *= 1.2
            update_linetext(self.scene.context, self.node, self.node.text)
            self.node.emphasized = False
            self.scene.request_refresh()
        elif signal == "linetext" and args[0] == "smaller":
            self.node.fontsize /= 1.2
            update_linetext(self.scene.context, self.node, self.node.text)
            self.node.emphasized = False
            self.scene.request_refresh()
        elif signal == "linetext" and args[0] == "font":
            if len(args)>1:
                font = args[1]
                self.node.font = font
                update_linetext(self.scene.context, self.node, self.node.text)
                self.node.emphasized = False
                self.scene.request_refresh()
