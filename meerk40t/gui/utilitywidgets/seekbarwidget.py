import wx

from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CONSUME
from meerk40t.gui.scene.widget import Widget

BLIP_RADIUS = 20
MOVE_RADIUS = BLIP_RADIUS * 2


class SeekbarWidget(Widget):
    def __init__(
        self,
        scene,
        start_x,
        start_y,
        end_x,
        end_y,
        value_min,
        value_max,
        changed,
        clicked=None,
    ):
        size = scene.cell() / 2
        Widget.__init__(
            self,
            scene,
            min(start_x, end_x) - size,
            min(start_y, end_y) - size,
            max(start_x, end_x) + size,
            max(start_y, end_y) + size,
        )
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.changed = changed
        self.clicked = clicked

        self.values = []
        self.moving = False
        self.value_min = value_min
        self.value_max = value_max
        self.offset = self.value_min
        self.range = self.value_max - self.value_min
        self.seeker = -1
        self.text = None

        self.selected_pen = wx.Pen()
        self.selected_pen.SetColour(wx.CYAN)
        self.selected_pen.SetWidth(4)

        self.selected_brush = wx.Brush()
        self.selected_brush.SetColour(wx.CYAN)

        self.lacking_pen = wx.Pen()
        self.lacking_pen.SetWidth(2)
        self.lacking_pen.SetColour(wx.BLACK)  # medium gray

        self.lacking_brush = wx.Brush()
        self.lacking_brush.SetColour(wx.Colour().SetRGBA(0x88888888))

        self.value_brush = wx.Brush()
        self.value_brush.SetColour(wx.LIGHT_GREY)

        self.moving_brush = wx.Brush()
        self.moving_brush.SetColour(wx.BLUE)

        self.background_brush = wx.Brush()
        self.background_brush.SetColour(wx.WHITE)

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        gc.SetBrush(self.background_brush)
        gc.DrawRectangle(self.left, self.top, self.right, self.bottom)

        gc.SetBrush(self.lacking_brush)
        gc.SetPen(self.lacking_pen)
        gc.DrawLines([(self.start_x, self.start_y), (self.end_x, self.end_y)])
        for idx, value in enumerate(self.values):
            amount = self.value_to_position(value)

            tx = amount * (self.end_x - self.start_x) + self.start_x
            ty = amount * (self.end_y - self.start_y) + self.start_y
            gc.SetBrush(self.selected_brush)
            gc.SetPen(self.selected_pen)
            gc.DrawLines([(self.start_x, self.start_y), (tx, ty)])
            gc.DrawEllipse(
                tx - BLIP_RADIUS / 2, ty - BLIP_RADIUS / 2, BLIP_RADIUS, BLIP_RADIUS
            )
            if self.moving and self.seeker == idx:
                gc.SetBrush(self.moving_brush)
                gc.DrawEllipse(
                    tx - MOVE_RADIUS / 2,
                    ty - MOVE_RADIUS / 2,
                    MOVE_RADIUS,
                    MOVE_RADIUS,
                )
        if self.seeker != -1:
            try:
                gc.DrawText(
                    f"{self.values[self.seeker]:.2f}",
                    self.start_x,
                    self.start_y,
                )
            except IndexError:
                pass

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type in ("hover", "hover_start", "hover_end"):
            return
        ax = self.start_x
        ay = self.start_y
        bx = self.end_x
        by = self.end_y

        px = space_pos[0]
        py = space_pos[1]

        vAPx = px - ax
        vAPy = py - ay
        vABx = bx - ax
        vABy = by - ay
        sqDistanceAB = vABx * vABx + vABy * vABy
        ABAPproduct = vABx * vAPx + vABy * vAPy
        amount = ABAPproduct / sqDistanceAB
        if amount > 1:
            amount = 1
        if amount < 0:
            amount = 0
        value = self.position_to_value(amount)

        if event_type == "leftdown":
            # New down, find the closest seeker.
            self.seeker = -1
            self.moving = True

            best = float("inf")
            for idx, v in enumerate(self.values):
                current = abs(value - v)
                if current < best:
                    best = current
                    self.seeker = idx
        elif event_type in ("drop", "leftup"):
            # Stopping action.
            self.moving = False
            self.seeker = -1
            self.scene.request_refresh()
        elif event_type == "leftclick":
            if self.clicked:
                self.clicked(self.values, self.seeker)
            self.moving = False
            self.seeker = -1
            self.scene.request_refresh()

        if self.seeker != -1:
            self.values[self.seeker] = value
            self.changed(self.values, self.seeker)
            self.scene.request_refresh()
        return RESPONSE_CONSUME

    def add_value(self, value):
        self.values.append(value)

    def set_value(self, seeker, value):
        try:
            self.values[seeker] = value
            self.changed(self.values, seeker)
        except IndexError:
            pass

    def clear_values(self):
        self.values.clear()

    def value_to_position(self, value):
        return (value - self.offset) / self.range

    def position_to_value(self, amount):
        return self.offset + (amount * self.range)

    def set_text(self, text):
        self.text = text
