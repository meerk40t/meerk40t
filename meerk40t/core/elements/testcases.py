from math import sqrt

from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.core.units import (
    UNITS_PER_MM,
    UNITS_PER_PIXEL,
    UNITS_PER_POINT,
    Angle,
    Length,
)
from meerk40t.kernel import CommandSyntaxError
from meerk40t.svgelements import (
    SVG_RULE_EVENODD,
    SVG_RULE_NONZERO,
    Color,
    Matrix,
    Path,
    Polygon,
    Polyline,
)
from meerk40t.tools.geomstr import Geomstr


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    def polybool_crash_test(channel, _):
        # rect_info = "M 30961.4173228,10320.4724409 L 474741.732283,10320.4724409 L 474741.732283,392177.952756 L 30961.4173228,392177.952756 L 30961.4173228,10320.4724409"
        # geom = Geomstr().svg(rect_info)
        # Testcase: polybool crash AttributeError: 'NoneType' object has no attribute 'next' for element difference
        data = []
        x_pos = 30961.4173228
        y_pos = 10320.4724409
        width = 474741.732283 - x_pos
        height = 392177.952756 - y_pos
        node1 = self.elem_branch.add(
            label = "Shape 1",
            x=x_pos,
            y=y_pos,
            width=width,
            height=height,
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            fill=self.default_fill,
            type="elem rect",
        )
        data.append(node1)
        geom = Geomstr()
        definition = (
            ((30961.417322839014,10320.472440944883), 
            (72243.30708661533,10320.472440944883)), 
            ((72243.30708661533,10320.472440944883), 
            (72243.30708661678,20640.944881889765)), 
            ((72243.30708661533,10320.472440944883), 
            (113525.19685039311,10320.472440944883)), 
            ((113525.19685039311,10320.472440944883), 
            (113525.19685039311,20640.944881889765)), 
            ((72243.30708661678,20640.944881889765), 
            (113525.19685039311,20640.944881889765)), 
            ((113525.19685039311,10320.472440944883), 
            (154807.08661416644,10320.472440944883)), 
            ((154807.08661416644,10320.472440944883), 
            (154807.08661417232,20640.944881889765)), 
            ((154807.08661417232,20640.944881889765), 
            (196088.97637794417,20640.944881889765)), 
            ((154807.08661416644,10320.472440944883), 
            (196088.97637794568,10320.472440944883)), 
            ((196088.97637794417,20640.944881889765), 
            (196088.97637794568,10320.472440944883)),
        )
        for s, e in definition:
            geom.line(complex(s[0], s[1]), complex(e[0], e[1]))
        node2 = self.elem_branch.add(
            label = "Shape 2",
            geometry=geom,
            stroke=self.default_stroke,
            stroke_width=self.default_strokewidth,
            fill=self.default_fill,
            type="elem path",
        )

        data.append(node2)
        return "elements", data

    @self.console_command(
        "test",
        output_type="elements",
    )
    def element_test(command, channel, _, data=None, post=None, **kwargs):
        # rect_info = "M 30961.4173228,10320.4724409 L 474741.732283,10320.4724409 L 474741.732283,392177.952756 L 30961.4173228,392177.952756 L 30961.4173228,10320.4724409"
        # geom = Geomstr().svg(rect_info)
        # Testcase: polybool crash AttributeError: 'NoneType' object has no attribute 'next' for element difference
        info, data = polybool_crash_test(channel, _)
        post.append(classify_new(data))
        return info, data
