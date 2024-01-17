import time

import wx

from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CONSUME, RESPONSE_DROP
from meerk40t.gui.scene.widget import Widget


def towards(a, b, amount):
    return amount * (b - a) + a


class TextBoxWidget(Widget):
    def __init__(
        self,
        scene,
        x,
        y,
        width,
        height,
        text=None,
        tool_tip=None,
    ):
        Widget.__init__(
            self,
            scene,
            x - width,
            y - height,
            x + width,
            y + height,
        )
        self.active = False
        self.text = text
        self.tool_tip = tool_tip
        self.value = ""
        if text is not None:
            self.value = text

        self.outline_pen = wx.Pen()
        self.outline_pen.SetColour(wx.BLACK)
        self.outline_pen.SetWidth(4)

        self.background_brush = wx.Brush()
        self.background_brush.SetColour(wx.WHITE)

        self.font_color = wx.Colour()
        self.font_color.SetRGBA(0xFF000000)
        self.font = wx.Font(wx.SWISS_FONT)

        self.text_height = float("inf")
        self.text_width = float("inf")

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        # Draw Box
        gc.SetBrush(self.background_brush)
        gc.SetPen(self.outline_pen)
        gc.DrawRectangle(
            self.left, self.top, self.right - self.left, self.bottom - self.top
        )

        if self.text:
            height = self.bottom - self.top
            width = self.right - self.left
            text_size = height * 3.0 / 4.0  # px to pt conversion
            try:
                self.font.SetFractionalPointSize(text_size)
            except AttributeError:
                self.font.SetPointSize(int(text_size))
            gc.SetFont(self.font, self.font_color)
            draw_text = self.text
            if self.active and int(time.time() * 2) % 2 == 0:
                draw_text += "|"
            gc.DrawText(draw_text, self.left, self.top)

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        print(event_type)
        if event_type == "hover_start":
            if self.tool_tip:
                self.scene.toast(self.tool_tip)
            self.scene.cursor("text")
            return RESPONSE_CONSUME
        if event_type == "hover_end":
            print("Unset Arrow")
            self.scene.cursor("arrow")
            return RESPONSE_DROP
        if event_type == "leftdown":
            self.scene.animate(self)
            self.active = True
            print(space_pos)
        return RESPONSE_CONSUME

    def tick(self):
        print("Tick")
        # self.scene.request_refresh_for_animation()
        self.scene.request_refresh()
        return True
