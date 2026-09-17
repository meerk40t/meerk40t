"""
The Balor live light (red dot) preview has to trace where the burn will go.

The preview and the burn are built from the same scene-to-device matrix, but the burn runs one
copy of the plan per enabled `place ...` operation. These tests pin the traced copies to the
coordinates the driver writes for the same selection.
"""

import os
import shutil
import tempfile
import unittest

from meerk40t.balormk.livelightjob import LiveLightJob
from meerk40t.core.geomstr import Geomstr
from meerk40t.core.units import Length
from test import bootstrap


class TestBalorLightJob(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.kernel = bootstrap.bootstrap(profile="MeerK40t_TEST_LIGHTJOB")
        self.addCleanup(self.close_kernel)
        self.kernel.console("service device start -i balor 0\n")
        self.device = self.kernel.device
        # Anything the profile restored as previous operations would show up as extra traced
        # copies, so start from a job with no placements at all.
        leftovers = [
            node
            for node in self.kernel.elements.ops()
            if node.type.startswith("place ")
        ]
        self.kernel.elements.remove_operations(leftovers)
        self.kernel.console("rect 20mm 20mm 20mm 10mm engrave -s 15\n")
        self.element = list(self.kernel.elements.elems())[-1]
        self.op = list(self.element.references)[-1].parent
        self.added = [self.element]
        self.set_emphasis()

    def close_kernel(self):
        """Drop what the test built before the tree is saved as the previous operations."""
        for node in self.added:
            if node.parent is not None:
                node.remove_node()
        self.kernel()

    # ---------- helpers ----------
    def set_emphasis(self, *nodes):
        """The elements the light job traces, plus the operations that get copied into the plan."""
        self.emphasis = [self.element, self.op] + list(nodes)
        self.kernel.elements.set_emphasis(self.emphasis)

    def place_point(self, x, y, corner=0):
        self.kernel.console(f"placement {x} {y} -c {corner}\n")
        node = [n for n in self.kernel.elements.ops() if n.type == "place point"][-1]
        self.added.append(node)
        self.set_emphasis(node)
        return node

    def place_current(self):
        self.kernel.console("current_position\n")
        node = [n for n in self.kernel.elements.ops() if n.type == "place current"][-1]
        self.added.append(node)
        self.set_emphasis(node)
        return node

    def place_point_in_group(self, x, y, corner=0):
        """A placement nested inside an operations group, as `planz copy` finds it."""
        from meerk40t.core.node.branch_ops import BranchOperationsNode
        from meerk40t.core.node.place_point import PlacePointNode

        group = BranchOperationsNode()
        self.kernel.elements.op_branch.add_node(group)
        node = PlacePointNode(x=x, y=y, corner=corner)
        group.add_node(node)
        self.added.extend([node, group])
        self.set_emphasis(node)
        return node

    def traced_copies(self, mode="bounds"):
        """The copies of the job the light job would trace, split at the rapid moves."""
        return [bounds for bounds, points in self.traced_points(mode)]

    def traced_points(self, mode="bounds"):
        """Like traced_copies, but handing back the points of every copy as well."""
        job = LiveLightJob(self.device, mode=mode, listen=False)
        getattr(job, f"update_{mode}")()
        copies = []
        current = []
        for point in job.points:
            if point is None:
                copies.append(current)
                current = []
            else:
                current.append(point)
        copies.append(current)
        return [(self.bounds_of(copy), copy) for copy in copies if copy]

    @staticmethod
    def bounds_of(points):
        xs = [point.real for point in points]
        ys = [point.imag for point in points]
        return min(xs), min(ys), max(xs), max(ys)

    def burn_coordinates(self):
        """The (x, y) positions the driver writes for the current selection."""
        filename = os.path.join(self.folder, "job.lmc")
        self.kernel.console(
            f'plan clear copy-selected preprocess validate blob preopt optimize save_job "{filename}"\n'
        )
        positions = set()
        with open(filename) as f:
            for line in f:
                words = line.split()
                if len(words) == 6 and words[0] in ("listJumpTo", "listMarkTo"):
                    positions.add((int(words[1], 16), int(words[2], 16)))
        return positions

    def burned(self, bounds, positions=None):
        """Does the driver write this traced copy at exactly these coordinates?"""
        if positions is None:
            positions = self.burn_coordinates()
        x0, y0, x1, y1 = bounds
        for corner in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            near = any(
                abs(x - corner[0]) <= 1 and abs(y - corner[1]) <= 1
                for x, y in positions
            )
            if not near:
                return False
        return True

    def assert_burned(self, bounds):
        self.assertTrue(
            self.burned(bounds), f"traced {bounds} is not written by the burn"
        )

    # ---------- tests ----------
    def test_trace_matches_burn_without_placement(self):
        """An absolute job is traced where it burns."""
        copies = self.traced_copies()
        self.assertEqual(len(copies), 1)
        self.assert_burned(copies[0])

    def test_trace_follows_job_start_placement(self):
        """A job start placement moves the traced copy onto the burned copy."""
        unplaced = self.traced_copies()[0]
        unplaced_positions = self.burn_coordinates()
        self.place_point("60mm", "60mm", corner=0)
        placed_positions = self.burn_coordinates()
        self.assertNotEqual(
            placed_positions, unplaced_positions, "the burn did not move"
        )
        matches = [
            copy for copy in self.traced_copies() if self.burned(copy, placed_positions)
        ]
        self.assertTrue(matches, "no traced copy sits on the burned copy")
        self.assertFalse(
            self.burned(matches[0], unplaced_positions),
            "the traced copy is still at the unplaced position",
        )

    def test_placement_corner_center_centers_the_trace(self):
        """Corner 4 puts the centre of the job on the placement point."""
        self.place_point("60mm", "60mm", corner=4)
        copy = self.traced_copies()[0]
        centre = ((copy[0] + copy[2]) / 2, (copy[1] + copy[3]) / 2)
        unit = Length("60mm", relative_length=self.device.view.unit_width).units
        expected = self.device.view.matrix.point_in_matrix_space((unit, unit))
        self.assertAlmostEqual(centre[0], expected[0], delta=1)
        self.assertAlmostEqual(centre[1], expected[1], delta=1)
        self.assert_burned(copy)

    def test_current_position_placement_follows_the_galvo(self):
        """A relative placement starts the job where the galvo currently points."""
        self.device.driver.native_x = 30000
        self.device.driver.native_y = 20000
        self.place_current()
        traced = [point for _, copy in self.traced_points() for point in copy]
        self.assertIn((30000, 20000), [(round(p.real), round(p.imag)) for p in traced])

    def test_disabled_placement_is_not_traced(self):
        """A switched off placement is not part of the job, so it is not traced."""
        unplaced = self.traced_copies()[0]
        node = self.place_point("60mm", "60mm", corner=0)
        node.output = False
        for copy in self.traced_copies():
            for seen, expected in zip(copy, unplaced):
                self.assertAlmostEqual(seen, expected, delta=1e-6)

    def test_each_placement_traces_its_own_copy(self):
        """Two placements are two copies of the job, each in its own place."""
        first = self.place_point("20mm", "20mm", corner=0)
        one_placed = self.traced_copies()
        second = self.place_point("70mm", "70mm", corner=0)
        self.set_emphasis(first, second)
        both_placed = self.traced_copies()
        # copies stay separate, so they do not merge into one box spanning both placements
        self.assertEqual(len(both_placed), len(one_placed) + 1)
        for copy in both_placed:
            self.assert_burned(copy)

    def test_placement_loops_trace_every_copy(self):
        """A placement with loops>1 has preprocess repeat its copies, so the trace repeats too."""
        node = self.place_point("60mm", "60mm", corner=0)
        single = self.traced_copies()
        node.loops = 3
        repeated = self.traced_copies()
        self.assertEqual(len(repeated), 3 * len(single))
        for copy in repeated:
            self.assert_burned(copy)

    def test_placement_inside_an_operations_group_is_traced(self):
        """A placement inside an operations group is part of the job, so the trace follows it."""
        unplaced = self.traced_copies()[0]
        unplaced_positions = self.burn_coordinates()
        self.place_point_in_group("60mm", "60mm", corner=0)
        placed_positions = self.burn_coordinates()
        self.assertNotEqual(placed_positions, unplaced_positions, "the burn did not move")
        matches = [
            copy for copy in self.traced_copies() if self.burned(copy, placed_positions)
        ]
        self.assertTrue(matches, "no traced copy sits on the burned copy")
        self.assertFalse(
            self.burned(matches[0], unplaced_positions),
            "the traced copy is still at the unplaced position",
        )

    def test_placement_outside_the_emphasis_follows_the_normal_job(self):
        """The preview models the job the Start button spools - `planN clear copy preprocess ...`,
        which takes every enabled operation - not the `copy-selected` job of the emphasis.
        """
        node = self.place_point("60mm", "60mm", corner=0)
        self.set_emphasis()  # element and op only: the placement stays enabled but unselected
        traced = self.traced_copies()[0]
        selected_positions = self.burn_coordinates()
        self.assertFalse(
            self.burned(traced, selected_positions),
            "the preview followed the selection instead of the enabled operations",
        )
        # Selecting the placement as well, the burn does write exactly that copy.
        self.set_emphasis(node)
        self.assert_burned(traced)

    def test_rotary_scale_is_applied_to_the_trace(self):
        """While the rotary is active the burn is scaled, so the trace has to be too."""
        unplaced = self.traced_copies()[0]
        self.device.rotary_active = True
        self.device.rotary_auto_length_scale = False
        self.device.rotary_auto_wrap_scale = False
        # a scale that shrinks the job, so it stays inside the 16 bit galvo range
        self.device.rotary_scale_x = 0.5
        self.device.rotary_scale_y = 0.5
        try:
            scaled = self.traced_copies()[0]
            self.assertNotEqual(scaled, unplaced)
            self.assert_burned(scaled)
        finally:
            self.device.rotary_active = False

    def test_raw_geometry_is_not_placed(self):
        """Raw geometry (the correction grid) is already device space and stays untouched."""
        raw = Geomstr.lines((100, 100), (200, 200))
        self.place_point("60mm", "60mm", corner=0)
        job = LiveLightJob(
            self.device, mode="geometry", geometry=raw, raw=True, listen=False
        )
        job.update_geometry()
        self.assertEqual(self.bounds_of(job.points), (100, 100, 200, 200))


if __name__ == "__main__":
    unittest.main()
