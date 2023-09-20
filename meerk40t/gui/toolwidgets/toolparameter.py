import math
import wx
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget


class ParameterTool(ToolWidget):
    """
    Parameter Tool displays parameter points and values of selected elements
    and allows to change them visually.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.element = None
        self.params = []
        self.paramtype = []
        self.mode = None
        self._index = -1

    def reset(self):
        self.params.clear()
        self.paramtype.clear()
        self.element = None
        self.mode = None
        self._index = -1
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False

    def establish_parameters(self, node):
        self.reset()
        self.element = node
        if self.element is None:
            return
        parameters = self.element.functional_parameter
        if parameters is None or len(parameters) < 3:
            return
        self.mode = parameters[0]
        idx = 1
        while idx < len(parameters):
            self.paramtype.append(parameters[idx])
            if parameters[idx] == 0:
                # point
                pt = (parameters[idx + 1], parameters[idx + 2])
                self.params.append(pt)
                idx += 1
            else:
                self.params.append(parameters[idx + 1])
            idx += 2

        self.scene.pane.tool_active = True
        self.scene.pane.modif_active = True

    def update_parameter(self):
        if self.element is None:
            return
        parameter = [self.mode]
        for d_type, d_data in zip(self.paramtype, self.params):
            parameter.append(d_type)
            if d_type == 0:
                parameter.append(d_data[0])
                parameter.append(d_data[1])
            else:
                parameter.append(d_data)
        self.element.functional_parameter = parameter

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        gc.PushState()
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s
        gc.SetPen(wx.RED_PEN)
        gc.SetBrush(wx.RED_BRUSH)
        for ptype, pdata in zip(self.paramtype, self.params):
            if ptype == 0:
                ptx = pdata[0]
                pty = pdata[1]
            gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)
        gc.PopState()

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
        """
        The routine dealing with propagated scene events

        Args:
            window_pos (tuple): The coordinates of the mouse position in window coordinates
            space_pos (tuple): The coordinates of the mouse position in scene coordinates
            event_type (string): [description]. Defaults to None.
            nearest_snap (tuple, optional): If set the coordinates of the nearest snap point in scene coordinates.
            modifiers (string): If available provides a  list of modifier keys that were pressed (shift, alt, ctrl).
            keycode (string): if available the keycode that was pressed

        Returns:
            Indicator how to proceed with this event after its execution (consume, chain etc)
        """
        try:
            pos = complex(*space_pos[:2])
        except TypeError:
            return RESPONSE_CONSUME
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s

        if event_type == "leftdown":
            xp = space_pos[0]
            yp = space_pos[1]
            self._index = -1
            w = offset * 4
            h = offset * 4
            idx = 0
            for d_type, d_entry in zip(self.paramtype, self.params):
                if d_type == 0:
                    ptx, pty = self.element.matrix.point_in_matrix_space(d_entry)
                    x = ptx - 2 * offset
                    y = pty - 2 * offset
                    if x <= xp <= x + w and y <= yp <= y + h:
                        self._index = idx
                        break
                idx += 1
            return RESPONSE_CONSUME
        elif event_type == "move":
            if self._index >= 0:
                self.params[self._index] = (space_pos[0], space_pos[1])
                self.update_parameter()
                if self.mode == "circle":
                    self.scene.context.elements.update_node_circle(self.element)
                elif self.mode == "ellipse":
                    self.scene.context.elements.update_node_ellipse(self.element)
                self.scene.refresh_scene()
            return RESPONSE_CONSUME
        elif event_type == "leftup":
            return RESPONSE_CONSUME
        elif event_type == "rightdown":
            # We stop
            self.done()
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN

    def done(self):
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.suppress_selection = False
        self.reset()
        self.scene.context("tool none\n")

    def signal(self, signal, *args, **kwargs):
        """
        Signal routine for stuff that's passed along within a scene,
        does not receive global signals
        """
        selected_node = None
        if signal == "tool_changed":
            if len(args[0]) > 1 and args[0][1] == "parameter":
                for node in self.scene.context.elements.elems(emphasized=True):
                    if node.functional_parameter is not None:
                        selected_node = node
                        break
                if selected_node is None:
                    self.scene.pane.suppress_selection = False
                else:
                    self.scene.pane.suppress_selection = True
                self.establish_parameters(selected_node)
                self.scene.request_refresh()
            else:
                self.reset()
            return
        elif signal == "emphasized":
            for node in self.scene.context.elements.elems(emphasized=True):
                if node.functional_parameter is not None:
                    selected_node = node
                    break
            if selected_node is None:
                self.scene.pane.suppress_selection = False
            else:
                self.scene.pane.suppress_selection = True
            self.establish_parameters(selected_node)
            self.scene.request_refresh()

    def init(self, context):
        return

    def final(self, context):
        self.scene.pane.suppress_selection = False
