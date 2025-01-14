"""
The ribbon tool includes a series of different animated physics based drawing methods dealing with the relationships
between different nodes. Each tick of animation each node performs its generic actions to update its positions.
Special care is taken to indicate how the drawing between the several nodes should take place.
"""

import math

import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.tools.geomstr import Geomstr


class RibbonNode:
    """
    Base RibbonNode class.
    """

    def __init__(self, ribbon):
        self.brush = wx.Brush(wx.RED)
        self.pen = wx.Pen(wx.BLUE)
        self.diameter = 5000
        self.ribbon = ribbon
        self.position = None

    def get(self, index):
        return self.ribbon.nodes[index].position

    def tick(self):
        pass

    def process_draw(self, gc: wx.GraphicsContext):
        if not self.position:
            return
        gc.PushState()
        gc.SetPen(self.pen)
        gc.SetBrush(self.brush)
        gc.DrawEllipse(self.position[0], self.position[1], self.diameter, self.diameter)
        gc.PopState()


class RetroNode(RibbonNode):
    """
    Position of node is the referenced nodes position <count> ticks ago. Or the average of the last <count> ticks.
    """

    def __init__(self, ribbon, retro_node, count, average=False):
        super().__init__(ribbon)
        self.retro_node = retro_node
        self.count = count
        self.average = average
        self._xs = []
        self._ys = []

    def tick(self):
        tracking_pos = self.get(self.retro_node)
        if tracking_pos is None:
            return
        self._xs.append(tracking_pos[0])
        self._ys.append(tracking_pos[1])
        if self.average:
            xs = sum(self._xs) / len(self._xs)
            ys = sum(self._ys) / len(self._ys)
            self.position = [xs, ys]
            if len(self._xs) >= self.count:
                self._xs.pop(0)
                self._ys.pop(0)
        else:
            self.position = None
            if len(self._xs) >= self.count:
                self.position = self._xs.pop(0), self._ys.pop(0)


class MidpointNode(RibbonNode):
    """
    Node's position is the average of the provided nodes positions.
    """

    def __init__(self, ribbon, nodes):
        super().__init__(ribbon)
        self.average_node = nodes
        self.ribbon = ribbon
        self.brush = wx.Brush(wx.RED)
        self.pen = wx.Pen(wx.BLUE)

    def tick(self):
        count = len(self.average_node)
        xs = 0
        ys = 0
        for node in self.average_node:
            pos = self.get(node)
            if pos is None:
                count -= 1
                continue
            xs += pos[0]
            ys += pos[1]
        if count == 0:
            self.position = None
            return
        self.position = xs / count, ys / count


class OffsetNode(RibbonNode):
    """
    Position is the referenced node's position plus a static offset.
    """

    def __init__(self, ribbon, offset_node, dx=0.0, dy=0.0):
        super().__init__(ribbon)
        self.offset_node = offset_node
        self.ribbon = ribbon
        self.brush = wx.Brush(wx.RED)
        self.pen = wx.Pen(wx.BLUE)
        self.dx = dx
        self.dy = dy

    def tick(self):
        pos = self.get(self.offset_node)
        if pos is None:
            self.position = None
            return
        self.position = pos[0] + self.dx, pos[1] + self.dy


class OrientationNode(RibbonNode):
    """
    Orientation node is a 5 node positional. It is located at the reference node. At some angle and some distance away.
    If a0, a1 are not given the angle is static at offset_angle.
    if d0, d1 are not given the radius is static at offset_radius.
    dx, dy are static offsets.
    """

    def __init__(
        self,
        ribbon,
        ref_node=0,
        a0=None,
        a1=None,
        d0=None,
        d1=None,
        dx=0.0,
        dy=0.0,
        offset_radius=0.0,
        offset_angle=0.0,
    ):
        super().__init__(ribbon)
        self.ref_node = ref_node
        self.a0 = a0
        self.a1 = a1
        self.d0 = d0
        self.d1 = d1
        self.dx = dx
        self.dy = dy
        self.offset_radius = offset_radius
        self.offset_angle = offset_angle

    def tick(self):
        ref_pos = self.get(self.ref_node)
        if ref_pos is None:
            # ref position is required.
            self.position = None
            return
        angle = self.offset_angle
        if self.a0 is not None and self.a1 is not None:
            a0 = self.get(self.a0)
            a1 = self.get(self.a1)
            if a0 is not None and a1 is not None:
                angle += Geomstr.angle(None, complex(*a0), complex(*a1))
        distance = self.offset_radius
        if self.d0 is not None and self.d1 is not None:
            d0 = self.get(self.d0)
            d1 = self.get(self.d1)
            if d0 is not None and d1 is not None:
                distance += Geomstr.distance(None, complex(*d0), complex(*d1))

        x = distance * math.cos(angle) + ref_pos[0] + self.dx
        y = distance * math.sin(angle) + ref_pos[1] + self.dy
        self.position = [x, y]


class GravityNode(RibbonNode):
    """
    Gravity node moves towards the node index it is attracted to at the given friction and attraction amount
    """

    def __init__(self, ribbon, attract_node=0):
        super().__init__(ribbon)
        self.friction = 0.05
        self.distance = 50
        self.attraction = 500
        self.velocity = [0.0, 0.0]
        self.attract_node = attract_node

    def tick(self):
        towards_pos = self.get(self.attract_node)
        if self.position is None:
            self.position = list(self.ribbon.position)
        vx = self.velocity[0] * (1 - self.friction)
        vy = self.velocity[1] * (1 - self.friction)
        if towards_pos is not None:
            angle = Geomstr.angle(None, complex(*towards_pos), complex(*self.position))
            vx -= self.attraction * math.cos(angle)
            vy -= self.attraction * math.sin(angle)

        self.velocity[0] = vx
        self.velocity[1] = vy
        self.position[0] += vx
        self.position[1] += vy


class PositionNode(RibbonNode):
    """
    Position node is simply the ribbon's last identified position as a node.
    """

    def __init__(self, ribbon):
        super().__init__(ribbon)
        self.ribbon = ribbon
        self.brush = wx.Brush(wx.RED)
        self.pen = wx.Pen(wx.BLUE)
        self.position = self.ribbon.position

    def tick(self):
        self.position = self.ribbon.position


class DrawSequence:
    """
    Draw sequence is what sort of drawn connections should occur between the different nodes and in what sequences.

    There are three levels of steps.
    1. The outermost is the series level and each series level step is drawn completely independent of any other series.
    These are disjointed paths.
    2. The step level is done in tick order.
    3. The indexes are performed in order during a tick.
    """

    def __init__(self, ribbon, sequences):
        self.series = {}
        self.tick_index = 0
        self.ribbon = ribbon
        self.pen = wx.Pen(wx.BLUE)
        self.sequences = sequences

    @classmethod
    def zig(cls, ribbon, zig=0, zag=1):
        """
        This is one path, [] and each is in a 4 tick sequence. The first sequence is 0 the second 0, third 1 and then 1
        So this draws between element 0, then element 0, then element 1, then element 1. Performing a zigzag.
        @param ribbon:
        @param zig:
        @param zag:
        @return:
        """
        return cls(ribbon, sequences=[[[zig], [zig], [zag], [zag]]])

    @classmethod
    def bounce(cls, ribbon, *args):
        return cls(ribbon, sequences=[[list(args)]])

    @classmethod
    def bounce_back(cls, ribbon, *args):
        return cls(ribbon, sequences=[[list(args), list(reversed(args))]])

    @classmethod
    def parallel(cls, ribbon, *args):
        sequence = [[[arg]] for arg in args]
        print(sequence)
        return cls(ribbon, sequences=sequence)

    def tick(self):
        """
        Process draw sequencing for the given tick.
        @return:
        """
        self.tick_index += 1
        for s, sequence in enumerate(self.sequences):
            series = self.series.get(s)
            if series is None:
                # Add series if not init
                series = []
                self.series[s] = series

            q = self.tick_index % len(sequence)
            seq = sequence[q]
            for i in seq:
                pos = self.ribbon.nodes[i].position
                if pos is None:
                    continue
                x, y = pos
                series.append((x, y))

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Draws the current sequence.
        @param gc:
        @return:
        """
        gc.SetPen(self.pen)
        for q in self.series:
            series = self.series[q]
            gc.StrokeLines(series)

    def get_path(self):
        """
        Get the sequence as a geomstr path.
        @return: geomstr return object
        """

        g = Geomstr()
        for q in self.series:
            series = self.series[q]
            g.polyline(points=[complex(x, y) for x, y in series])
        return g

    def clear(self):
        self.series.clear()


class Ribbon:
    def __init__(self):
        self.nodes = []
        self.sequence = DrawSequence.zig(self)
        self.position = None

    @classmethod
    def gravity_tool(cls):
        """
        Gravity tool is a position node and a single gravity node that moves towards it.
        @return:
        """
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(GravityNode(obj, 0))
        obj.sequence = DrawSequence.zig(obj)
        return obj

    @classmethod
    def smooth_gravity_tool(cls):
        """
        Gravity tool is a position node and a single gravity node that moves towards it.
        @return:
        """
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(RetroNode(obj, 0, 25, average=True))
        obj.nodes.append(GravityNode(obj, 1))

        obj.sequence = DrawSequence.zig(obj, 1, 2)
        return obj

    @classmethod
    def speed_zig_tool(cls):
        """
        @return:
        """
        obj = cls()
        obj.nodes.append(OrientationNode(obj, 2, 2, 3, 2, 3, offset_angle=math.tau / 4))
        obj.nodes.append(
            OrientationNode(obj, 2, 2, 3, 2, 3, offset_angle=-math.tau / 4)
        )
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(RetroNode(obj, 2, 5, average=True))
        obj.sequence = DrawSequence.zig(obj, 0, 1)
        return obj

    @classmethod
    def reverb_tool(cls):
        """
        @return:
        """
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(RetroNode(obj, 0, 20))
        return obj

    @classmethod
    def line_gravity_tool(cls):
        """
        Gravity line tool is a position node, being tracked by a gravity node, which in turn is tracked by another such
        node. The draw sequence bounces between the two gravity nodes.

        @return:
        """
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(GravityNode(obj, 0))
        obj.nodes.append(GravityNode(obj, 1))
        obj.sequence = DrawSequence.bounce(obj, 1, 2)
        return obj

    @classmethod
    def calligraphy_tool(cls):
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(OffsetNode(obj, 0, 10000, 10000))
        obj.sequence = DrawSequence.bounce_back(obj, 0, 1)
        return obj

    @classmethod
    def bendy_calligraphy_tool(cls):
        """
        B5,5B2,10kO5,3,4vvl100,100f0"
        @return:
        """
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(OffsetNode(obj, 0, 10000, 10000))
        obj.nodes.append(RetroNode(obj, 0, 5, average=True))
        obj.nodes.append(RetroNode(obj, 1, 10, average=True))
        obj.sequence = DrawSequence.bounce_back(obj, 2, 3)
        return obj

    @classmethod
    def crescent_tool(cls):
        """
        o3,4,120,100o3,4,0,100o3,4,-120,100kB5, 10B5,5f0"
        @return:
        """
        obj = cls()
        obj.nodes.append(
            OrientationNode(
                obj, 3, 3, 4, offset_angle=math.tau / 3, offset_radius=10000
            )
        )
        obj.nodes.append(
            OrientationNode(obj, 3, 3, 4, offset_angle=0, offset_radius=10000)
        )
        obj.nodes.append(
            OrientationNode(
                obj, 3, 3, 4, offset_angle=-math.tau / 3, offset_radius=10000
            )
        )
        obj.nodes.append(RetroNode(obj, 5, 10, average=True))
        obj.nodes.append(RetroNode(obj, 5, 5, average=True))
        obj.nodes.append(PositionNode(obj))

        obj.sequence = DrawSequence.bounce_back(obj, 0, 1, 2)
        return obj

    @classmethod
    def rake_tool(cls):
        """
        "f0B0,10o1,0,90,100s.3ns.6ns-.3ns-.6D2,3,1,4,5"
        @return:
        """
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(RetroNode(obj, 0, 10, average=True))

        obj.nodes.append(
            OrientationNode(
                obj, 1, 0, 1, offset_angle=math.tau / 4, offset_radius=10000
            )
        )
        obj.nodes.append(
            OrientationNode(obj, 1, 0, 1, offset_angle=math.tau / 4, offset_radius=5000)
        )
        obj.nodes.append(
            OrientationNode(
                obj, 1, 0, 1, offset_angle=math.tau / 4, offset_radius=-5000
            )
        )
        obj.nodes.append(
            OrientationNode(
                obj, 1, 0, 1, offset_angle=math.tau / 4, offset_radius=-10000
            )
        )
        obj.sequence = DrawSequence.parallel(obj, 2, 3, 1, 4, 5)

        return obj

    @classmethod
    def nudge_loop_tool(cls):
        obj = cls()
        obj.nodes.append(PositionNode(obj))
        obj.nodes.append(GravityNode(obj, 2))
        obj.nodes.append(GravityNode(obj, 3))
        obj.nodes.append(GravityNode(obj, 4))
        obj.nodes.append(MidpointNode(obj, [0, 1]))
        obj.sequence = DrawSequence.bounce_back(obj, 1, 2, 3)
        return obj

    def tick(self):
        """
        Delegate to nodes and sequence.
        @return:
        """
        for node in self.nodes:
            node.tick()
        self.sequence.tick()

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Delegate to nodes and sequence.
        @return:
        """
        for node in self.nodes:
            node.process_draw(gc)
        self.sequence.process_draw(gc)

    def get_path(self):
        """
        Delegate to sequence.
        @return:
        """
        return self.sequence.get_path()

    def clear(self):
        self.sequence.clear()


class RibbonTool(ToolWidget):
    """
    Ribbon Tool draws new segments by animating some click and press locations.
    """

    def __init__(self, scene, mode="gravity"):
        ToolWidget.__init__(self, scene)
        self.stop = False
        if mode == "gravity":
            self.ribbon = Ribbon.gravity_tool()
        elif mode == "line":
            self.ribbon = Ribbon.line_gravity_tool()
        elif mode == "smooth":
            self.ribbon = Ribbon.smooth_gravity_tool()
        elif mode == "speedzig":
            self.ribbon = Ribbon.speed_zig_tool()
        elif mode == "reverb":
            self.ribbon = Ribbon.reverb_tool()
        elif mode == "calligraphy":
            self.ribbon = Ribbon.calligraphy_tool()
        elif mode == "nudge":
            self.ribbon = Ribbon.nudge_loop_tool()
        elif mode == "bendy_calligraphy":
            self.ribbon = Ribbon.bendy_calligraphy_tool()
        elif mode == "rake":
            self.ribbon = Ribbon.rake_tool()
        elif mode == "crescent":
            self.ribbon = Ribbon.crescent_tool()
        else:
            self.ribbon = Ribbon.gravity_tool()

    def process_draw(self, gc: wx.GraphicsContext):
        self.ribbon.process_draw(gc)

    def tick(self):
        self.ribbon.tick()
        self.scene.request_refresh()
        if self.stop:
            return False
        return True

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        # We don't set tool_active here, as this can't be properly honored...
        # And we don't care about nearest_snap either...
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.stop = False
            self.ribbon.position = space_pos[:2]
            self.scene.animate(self)
            response = RESPONSE_CONSUME
        elif event_type == "move" or event_type == "hover":
            self.ribbon.position = space_pos[:2]
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            self.stop = True
            self.ribbon.clear()
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "leftup":
            self.stop = True
            t = self.ribbon.get_path()
            if not t:
                return RESPONSE_CONSUME
            elements = self.scene.context.elements
            # _("Create path")
            with elements.undoscope("Create path"):
                node = elements.elem_branch.add(
                    geometry=t,
                    type="elem path",
                    stroke_width=elements.default_strokewidth,
                    stroke=elements.default_stroke,
                    fill=elements.default_fill,
                )
                if elements.classify_new:
                    elements.classify([node])
            self.ribbon.clear()
            response = RESPONSE_CONSUME
        return response
