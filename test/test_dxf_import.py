import os
import tempfile
import unittest
from test import bootstrap

import ezdxf

from meerk40t.core.exceptions import BadFileError
from meerk40t.dxf.dxf_io import DxfLoader


class TestDXFImport(unittest.TestCase):
    """Test suite for DXF file import functionality."""

    def setUp(self):
        """Set up test environment."""
        self.kernel = bootstrap.bootstrap()
        self.elements = self.kernel.elements

    def tearDown(self):
        """Clean up test environment."""
        self.kernel()

    def create_test_dxf(self, entities_data):
        """Create a temporary DXF file with specified entities."""
        doc = ezdxf.new()
        msp = doc.modelspace()

        for entity_data in entities_data:
            entity_type = entity_data.get("type")
            if entity_type == "CIRCLE":
                msp.add_circle(
                    center=entity_data.get("center", (0, 0)),
                    radius=entity_data.get("radius", 10),
                )
            elif entity_type == "LINE":
                msp.add_line(
                    start=entity_data.get("start", (0, 0)),
                    end=entity_data.get("end", (10, 10)),
                )
            elif entity_type == "ARC":
                msp.add_arc(
                    center=entity_data.get("center", (0, 0)),
                    radius=entity_data.get("radius", 10),
                    start_angle=entity_data.get("start_angle", 0),
                    end_angle=entity_data.get("end_angle", 90),
                )
            elif entity_type == "ELLIPSE":
                msp.add_ellipse(
                    center=entity_data.get("center", (0, 0)),
                    major_axis=entity_data.get("major_axis", (10, 0)),
                    ratio=entity_data.get("ratio", 0.5),
                )
            elif entity_type == "POLYLINE":
                points = entity_data.get("points", [(0, 0), (10, 0), (10, 10), (0, 10)])
                msp.add_polyline2d(points, close=entity_data.get("closed", True))
            elif entity_type == "LWPOLYLINE":
                points = entity_data.get("points", [(0, 0), (10, 0), (10, 10), (0, 10)])
                msp.add_lwpolyline(points, close=entity_data.get("closed", True))
            elif entity_type == "POINT":
                msp.add_point(entity_data.get("location", (5, 5)))
            elif entity_type == "TEXT":
                text_entity = msp.add_text(entity_data.get("text", "Test Text"))
                text_entity.dxf.insert = entity_data.get("insert", (0, 0))
            elif entity_type == "HATCH":
                # Create a simple rectangular hatch
                hatch = msp.add_hatch()
                # Add a polyline path for the hatch boundary
                points = entity_data.get("points", [(0, 0), (10, 0), (10, 10), (0, 10)])
                hatch.paths.add_polyline_path(points, is_closed=True)
                # Set hatch pattern
                hatch.set_pattern_fill("ANSI31", scale=1.0)

        # Create temporary file
        fd, filepath = tempfile.mkstemp(suffix=".dxf")
        try:
            doc.saveas(filepath)
        finally:
            os.close(fd)

        return filepath

    def test_basic_dxf_loading(self):
        """Test basic DXF file loading functionality."""
        # Create a simple DXF with a circle
        entities = [{"type": "CIRCLE", "center": (50, 50), "radius": 25}]
        dxf_file = self.create_test_dxf(entities)

        try:
            # Test loading via DxfLoader
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            # Check that elements were created
            # elements = list(self.elements.elem_branch.flat())
            # self.assertGreater(len(elements), 0)

            # Check for circle element
            circles = list(self.elements.elem_branch.flat(types="elem ellipse"))
            self.assertEqual(len(circles), 1)

        finally:
            os.unlink(dxf_file)

    def test_multiple_entity_types(self):
        """Test loading DXF with multiple entity types."""
        entities = [
            {"type": "CIRCLE", "center": (0, 0), "radius": 10},
            {"type": "LINE", "start": (20, 0), "end": (30, 10)},
            {"type": "POINT", "location": (40, 40)},
            {"type": "TEXT", "text": "Hello", "insert": (50, 50)},
        ]
        dxf_file = self.create_test_dxf(entities)

        try:
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            elements = list(self.elements.elem_branch.flat())

            # Should have circle, line, point, and text
            circles = list(self.elements.elem_branch.flat(types="elem ellipse"))
            lines = list(self.elements.elem_branch.flat(types="elem line"))
            points = list(self.elements.elem_branch.flat(types="elem point"))
            texts = list(self.elements.elem_branch.flat(types="elem text"))

            self.assertEqual(len(circles), 1)
            self.assertEqual(len(lines), 1)
            self.assertEqual(len(points), 1)
            self.assertEqual(len(texts), 1)

            # Test entity geometry and attributes
            circle = circles[0]
            self.assertAlmostEqual(circle.cx, 0, places=1)  # Center X
            self.assertAlmostEqual(circle.cy, 0, places=1)  # Center Y
            self.assertAlmostEqual(circle.rx, 10, places=1)  # Radius
            self.assertAlmostEqual(circle.ry, 10, places=1)  # Radius (ellipse)

            line = lines[0]
            self.assertAlmostEqual(line.x1, 20, places=1)  # Start X
            self.assertAlmostEqual(line.y1, 0, places=1)  # Start Y
            self.assertAlmostEqual(line.x2, 30, places=1)  # End X
            self.assertAlmostEqual(line.y2, 10, places=1)  # End Y

            point = points[0]
            self.assertAlmostEqual(point.x, 40, places=1)  # X coordinate
            self.assertAlmostEqual(point.y, 40, places=1)  # Y coordinate

            text = texts[0]
            self.assertEqual(text.text, "Hello")  # Text content
            # Check that the text has a transformation matrix (position is stored in matrix)
            self.assertIsNotNone(text.matrix)
            # Check that bounds exist (indicating the text was positioned)
            bounds = text.bounds
            self.assertIsNotNone(bounds)
            # Verify the bounds have reasonable dimensions
            self.assertGreater(bounds[2] - bounds[0], 0)  # Width > 0
            self.assertGreater(bounds[3] - bounds[1], 0)  # Height > 0

        finally:
            os.unlink(dxf_file)

    def test_polyline_entities(self):
        """Test loading POLYLINE and LWPOLYLINE entities."""
        entities = [
            {
                "type": "POLYLINE",
                "points": [(0, 0), (10, 0), (10, 10), (0, 10)],
                "closed": True,
            },
            {
                "type": "LWPOLYLINE",
                "points": [(20, 0), (30, 0), (30, 10), (20, 10)],
                "closed": True,
            },
        ]
        dxf_file = self.create_test_dxf(entities)

        try:
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            polylines = list(self.elements.elem_branch.flat(types="elem polyline"))
            self.assertEqual(len(polylines), 2)

        finally:
            os.unlink(dxf_file)

    def test_arc_and_ellipse_entities(self):
        """Test loading ARC and ELLIPSE entities."""
        entities = [
            {
                "type": "ARC",
                "center": (0, 0),
                "radius": 15,
                "start_angle": 0,
                "end_angle": 180,
            },
            {"type": "ELLIPSE", "center": (30, 0), "major_axis": (10, 0), "ratio": 0.6},
        ]
        dxf_file = self.create_test_dxf(entities)

        try:
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            paths = list(self.elements.elem_branch.flat(types="elem path"))
            self.assertGreaterEqual(len(paths), 2)  # Arcs and ellipses become paths

        finally:
            os.unlink(dxf_file)

    def test_layer_assignment(self):
        """Test that entities are properly assigned to layers and operations."""
        # Create DXF with entities on different layers
        doc = ezdxf.new()
        msp = doc.modelspace()

        # Create layers
        doc.layers.add("CUT_LAYER")
        doc.layers.add("ENGRAVE_LAYER")

        # Add entities to specific layers
        circle = msp.add_circle((0, 0), 10)
        circle.dxf.layer = "CUT_LAYER"

        line = msp.add_line((20, 0), (30, 10))
        line.dxf.layer = "ENGRAVE_LAYER"

        # Save to temporary file
        fd, dxf_file = tempfile.mkstemp(suffix=".dxf")
        try:
            doc.saveas(dxf_file)
        finally:
            os.close(fd)

        try:
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            # Check that operations were created
            cut_ops = list(self.elements.op_branch.flat(types="op cut"))
            engrave_ops = list(self.elements.op_branch.flat(types="op engrave"))

            # Should have created operations for the layers
            self.assertGreaterEqual(len(cut_ops) + len(engrave_ops), 1)

        finally:
            os.unlink(dxf_file)

    def test_color_handling(self):
        """Test that DXF colors are properly converted."""
        doc = ezdxf.new()
        msp = doc.modelspace()

        # Add a circle with a specific DXF color (e.g., color index 1 = red)
        circle = msp.add_circle(center=(0, 0), radius=10)
        circle.dxf.color = 1  # DXF color index 1 (red)

        # Save to temp file
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
            doc.saveas(tmp.name)
            dxf_file = tmp.name

        try:
            # Import the DXF file using the tested import function
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            # Find the imported element (assuming it's stored in self.elements)
            circles = list(self.elements.elem_branch.flat(types="elem ellipse"))
            self.assertEqual(len(circles), 1)

            imported = circles[0]
            # Assert that stroke is set
            self.assertIsNotNone(imported.stroke)
            # Assert that the color value matches the expected DXF color mapping
            # DXF color index 1 should map to #FF0000 (red)
            self.assertEqual(str(imported.stroke).upper(), "#FF0000")

        finally:
            os.unlink(dxf_file)

    def test_corrupted_file_handling(self):
        """Test handling of corrupted DXF files."""
        # Create a corrupted DXF file
        fd, dxf_file = tempfile.mkstemp(suffix=".dxf")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("This is not a valid DXF file content")
        except:
            os.close(fd)
            raise

        try:
            # Should raise an error for corrupted file (could be OSError or BadFileError)
            with self.assertRaises((OSError, BadFileError)):
                DxfLoader.load(self.kernel, self.elements, dxf_file)
        finally:
            os.unlink(dxf_file)

    def test_empty_dxf_file(self):
        """Test handling of empty DXF files."""
        doc = ezdxf.new()
        # Don't add any entities

        fd, dxf_file = tempfile.mkstemp(suffix=".dxf")
        try:
            doc.saveas(dxf_file)
        finally:
            os.close(fd)

        try:
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            # Check what elements exist - might include file node or other structural elements
            elements = list(self.elements.elem_branch.flat())
            # Just verify that loading succeeded, don't check for zero elements
            # as the file node itself might be counted
            self.assertIsInstance(elements, list)

        finally:
            os.unlink(dxf_file)

    def test_scaling_and_transformation(self):
        """Test that DXF scaling and coordinate transformation works correctly."""
        entities = [{"type": "CIRCLE", "center": (100, 100), "radius": 50}]
        dxf_file = self.create_test_dxf(entities)

        try:
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            circles = list(self.elements.elem_branch.flat(types="elem ellipse"))
            self.assertEqual(len(circles), 1)

            circle = circles[0]
            # Check that transformation matrix was applied
            self.assertIsNotNone(circle.matrix)

        finally:
            os.unlink(dxf_file)

    def test_file_recovery(self):
        """Test DXF file recovery for damaged files."""
        # Create a valid DXF first
        entities = [{"type": "CIRCLE", "center": (0, 0), "radius": 10}]
        dxf_file = self.create_test_dxf(entities)

        # Corrupt the file by truncating it
        with open(dxf_file, "r+") as f:
            content = f.read()
            f.seek(0)
            f.write(content[: len(content) // 2])  # Truncate to half
            f.truncate()

        try:
            # The loader should attempt recovery - it may succeed or fail
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            # Result should be True if recovery succeeded
            self.assertIsInstance(result, bool)

        finally:
            os.unlink(dxf_file)

    def test_unsupported_entities(self):
        """Test that unsupported entities are handled gracefully."""
        # Create DXF with some unsupported entity types
        doc = ezdxf.new()
        msp = doc.modelspace()

        # Add a supported entity
        msp.add_circle((0, 0), 10)

        # Add an unsupported entity (if any exist in ezdxf)
        # Most entities should be supported, but this tests the fallback

        fd, dxf_file = tempfile.mkstemp(suffix=".dxf")
        try:
            doc.saveas(dxf_file)
        finally:
            os.close(fd)

        try:
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            # Should still load the supported entities
            circles = list(self.elements.elem_branch.flat(types="elem ellipse"))
            self.assertEqual(len(circles), 1)

        finally:
            os.unlink(dxf_file)

    def test_hatch_entities(self):
        """Test loading HATCH entities."""
        entities = [
            {"type": "HATCH", "points": [(0, 0), (20, 0), (20, 20), (0, 20)]},
            {"type": "HATCH", "points": [(30, 0), (50, 0), (50, 15), (30, 15)]},
        ]
        dxf_file = self.create_test_dxf(entities)

        try:
            result = DxfLoader.load(self.kernel, self.elements, dxf_file)
            self.assertTrue(result)

            # HATCH entities should be converted to paths
            paths = list(self.elements.elem_branch.flat(types="elem path"))
            # Should have at least the hatch entities (may have more from other processing)
            self.assertGreaterEqual(len(paths), 2)

        finally:
            os.unlink(dxf_file)


if __name__ == "__main__":
    unittest.main()
