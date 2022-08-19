import wx

from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CONSUME, RESPONSE_DROP
from meerk40t.gui.scene.widget import Widget


def towards(a, b, amount):
    return amount * (b - a) + a


class CheckboxWidget(Widget):
    def __init__(
        self,
        scene,
        x,
        y,
        size=1,
        text=None,
        tool_tip=None,
        checked=None,
    ):
        size = size * scene.cell() / 2
        Widget.__init__(
            self,
            scene,
            x - size,
            y - size,
            x + size,
            y + size,
        )
        self.text = text
        self.checked = checked
        self.tool_tip = tool_tip
        self.value = False

        self.checkline_pen = wx.Pen()
        self.checkline_pen.SetColour(wx.CYAN)
        self.checkline_pen.SetWidth(4)

        self.font_color = wx.Colour()
        self.font_color.SetRGBA(0xFF000000)
        self.font = wx.Font(wx.SWISS_FONT)
        self.text_height = float("inf")
        self.text_width = float("inf")

        self._text_gap = 0.2

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        # Draw Box
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetPen(self.checkline_pen)
        gc.DrawRectangle(
            self.left, self.top, self.right - self.left, self.bottom - self.top
        )
        if self.value:
            # Draw Check
            gc.SetPen(self.checkline_pen)
            check = [(0.2, 0.5), (0.4, 0.75), (0.8, 0.2)]
            for i in range(len(check)):
                x, y = check[i]
                check[i] = towards(self.left, self.right, x), towards(
                    self.top, self.bottom, y
                )
            gc.DrawLines(check)

        if self.text:
            height = self.bottom - self.top
            width = self.right - self.left
            text_size = height * 3.0 / 4.0  # px to pt conversion
            try:
                self.font.SetFractionalPointSize(text_size)
            except AttributeError:
                self.font.SetPointSize(int(text_size))
            gc.SetFont(self.font, self.font_color)
            gc.DrawText(self.text, self.right + width * self._text_gap, self.top)

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type in ("hover", "hover_start", "hover_end"):
            if self.tool_tip:
                self.scene.toast(self.tool_tip)
            return RESPONSE_DROP
        if event_type == "leftdown":
            self.value = not self.value
            if self.checked:
                self.checked(self.value)
            self.scene.request_refresh()
        return RESPONSE_CONSUME
