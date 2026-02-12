"""
Tests that validate all relevant attributes are correctly preserved
through copy(), backup_tree(), and restore_tree() operations.

Each node subclass is tested for:
1. Attribute value preservation after copy()
2. Deep-copy independence for mutable objects (matrix, stroke, fill, geometry)
3. Round-trip through backup_tree() / restore_tree()
4. Attribute preservation through the full undo/redo cycle
"""

import unittest
from copy import copy

from test.bootstrap import bootstrap

from meerk40t.core.geomstr import Geomstr
from meerk40t.core.node.node import Fillrule, Linejoin, Linecap
from meerk40t.svgelements import Color, Matrix


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_value_equal(tc, original, restored, attr, msg_prefix=""):
    """Assert attribute value equality, with type-aware comparison."""
    oval = getattr(original, attr)
    rval = getattr(restored, attr)
    if oval is None:
        tc.assertIsNone(rval, f"{msg_prefix}{attr}: expected None, got {rval!r}")
    elif isinstance(oval, (Matrix, Color, Geomstr)):
        tc.assertEqual(oval, rval, f"{msg_prefix}{attr} value mismatch")
    elif isinstance(oval, float):
        tc.assertAlmostEqual(
            oval, rval, places=6, msg=f"{msg_prefix}{attr} float mismatch"
        )
    else:
        tc.assertEqual(oval, rval, f"{msg_prefix}{attr} value mismatch")


def _assert_deep_independent(tc, original, copied, attr, msg_prefix=""):
    """Assert that a mutable attribute was deep-copied (different identity)."""
    oval = getattr(original, attr)
    cval = getattr(copied, attr)
    if oval is not None:
        tc.assertIsNot(
            oval,
            cval,
            f"{msg_prefix}{attr} should be a deep copy (different identity)",
        )


# ---------------------------------------------------------------------------
# Per-node-type copy attribute tests
# ---------------------------------------------------------------------------


class TestRectNodeCopy(unittest.TestCase):
    """Validate RectNode attribute preservation after copy."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.elem_branch.add(
            type="elem rect",
            x=10,
            y=20,
            width=300,
            height=400,
            rx=5,
            ry=7,
            stroke=Color("red"),
            fill=Color("blue"),
            stroke_width=2000.0,
            stroke_scale=True,
            label="TestRect",
        )

    def test_copy_preserves_scalars(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("x", "y", "width", "height", "rx", "ry"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "fill", "stroke_width", "stroke_scale", "label"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_enum_attrs(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("linejoin", "fillrule"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_matrix(self):
        node = self._make_node()
        node.matrix.post_translate(100, 200)
        c = copy(node)
        self.assertEqual(node.matrix, c.matrix)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("matrix", "stroke", "fill"):
            _assert_deep_independent(self, node, c, attr)

    def test_copy_mutation_independence(self):
        """Mutating the copy must not affect the original."""
        node = self._make_node()
        c = copy(node)
        c.matrix.post_translate(9999, 9999)
        c.stroke = Color("green")
        c.x = 77777
        self.assertNotEqual(node.matrix, c.matrix)
        self.assertNotEqual(node.stroke, c.stroke)
        self.assertNotEqual(node.x, c.x)

    def test_copy_preserves_tab_attrs(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("mktablength", "mktabpositions"):
            _assert_value_equal(self, node, c, attr)


class TestEllipseNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.elem_branch.add(
            type="elem ellipse",
            cx=100,
            cy=200,
            rx=50,
            ry=30,
            stroke=Color("green"),
            fill=Color("yellow"),
            stroke_width=1500.0,
            label="TestEllipse",
        )

    def test_copy_preserves_geometry(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("cx", "cy", "rx", "ry"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "fill", "stroke_width", "label"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("matrix", "stroke", "fill"):
            _assert_deep_independent(self, node, c, attr)


class TestLineNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.elem_branch.add(
            type="elem line",
            x1=0,
            y1=0,
            x2=1000,
            y2=2000,
            stroke=Color("black"),
            stroke_width=500.0,
            label="TestLine",
        )

    def test_copy_preserves_endpoints(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("x1", "y1", "x2", "y2"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "stroke_width", "label", "linecap", "linejoin"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("matrix", "stroke"):
            _assert_deep_independent(self, node, c, attr)


class TestPointNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.elem_branch.add(
            type="elem point",
            x=42,
            y=84,
            stroke=Color("red"),
            stroke_width=300.0,
            label="TestPoint",
        )

    def test_copy_preserves_position(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("x", "y"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "stroke_width", "label"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("matrix", "stroke"):
            _assert_deep_independent(self, node, c, attr)


class TestPathNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        g = Geomstr()
        g.line(complex(0, 0), complex(100, 100))
        g.line(complex(100, 100), complex(200, 0))
        return self.elements.elem_branch.add(
            type="elem path",
            geometry=g,
            stroke=Color("purple"),
            fill=Color("orange"),
            stroke_width=800.0,
            label="TestPath",
        )

    def test_copy_preserves_geometry(self):
        node = self._make_node()
        c = copy(node)
        self.assertEqual(node.geometry, c.geometry)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in (
            "stroke",
            "fill",
            "stroke_width",
            "stroke_scale",
            "linecap",
            "linejoin",
            "fillrule",
            "label",
        ):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("geometry", "matrix", "stroke", "fill"):
            _assert_deep_independent(self, node, c, attr)

    def test_geometry_mutation_independence(self):
        node = self._make_node()
        original_geom = copy(node.geometry)
        c = copy(node)
        c.geometry.line(complex(300, 300), complex(400, 400))
        self.assertEqual(node.geometry, original_geom)


class TestPolylineNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        g = Geomstr()
        g.line(complex(0, 0), complex(50, 50))
        g.line(complex(50, 50), complex(100, 0))
        return self.elements.elem_branch.add(
            type="elem polyline",
            geometry=g,
            stroke=Color("cyan"),
            stroke_width=600.0,
            label="TestPolyline",
        )

    def test_copy_preserves_geometry(self):
        node = self._make_node()
        c = copy(node)
        self.assertEqual(node.geometry, c.geometry)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "stroke_width", "label", "linecap", "linejoin"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("geometry", "matrix", "stroke"):
            _assert_deep_independent(self, node, c, attr)


class TestTextNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.elem_branch.add(
            type="elem text",
            text="Hello World",
            x=50,
            y=100,
            stroke=Color("black"),
            fill=Color("red"),
            font_size=24.0,
            font_family="Arial",
            font_weight=700,
            anchor="middle",
            label="TestText",
        )

    def test_copy_preserves_text_attrs(self):
        node = self._make_node()
        c = copy(node)
        for attr in (
            "text",
            "anchor",
            "baseline",
            "font_size",
            "font_family",
            "font_weight",
            "font_style",
            "font_variant",
            "font_stretch",
            "label",
        ):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "fill", "stroke_width", "stroke_scale"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_decorations(self):
        node = self._make_node()
        node.underline = True
        node.strikethrough = True
        c = copy(node)
        for attr in ("underline", "strikethrough", "overline"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("matrix", "stroke", "fill"):
            _assert_deep_independent(self, node, c, attr)


class TestEffectWarpCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.elem_branch.add(
            type="effect warp",
            stroke=Color("blue"),
            stroke_width=1000.0,
            label="TestWarp",
        )

    def test_copy_preserves_warp_points(self):
        node = self._make_node()
        node.p1 = complex(10, 20)
        node.p2 = complex(30, 40)
        node.d1 = complex(1, 2)
        c = copy(node)
        for attr in ("p1", "p2", "p3", "p4", "d1", "d2", "d3", "d4"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "stroke_width", "output", "autohide", "label"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke",):
            _assert_deep_independent(self, node, c, attr)


class TestEffectWobbleCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.elem_branch.add(
            type="effect wobble",
            stroke=Color("blue"),
            label="TestWobble",
        )

    def test_copy_preserves_wobble_attrs(self):
        node = self._make_node()
        c = copy(node)
        for attr in (
            "wobble_radius",
            "wobble_interval",
            "wobble_speed",
            "wobble_type",
            "output",
            "autohide",
            "label",
        ):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "stroke_width"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke",):
            _assert_deep_independent(self, node, c, attr)


class TestEffectHatchCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.elem_branch.add(
            type="effect hatch",
            stroke=Color("blue"),
            hatch_distance="2mm",
            hatch_angle="45deg",
            label="TestHatch",
        )

    def test_copy_preserves_hatch_attrs(self):
        node = self._make_node()
        c = copy(node)
        for attr in (
            "hatch_distance",
            "hatch_angle",
            "hatch_angle_delta",
            "hatch_type",
            "hatch_algorithm",
            "unidirectional",
            "include_outlines",
            "output",
            "label",
        ):
            _assert_value_equal(self, node, c, attr)

    def test_copy_preserves_style(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke", "stroke_width"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_deep_copies_mutables(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("stroke",):
            _assert_deep_independent(self, node, c, attr)


# ---------------------------------------------------------------------------
# Base Node attribute tests
# ---------------------------------------------------------------------------


class TestNodeBaseCopy(unittest.TestCase):
    """Test base Node attribute preservation common to all node types."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def test_copy_preserves_base_attrs(self):
        node = self.elements.elem_branch.add(
            type="elem rect",
            x=0,
            y=0,
            width=100,
            height=100,
            label="BaseTest",
            lock=True,
        )
        node.id = "test_id_123"
        c = copy(node)
        for attr in ("type", "id", "label", "lock"):
            _assert_value_equal(self, node, c, attr)

    def test_copy_detaches_from_tree(self):
        node = self.elements.elem_branch.add(
            type="elem rect", x=0, y=0, width=100, height=100
        )
        c = copy(node)
        self.assertIsNone(c._parent)
        self.assertIsNone(c._root)

    def test_copy_new_mutable_containers(self):
        node = self.elements.elem_branch.add(
            type="elem rect", x=0, y=0, width=100, height=100
        )
        c = copy(node)
        self.assertIsNot(node._children, c._children)
        self.assertIsNot(node._references, c._references)
        self.assertIsNot(node._points, c._points)
        self.assertIsNot(node._default_map, c._default_map)

    def test_copy_preserves_settings_dict(self):
        """Operation nodes (which have settings via Parameters mixin)
        should deep-copy their settings dict.  Element nodes don't
        normally have settings, so we test via an op node."""
        op = self.elements.op_branch.add(
            type="op cut", label="SettingsTest", speed=500, power=1000
        )
        # Operation nodes inherit Parameters which sets self.settings
        self.assertIsInstance(op.settings, dict)
        c = copy(op)
        # Values preserved
        self.assertEqual(c.settings.get("speed"), op.settings.get("speed"))
        # Independence: different dict objects
        self.assertIsNot(op.settings, c.settings)
        c.settings["speed"] = 99999
        self.assertNotEqual(op.settings.get("speed"), 99999)


# ---------------------------------------------------------------------------
# Backup / Restore round-trip tests
# ---------------------------------------------------------------------------


class TestBackupRestoreAttributes(unittest.TestCase):
    """Test that backup_tree + restore_tree preserves all node attributes."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _find_elem_branch(self, backup):
        """Find the elem branch in a backup snapshot."""
        for node in backup:
            if node.type == "branch elems":
                return node
        return None

    def test_rect_roundtrip(self):
        """Rect attributes survive backup→restore."""
        node = self.elements.elem_branch.add(
            type="elem rect",
            x=10,
            y=20,
            width=300,
            height=400,
            rx=5,
            ry=7,
            stroke=Color("red"),
            fill=Color("blue"),
            stroke_width=2000.0,
            label="RoundtripRect",
        )
        node.matrix.post_translate(50, 60)

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.type, "elem rect")
        for attr in (
            "x",
            "y",
            "width",
            "height",
            "rx",
            "ry",
            "stroke_width",
            "label",
            "linejoin",
            "fillrule",
        ):
            _assert_value_equal(self, node, restored, attr, "rect roundtrip: ")

        # Stroke and fill values
        self.assertEqual(node.stroke, restored.stroke)
        self.assertEqual(node.fill, restored.fill)
        # Matrix
        self.assertEqual(node.matrix, restored.matrix)

    def test_ellipse_roundtrip(self):
        node = self.elements.elem_branch.add(
            type="elem ellipse",
            cx=100,
            cy=200,
            rx=50,
            ry=30,
            stroke=Color("green"),
            fill=Color("yellow"),
            label="RoundtripEllipse",
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.type, "elem ellipse")
        for attr in ("cx", "cy", "rx", "ry", "label"):
            _assert_value_equal(self, node, restored, attr, "ellipse roundtrip: ")
        self.assertEqual(node.stroke, restored.stroke)
        self.assertEqual(node.fill, restored.fill)

    def test_line_roundtrip(self):
        node = self.elements.elem_branch.add(
            type="elem line",
            x1=10,
            y1=20,
            x2=300,
            y2=400,
            stroke=Color("black"),
            stroke_width=500.0,
            label="RoundtripLine",
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.type, "elem line")
        for attr in ("x1", "y1", "x2", "y2", "stroke_width", "label"):
            _assert_value_equal(self, node, restored, attr, "line roundtrip: ")
        self.assertEqual(node.stroke, restored.stroke)

    def test_path_roundtrip(self):
        g = Geomstr()
        g.line(complex(0, 0), complex(100, 100))
        g.line(complex(100, 100), complex(200, 0))
        node = self.elements.elem_branch.add(
            type="elem path",
            geometry=g,
            stroke=Color("purple"),
            fill=Color("orange"),
            label="RoundtripPath",
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.type, "elem path")
        self.assertEqual(node.geometry, restored.geometry)
        self.assertEqual(node.stroke, restored.stroke)
        self.assertEqual(node.fill, restored.fill)
        self.assertEqual(node.label, restored.label)

    def test_text_roundtrip(self):
        node = self.elements.elem_branch.add(
            type="elem text",
            text="Hello World",
            stroke=Color("black"),
            fill=Color("red"),
            font_size=24.0,
            font_family="Arial",
            font_weight=700,
            anchor="middle",
            label="RoundtripText",
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.type, "elem text")
        for attr in (
            "text",
            "anchor",
            "font_size",
            "font_family",
            "font_weight",
            "label",
        ):
            _assert_value_equal(self, node, restored, attr, "text roundtrip: ")
        self.assertEqual(node.stroke, restored.stroke)
        self.assertEqual(node.fill, restored.fill)

    def test_group_with_children_roundtrip(self):
        """Group structures survive backup→restore with children intact."""
        group = self.elements.elem_branch.add(type="group", label="TestGroup")
        child1 = group.add(
            type="elem rect",
            x=0,
            y=0,
            width=50,
            height=50,
            stroke=Color("red"),
            label="Child1",
        )
        child2 = group.add(
            type="elem rect",
            x=100,
            y=100,
            width=75,
            height=75,
            stroke=Color("blue"),
            label="Child2",
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored_group = self.elements.elem_branch.children[-1]
        self.assertEqual(restored_group.type, "group")
        self.assertEqual(restored_group.label, "TestGroup")
        self.assertEqual(len(restored_group.children), 2)

        r1, r2 = restored_group.children
        self.assertEqual(r1.label, "Child1")
        self.assertEqual(r1.type, "elem rect")
        self.assertEqual(r1.width, 50)
        self.assertEqual(r1.stroke, Color("red"))

        self.assertEqual(r2.label, "Child2")
        self.assertEqual(r2.type, "elem rect")
        self.assertEqual(r2.width, 75)
        self.assertEqual(r2.stroke, Color("blue"))

    def test_operation_roundtrip(self):
        """Operation node attributes survive backup→restore."""
        initial_count = len(self.elements.op_branch.children)
        op = self.elements.op_branch.add(
            type="op cut",
            label="TestCut",
            speed=500,
            power=1000,
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        # Find the operation we added (it's after the pre-existing ones)
        self.assertGreater(len(self.elements.op_branch.children), initial_count)
        restored_op = self.elements.op_branch.children[-1]
        self.assertEqual(restored_op.type, "op cut")
        self.assertEqual(restored_op.label, "TestCut")
        self.assertEqual(restored_op.speed, 500)
        self.assertEqual(restored_op.power, 1000)


# ---------------------------------------------------------------------------
# Undo/Redo attribute preservation tests (console commands)
# ---------------------------------------------------------------------------


class TestUndoRedoAttributePreservation(unittest.TestCase):
    """Test that attributes are correctly preserved through undo/redo cycles."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def test_rect_attrs_survive_undo_redo(self):
        """Rect created via console survives undo→redo with attributes intact."""
        initial_count = len(self.elements.elem_branch.children)
        self.kernel.console("rect 1cm 2cm 3cm 4cm\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count + 1)

        node = self.elements.elem_branch.children[-1]
        self.assertEqual(node.type, "elem rect")
        orig_width = node.width
        orig_height = node.height

        self.kernel.console("undo\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count)

        self.kernel.console("redo\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count + 1)

        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.type, "elem rect")
        self.assertEqual(restored.width, orig_width)
        self.assertEqual(restored.height, orig_height)

    def test_circle_attrs_survive_undo_redo(self):
        """Circle/ellipse created via console survives undo→redo."""
        initial_count = len(self.elements.elem_branch.children)
        self.kernel.console("circle 5cm 5cm 2cm\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count + 1)

        node = self.elements.elem_branch.children[-1]
        self.assertEqual(node.type, "elem ellipse")
        orig_rx = node.rx
        orig_ry = node.ry

        self.kernel.console("undo\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count)

        self.kernel.console("redo\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count + 1)

        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.type, "elem ellipse")
        self.assertEqual(restored.rx, orig_rx)
        self.assertEqual(restored.ry, orig_ry)

    def test_line_attrs_survive_undo_redo(self):
        """Line created via console survives undo→redo."""
        initial_count = len(self.elements.elem_branch.children)
        self.kernel.console("line 0 0 5cm 5cm\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count + 1)

        node = self.elements.elem_branch.children[-1]
        self.assertEqual(node.type, "elem line")
        orig_x1 = node.x1
        orig_y1 = node.y1
        orig_x2 = node.x2
        orig_y2 = node.y2

        self.kernel.console("undo\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count)

        self.kernel.console("redo\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count + 1)

        restored = self.elements.elem_branch.children[-1]
        self.assertEqual(restored.type, "elem line")
        self.assertEqual(restored.x1, orig_x1)
        self.assertEqual(restored.y1, orig_y1)
        self.assertEqual(restored.x2, orig_x2)
        self.assertEqual(restored.y2, orig_y2)

    def test_multiple_element_types_undo_redo(self):
        """Multiple element types created then undo-all / redo-all."""
        initial_count = len(self.elements.elem_branch.children)

        self.kernel.console("rect 0 0 1cm 1cm\n")
        self.kernel.console("circle 3cm 3cm 1cm\n")
        self.kernel.console("line 0 0 5cm 5cm\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count + 3)

        # Remember types
        types_before = [c.type for c in self.elements.elem_branch.children[initial_count:]]
        self.assertEqual(types_before, ["elem rect", "elem ellipse", "elem line"])

        # Undo all
        self.kernel.console("undo\n")
        self.kernel.console("undo\n")
        self.kernel.console("undo\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count)

        # Redo all
        self.kernel.console("redo\n")
        self.kernel.console("redo\n")
        self.kernel.console("redo\n")
        self.assertEqual(len(self.elements.elem_branch.children), initial_count + 3)

        types_after = [c.type for c in self.elements.elem_branch.children[initial_count:]]
        self.assertEqual(types_after, types_before)


# ---------------------------------------------------------------------------
# Deep-copy independence across full backup cycle
# ---------------------------------------------------------------------------


class TestBackupIndependence(unittest.TestCase):
    """Test that backup snapshots are fully independent of the live tree."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def test_mutating_live_tree_doesnt_affect_backup(self):
        """After backup, mutations to live tree don't bleed into snapshot."""
        self.elements.elem_branch.add(
            type="elem rect",
            x=10,
            y=20,
            width=100,
            height=200,
            stroke=Color("red"),
            fill=Color("blue"),
            label="Original",
        )
        backup = self.elements._tree.backup_tree()

        # Mutate the live tree
        live_node = self.elements.elem_branch.children[-1]
        live_node.x = 99999
        live_node.label = "Mutated"
        live_node.stroke = Color("green")
        live_node.matrix.post_scale(10, 10)

        # Check backup is unaffected
        for b in backup:
            if b.type == "branch elems":
                backup_node = b.children[-1]
                self.assertEqual(backup_node.x, 10)
                self.assertEqual(backup_node.label, "Original")
                self.assertEqual(backup_node.stroke, Color("red"))
                break
        else:
            self.fail("Could not find elem branch in backup")

    def test_mutating_backup_doesnt_affect_live(self):
        """After backup, mutations to backup don't affect live tree."""
        self.elements.elem_branch.add(
            type="elem rect",
            x=10,
            y=20,
            width=100,
            height=200,
            stroke=Color("red"),
            label="Original",
        )
        backup = self.elements._tree.backup_tree()

        # Mutate the backup
        for b in backup:
            if b.type == "branch elems":
                backup_node = b.children[-1]
                backup_node.x = 99999
                backup_node.label = "Mutated"
                backup_node.matrix.post_scale(10, 10)
                break

        # Live tree should be unaffected
        live_node = self.elements.elem_branch.children[-1]
        self.assertEqual(live_node.x, 10)
        self.assertEqual(live_node.label, "Original")

    def test_path_geometry_independence(self):
        """Path geometry is independent between backup and live tree."""
        g = Geomstr()
        g.line(complex(0, 0), complex(100, 100))
        self.elements.elem_branch.add(
            type="elem path",
            geometry=g,
            stroke=Color("purple"),
            label="GeoTest",
        )
        backup = self.elements._tree.backup_tree()

        # Mutate live geometry
        live_node = self.elements.elem_branch.children[-1]
        live_node.geometry.line(complex(200, 200), complex(300, 300))

        # Backup geometry should be unaffected
        for b in backup:
            if b.type == "branch elems":
                backup_node = b.children[-1]
                self.assertNotEqual(
                    live_node.geometry, backup_node.geometry
                )
                break


# ---------------------------------------------------------------------------
# Operation node copy attribute tests
# ---------------------------------------------------------------------------


class TestCutOpNodeCopy(unittest.TestCase):
    """Validate CutOpNode attribute preservation after copy."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.op_branch.add(
            type="op cut",
            label="TestCut",
            speed=42.5,
            power=750,
            frequency=30.0,
            passes=3,
            kerf=0.15,
            color=Color("red"),
        )

    def test_copy_preserves_parameters(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("speed", "power", "frequency", "passes", "kerf", "label"):
            _assert_value_equal(self, node, c, attr, "cut copy: ")

    def test_copy_preserves_settings_dict_values(self):
        node = self._make_node()
        c = copy(node)
        self.assertEqual(node.settings.get("speed"), c.settings.get("speed"))
        self.assertEqual(node.settings.get("power"), c.settings.get("power"))
        self.assertEqual(
            node.settings.get("frequency"), c.settings.get("frequency")
        )

    def test_copy_deep_copies_settings(self):
        node = self._make_node()
        c = copy(node)
        self.assertIsNot(node.settings, c.settings)

    def test_settings_mutation_independence(self):
        """Mutating copy's settings must not change original."""
        node = self._make_node()
        c = copy(node)
        c.speed = 999
        c.power = 111
        self.assertNotEqual(node.speed, 999)
        self.assertNotEqual(node.power, 111)
        # Also check settings dict directly
        self.assertNotEqual(node.settings.get("speed"), 999)
        self.assertNotEqual(node.settings.get("power"), 111)

    def test_copy_preserves_type(self):
        node = self._make_node()
        c = copy(node)
        self.assertEqual(c.type, "op cut")

    def test_copy_preserves_allowed_attributes(self):
        node = self._make_node()
        c = copy(node)
        self.assertEqual(node.allowed_attributes, c.allowed_attributes)
        # allowed_attributes list independence (stored in settings)
        if isinstance(c.allowed_attributes, list):
            self.assertIsNot(node.settings.get("allowed_attributes"),
                             c.settings.get("allowed_attributes"))


class TestEngraveOpNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.op_branch.add(
            type="op engrave",
            label="TestEngrave",
            speed=35.0,
            power=500,
            passes=2,
        )

    def test_copy_preserves_parameters(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("speed", "power", "passes", "label"):
            _assert_value_equal(self, node, c, attr, "engrave copy: ")

    def test_copy_deep_copies_settings(self):
        node = self._make_node()
        c = copy(node)
        self.assertIsNot(node.settings, c.settings)

    def test_settings_mutation_independence(self):
        node = self._make_node()
        c = copy(node)
        c.speed = 999
        self.assertNotEqual(node.speed, 999)


class TestRasterOpNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.op_branch.add(
            type="op raster",
            label="TestRaster",
            speed=150.0,
            power=800,
            raster_step_x=1,
            raster_step_y=1,
            bidirectional=True,
            overscan="1mm",
        )

    def test_copy_preserves_parameters(self):
        node = self._make_node()
        c = copy(node)
        for attr in (
            "speed",
            "power",
            "raster_step_x",
            "raster_step_y",
            "bidirectional",
            "label",
        ):
            _assert_value_equal(self, node, c, attr, "raster copy: ")

    def test_copy_deep_copies_settings(self):
        node = self._make_node()
        c = copy(node)
        self.assertIsNot(node.settings, c.settings)

    def test_settings_mutation_independence(self):
        node = self._make_node()
        c = copy(node)
        c.speed = 999
        c.power = 111
        self.assertNotEqual(node.speed, 999)
        self.assertNotEqual(node.power, 111)

    def test_copy_preserves_type(self):
        node = self._make_node()
        c = copy(node)
        self.assertEqual(c.type, "op raster")


class TestImageOpNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.op_branch.add(
            type="op image",
            label="TestImage",
            speed=150.0,
            power=600,
            dpi=500,
        )

    def test_copy_preserves_parameters(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("speed", "power", "dpi", "label"):
            _assert_value_equal(self, node, c, attr, "image copy: ")

    def test_copy_deep_copies_settings(self):
        node = self._make_node()
        c = copy(node)
        self.assertIsNot(node.settings, c.settings)

    def test_settings_mutation_independence(self):
        node = self._make_node()
        c = copy(node)
        c.speed = 999
        self.assertNotEqual(node.speed, 999)


class TestDotsOpNodeCopy(unittest.TestCase):
    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def _make_node(self):
        return self.elements.op_branch.add(
            type="op dots",
            label="TestDots",
            speed=35.0,
            power=300,
            dwell_time=50,
        )

    def test_copy_preserves_parameters(self):
        node = self._make_node()
        c = copy(node)
        for attr in ("speed", "power", "dwell_time", "label"):
            _assert_value_equal(self, node, c, attr, "dots copy: ")

    def test_copy_deep_copies_settings(self):
        node = self._make_node()
        c = copy(node)
        self.assertIsNot(node.settings, c.settings)

    def test_settings_mutation_independence(self):
        node = self._make_node()
        c = copy(node)
        c.speed = 999
        self.assertNotEqual(node.speed, 999)


# ---------------------------------------------------------------------------
# Operation backup/restore round-trip tests
# ---------------------------------------------------------------------------


class TestOpBackupRestoreAttributes(unittest.TestCase):
    """Test that operation node attributes survive backup→restore."""

    def setUp(self):
        self.kernel = bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        self.kernel()

    def test_cut_op_roundtrip(self):
        initial_count = len(self.elements.op_branch.children)
        op = self.elements.op_branch.add(
            type="op cut",
            label="RoundtripCut",
            speed=42.5,
            power=750,
            frequency=30.0,
            passes=3,
            kerf=0.15,
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.op_branch.children[-1]
        self.assertEqual(restored.type, "op cut")
        for attr in ("speed", "power", "frequency", "passes", "kerf", "label"):
            _assert_value_equal(self, op, restored, attr, "cut roundtrip: ")
        # Settings dict is independent
        self.assertIsNot(op.settings, restored.settings)

    def test_engrave_op_roundtrip(self):
        op = self.elements.op_branch.add(
            type="op engrave",
            label="RoundtripEngrave",
            speed=35.0,
            power=500,
            passes=2,
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.op_branch.children[-1]
        self.assertEqual(restored.type, "op engrave")
        for attr in ("speed", "power", "passes", "label"):
            _assert_value_equal(self, op, restored, attr, "engrave roundtrip: ")

    def test_raster_op_roundtrip(self):
        op = self.elements.op_branch.add(
            type="op raster",
            label="RoundtripRaster",
            speed=150.0,
            power=800,
            raster_step_x=1,
            raster_step_y=1,
            bidirectional=True,
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.op_branch.children[-1]
        self.assertEqual(restored.type, "op raster")
        for attr in ("speed", "power", "raster_step_x", "raster_step_y", "bidirectional", "label"):
            _assert_value_equal(self, op, restored, attr, "raster roundtrip: ")

    def test_image_op_roundtrip(self):
        op = self.elements.op_branch.add(
            type="op image",
            label="RoundtripImage",
            speed=150.0,
            power=600,
            dpi=500,
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.op_branch.children[-1]
        self.assertEqual(restored.type, "op image")
        for attr in ("speed", "power", "dpi", "label"):
            _assert_value_equal(self, op, restored, attr, "image roundtrip: ")

    def test_dots_op_roundtrip(self):
        op = self.elements.op_branch.add(
            type="op dots",
            label="RoundtripDots",
            speed=35.0,
            power=300,
            dwell_time=50,
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.op_branch.children[-1]
        self.assertEqual(restored.type, "op dots")
        for attr in ("speed", "power", "dwell_time", "label"):
            _assert_value_equal(self, op, restored, attr, "dots roundtrip: ")

    def test_op_settings_independence_after_restore(self):
        """Mutating restored op settings must not affect the backup."""
        op = self.elements.op_branch.add(
            type="op cut",
            label="IndependenceTest",
            speed=42.5,
            power=750,
        )

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored = self.elements.op_branch.children[-1]
        restored.speed = 999
        restored.power = 111

        # Take another backup — the first backup should be unaffected
        # The values in the first backup snapshot should not change
        for b in backup:
            if b.type == "branch ops":
                for child in b.children:
                    if child.label == "IndependenceTest":
                        self.assertNotEqual(child.speed, 999)
                        self.assertNotEqual(child.power, 111)
                        break

    def test_op_with_references_roundtrip(self):
        """Op with element references survives backup→restore."""
        elem = self.elements.elem_branch.add(
            type="elem rect",
            x=0, y=0, width=100, height=100,
            stroke=Color("red"),
            label="RefTarget",
        )
        op = self.elements.op_branch.add(
            type="op cut",
            label="RefOp",
            speed=10,
            power=1000,
        )
        op.add_reference(elem)
        self.assertEqual(len(op.children), 1)
        self.assertEqual(op.children[0].type, "reference")

        backup = self.elements._tree.backup_tree()
        self.elements._tree.restore_tree(backup)

        restored_op = None
        for child in self.elements.op_branch.children:
            if child.label == "RefOp":
                restored_op = child
                break
        self.assertIsNotNone(restored_op)
        self.assertEqual(restored_op.speed, 10)
        self.assertEqual(restored_op.power, 1000)
        # Reference child should be restored
        self.assertEqual(len(restored_op.children), 1)
        self.assertEqual(restored_op.children[0].type, "reference")


if __name__ == "__main__":
    unittest.main()
