"""
Affinemover is a replacement for SelectionWidget. It performs the selected widget manipulations toggling itself in
place of the selectionwidget when `affinemover` console command is called. It's generally unusable but performs all
affine transformations on selected objects by moving three points either locked, mirrored, or anchored.
"""

import wx

from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.svgelements import Matrix


class AffineMover(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)

        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.BLUE)
        self._bounds = None
        self.point_1 = None
        self.point_2 = None
        self.point_4 = None
        self._matrix = None
        self._last_m = None
        self._locked_point = None
        self.lock_1 = 0
        self.lock_2 = 0
        self.lock_4 = 0

    def init(self, context):
        context.listen("emphasized", self.emphasis_changed)
        # Option to draw selection Handle outside of box to allow for better visibility

    def final(self, context):
        context.unlisten("emphasized", self.emphasis_changed)

    def emphasis_changed(self, origin, *arg):
        self._bounds = None

    def process_draw(self, gc: wx.GraphicsContext):
        bounds = self.scene.context.elements.selected_area()
        if bounds is None:
            self.point_1 = None
            self.point_2 = None
            self.point_4 = None
            return
        if self._bounds is None:
            primary = self.scene.context.elements.first_emphasized
            try:
                bounds = primary.bbox(transformed=False)
            except AttributeError:
                return
            matrix = primary.matrix
            left, top, right, bottom = bounds
            min_x = min(right, left)
            min_y = min(top, bottom)
            max_x = max(right, left)
            max_y = max(top, bottom)
            self.point_1 = matrix.point_in_matrix_space([min_x, min_y])
            self.point_2 = matrix.point_in_matrix_space([max_x, min_y])
            self.point_4 = matrix.point_in_matrix_space([min_x, max_y])
        self._bounds = bounds
        gc.PushState()
        gc.SetPen(self.tool_pen)
        buffer = 2000
        try:
            if self.lock_1 == 1:
                gc.SetBrush(wx.GREEN_BRUSH)
            if self.lock_1 == -1:
                gc.SetBrush(wx.BLUE_BRUSH)
            else:
                gc.SetBrush(wx.RED_BRUSH)
            gc.DrawEllipse(
                self.point_1[0] - buffer,
                self.point_1[1] - buffer,
                2 * buffer,
                2 * buffer,
            )
            if self.lock_2 == 1:
                gc.SetBrush(wx.GREEN_BRUSH)
            elif self.lock_2 == -1:
                gc.SetBrush(wx.BLUE_BRUSH)
            else:
                gc.SetBrush(wx.RED_BRUSH)
            gc.DrawEllipse(
                self.point_2[0] - buffer,
                self.point_2[1] - buffer,
                2 * buffer,
                2 * buffer,
            )
            if self.lock_4 == 1:
                gc.SetBrush(wx.GREEN_BRUSH)
            elif self.lock_4 == -1:
                gc.SetBrush(wx.BLUE_BRUSH)
            else:
                gc.SetBrush(wx.RED_BRUSH)
            gc.DrawEllipse(
                self.point_4[0] - buffer,
                self.point_4[1] - buffer,
                2 * buffer,
                2 * buffer,
            )
        except TypeError:
            pass
        gc.PopState()

    def current_affine_matrix(self):
        """
            [a c  e]
            [b d  f]
            [0 0  1]

            [a b c]
            [d e f]
            [g h i]
        @return:
        """
        x1, y1 = self.point_1
        x2, y2 = self.point_2
        x4, y4 = self.point_4
        a = x4 - x1
        b = x2 - x1
        c = x1
        d = y4 - y1
        e = y2 - y1
        f = y1
        return Matrix(a, d, b, e, c, f)

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if self._bounds is None:
            return RESPONSE_DROP
        if self.point_1 is None:
            return RESPONSE_DROP
        if event_type == "move":
            if self._locked_point is None or self._matrix is None:
                return RESPONSE_DROP
            self.scene.toast(f"moving point {self._locked_point} to {space_pos[:2]}")
            if self._locked_point == 1:
                self.point_1 = list(space_pos[:2])
                self.point_2[0] += space_pos[4] * self.lock_2
                self.point_2[1] += space_pos[5] * self.lock_2
                self.point_4[0] += space_pos[4] * self.lock_4
                self.point_4[1] += space_pos[5] * self.lock_4
            elif self._locked_point == 2:
                self.point_2 = list(space_pos[:2])
                self.point_1[0] += space_pos[4] * self.lock_1
                self.point_1[1] += space_pos[5] * self.lock_1
                self.point_4[0] += space_pos[4] * self.lock_4
                self.point_4[1] += space_pos[5] * self.lock_4
            elif self._locked_point == 4:
                self.point_4 = list(space_pos[:2])
                self.point_1[0] += space_pos[4] * self.lock_1
                self.point_1[1] += space_pos[5] * self.lock_1
                self.point_2[0] += space_pos[4] * self.lock_2
                self.point_2[1] += space_pos[5] * self.lock_2
            matrix = self.current_affine_matrix()
            try:
                m = ~self._matrix * matrix
                for r in self.scene.context.elements.flat(emphasized=True):
                    if not hasattr(r, "matrix"):
                        # Not a thing that transforms.
                        continue
                    if self._last_m is not None:
                        # We undo our last application of m, avoid compounding
                        r.matrix *= ~self._last_m
                    # Apply m
                    r.matrix *= Matrix(m)
                    r.modified()
                self._last_m = m
            except ZeroDivisionError:
                pass
            return RESPONSE_CONSUME
        elif event_type == "leftdown":
            if self.point_1 is None:
                return RESPONSE_DROP
            if abs(complex(*self.point_1) - complex(*space_pos[:2])) < 2000:
                self._locked_point = 1
            elif abs(complex(*self.point_2) - complex(*space_pos[:2])) < 2000:
                self._locked_point = 2
            elif abs(complex(*self.point_4) - complex(*space_pos[:2])) < 2000:
                self._locked_point = 4
            else:
                self._locked_point = None
                return RESPONSE_DROP
            self._matrix = self.current_affine_matrix()
            return RESPONSE_CONSUME
        elif event_type == "leftup":
            self._locked_point = None
            self._bounds = None
            self._last_m = None
            self.scene.request_refresh()
            return RESPONSE_CONSUME
        elif event_type == "leftclick":
            if self._locked_point == 1:
                self.lock_1 = ((self.lock_1 + 2) % 3) - 1
            elif self._locked_point == 2:
                self.lock_2 = ((self.lock_2 + 2) % 3) - 1
            elif self._locked_point == 4:
                self.lock_4 = ((self.lock_4 + 2) % 3) - 1
            self.scene.request_refresh()
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN

    def hit(self):
        if self._bounds is not None:
            return HITCHAIN_HIT
        else:
            return HITCHAIN_DELEGATE
