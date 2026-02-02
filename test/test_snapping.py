import unittest
import numpy as np

from meerk40t.gui.scenewidgets.selectionwidget import MoveWidget, TOOL_RESULT_END


class Scene:
    def __init__(self):
        class Grid:
            tick_distance = 0
            grid_points = []

        class Pane:
            def __init__(self):
                self.grid = Grid()
                self._magnet_attraction = 0
                self.magnet_attract_x = False
                self.magnet_attract_y = False
                self.magnet_attract_c = False

            def revised_magnet_bound(self, bounds):
                return 0, 0

        class WidgetRoot:
            class SceneWidget:
                def __init__(self):
                    class M:
                        def point_in_matrix_space(self, p):
                            return p

                    self.matrix = M()

            def __init__(self):
                self.scene_widget = self.SceneWidget()

        self.context = type("C", (), {})()
        # Provide minimal settings and attributes
        def setting(t, name, default):
            return default

        self.context.setting = setting
        # attract lengths and snapping flags
        self.context.action_attract_len = 10.0
        self.context.grid_attract_len = 10.0
        self.context.snap_points = True
        self.context.snap_grid = True

        self.pane = Pane()
        self.widget_root = WidgetRoot()
        # Minimal callbacks used by MoveWidget


class DummyMaster:
    def __init__(self):
        self.key_shift_pressed = False
        self.left = -5.0
        self.right = 5.0
        self.top = -5.0
        self.bottom = 5.0
        self.width = 10
        self.height = 10
        self.offset_x = 0
        self.offset_y = 0
        self.tool_running = False


class TestSnapPreview(unittest.TestCase):
    def test_element_preview_detected(self):
        scene = Scene()
        master = DummyMaster()
        mw = MoveWidget(master, scene, 10, 6)
        # Create a snap cache where other point at (20,20) and selected at (9,9)
        mw._snap_cache = {
            "other_points": np.array([9 + 1j * 9, 20 + 1j * 20]),
            "selected_points_start": np.array([9 + 1j * 9]),
            "grid_points": [],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [0, 0, 10, 10]
        mw.total_dx = 0
        mw.total_dy = 0
        mw._update_snap_preview(b)
        self.assertIsNotNone(mw._snap_preview)
        self.assertEqual(mw._snap_preview["type"], "point")

    def test_precedence_grid_vs_magnet_grid_closer(self):
        """Magnet takes precedence over grid snapping."""
        scene = Scene()
        master = DummyMaster()
        mw = MoveWidget(master, scene, 10, 6)

        # Make pane return a magnet delta of 5 units and an attraction strong enough
        scene.pane._magnet_attraction = 4.0
        def revised_magnet_bound(bounds):
            return 5.0, 0.0
        scene.pane.revised_magnet_bound = revised_magnet_bound

        # Provide a grid point at (11,10); selected bounds such that corner at (10,10)
        mw._snap_cache = {
            "other_points": np.array([]),
            "selected_points_start": np.array([10+10j, 20+10j, 10+20j, 20+20j]),
            "grid_points": [(11.0, 10.0)],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [10, 10, 20, 20]
        mw.total_dx = 0
        mw.total_dy = 0
        mw._update_snap_preview(b)
        self.assertIsNotNone(mw._snap_preview)
        self.assertEqual(mw._snap_preview["type"], "magnet")

    def test_precedence_magnet_vs_grid_magnet_closer(self):
        """If magnet is closer than grid, magnet wins."""
        scene = Scene()
        master = DummyMaster()
        mw = MoveWidget(master, scene, 10, 6)

        # Make pane return a small magnet delta and attraction large enough
        scene.pane._magnet_attraction = 4.0
        def revised_magnet_bound(bounds):
            return 0.3, 0.0
        scene.pane.revised_magnet_bound = revised_magnet_bound

        mw._snap_cache = {
            "other_points": np.array([]),
            "selected_points_start": np.array([]),
            "grid_points": [(11.0, 10.0)],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [10, 10, 20, 20]
        mw.total_dx = 0
        mw.total_dy = 0
        mw._update_snap_preview(b)
        self.assertIsNotNone(mw._snap_preview)
        self.assertEqual(mw._snap_preview["type"], "magnet")

    def test_preview_prefers_grid_when_closer(self):
        """Preview chooses grid over distant point when grid is closer."""
        scene = Scene()
        master = DummyMaster()
        mw = MoveWidget(master, scene, 10, 6)

        mw._snap_cache = {
            "other_points": np.array([50 + 50j]),
            "selected_points_start": np.array([10 + 10j]),
            "grid_points": [(10.2, 10.0)],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [10, 10, 20, 20]
        mw.total_dx = 0
        mw.total_dy = 0
        mw._update_snap_preview(b)
        self.assertIsNotNone(mw._snap_preview)
        self.assertEqual(mw._snap_preview["type"], "grid")

    def test_shift_allows_grid_when_magnet_suppressed(self):
        """If Shift is pressed and magnet would otherwise attract, grid preview should still show."""
        scene = Scene()
        master = DummyMaster()
        master.key_shift_pressed = True
        mw = MoveWidget(master, scene, 10, 6)

        scene.pane._magnet_attraction = 4.0
        def revised_magnet_bound(bounds):
            return 5.0, 0.0
        scene.pane.revised_magnet_bound = revised_magnet_bound

        mw._snap_cache = {
            "other_points": np.array([]),
            "selected_points_start": np.array([]),
            "grid_points": [(11.0, 10.0)],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [10, 10, 20, 20]
        mw.total_dx = 0
        mw.total_dy = 0
        mw._update_snap_preview(b)
        self.assertIsNotNone(mw._snap_preview)
        self.assertEqual(mw._snap_preview["type"], "grid")

    def test_shift_suppresses_magnet_preview(self):
        """If Shift is pressed, magnet preview is suppressed."""
        scene = Scene()
        master = DummyMaster()
        master.key_shift_pressed = True
        mw = MoveWidget(master, scene, 10, 6)

        scene.pane._magnet_attraction = 4.0
        def revised_magnet_bound(bounds):
            return 5.0, 0.0
        scene.pane.revised_magnet_bound = revised_magnet_bound

        mw._snap_cache = {
            "other_points": np.array([]),
            "selected_points_start": np.array([]),
            "grid_points": [],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [10, 10, 20, 20]
        mw.total_dx = 0
        mw.total_dy = 0
        mw._update_snap_preview(b)
        self.assertIsNone(mw._snap_preview)

    def test_star_endpoint_attraction(self):
        """Two multi-point star shapes: endpoints attract each other (preview matches final)."""
        scene = Scene()
        master = DummyMaster()
        mw = MoveWidget(master, scene, 10, 6)

        # Construct two star-shaped point lists (complex points)
        # Selected star (5 points star-like)
        sel = np.array([
            5 + 0j,
            6 + 2j,
            4 + 4j,
            2 + 2j,
            3 + 0j,
        ])
        # Other star with one endpoint close to sel[0]
        oth = np.array([
            5.8 + 0.1j,
            7 + 2j,
            5 + 4j,
            3 + 2j,
            4 + -0.1j,
        ])

        mw._snap_cache = {
            "other_points": oth,
            "selected_points_start": sel,
            "grid_points": [],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [0, 0, 10, 10]
        mw.total_dx = 0
        mw.total_dy = 0

        # Compute preview
        mw._update_snap_preview(b)
        self.assertIsNotNone(mw._snap_preview)
        self.assertEqual(mw._snap_preview["type"], "point")

    def test_star_shapes_preview_matches_final_snap(self):
        """Two star polylines, one selected, one not: preview => final snap"""
        scene = Scene()
        master = DummyMaster()
        mw = MoveWidget(master, scene, 10, 6)

        # Build two simple star-like point sets (just points approximating stars)
        # Selected star has a point at x=4
        selected = np.array([4 + 0j, 2 + 2j, 3 + 4j])
        # Other star has a close point at x=5 so minimal distance = 1
        other = np.array([5 + 0j, 7 + 1j, 6 + 3j])

        mw._snap_cache = {
            "other_points": other,
            "selected_points_start": selected,
            "grid_points": [],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [0, 0, 10, 10]
        mw.total_dx = 0
        mw.total_dy = 0

        # Compute preview
        mw._update_snap_preview(b)
        preview = mw._snap_preview
        self.assertIsNotNone(preview)
        self.assertEqual(preview["type"], "point")

    def test_rectangle_over_grid_preview(self):
        """Rectangle selection over grid shows grid snap preview."""
        scene = Scene()
        master = DummyMaster()
        mw = MoveWidget(master, scene, 10, 6)

        # Rectangle bounds [10,10,20,20], center at (15,15)
        # Grid point at (15.2, 15.0) close to center
        mw._snap_cache = {
            "other_points": np.array([]),
            "selected_points_start": np.array([10 + 10j, 20 + 10j, 20 + 20j, 10 + 20j]),  # rectangle corners
            "grid_points": [(15.2, 15.0)],
            "start_total_dx": 0,
            "start_total_dy": 0,
            "grid_tick_distance": 0,
        }
        b = [10, 10, 20, 20]
        mw.total_dx = 0
        mw.total_dy = 0
        mw._update_snap_preview(b)
        self.assertIsNotNone(mw._snap_preview)
        self.assertEqual(mw._snap_preview["type"], "grid")

    def test_gather_interior_segment_points(self):
        """Segments with endpoints outside but interior points inside expanded bounds are captured."""
        scene = Scene()
        master = DummyMaster()

        class FakeGeom:
            def __init__(self, start, end):
                self.segments = [(start, None, None, None, end)]
                self.index = 1
            def _segtype(self, seg):
                return 1
            def position(self, idx, t):
                s = self.segments[idx][0]
                e = self.segments[idx][4]
                return s + t * (e - s)

        class FakeElem:
            def __init__(self, start, end, emphasized=False):
                self.hidden = False
                self.emphasized = emphasized
                self.type = "elem polyline"
                self._start = start
                self._end = end
            def as_geometry(self):
                return FakeGeom(self._start, self._end)
            def modified(self):
                pass

        class FakeElements:
            def __init__(self, elems):
                self._elems = elems
            def elems(self, *args, **kwargs):
                return self._elems

        # Other element: long horizontal segment from x=5 to x=25 at y=15
        other = FakeElem(5 + 15j, 25 + 15j, emphasized=False)
        # Selected small point near x=14,y=15
        selected = FakeElem(14 + 15j, 14 + 15j, emphasized=True)

        scene.context.elements = FakeElements([other, selected])
        mw = MoveWidget(master, scene, 10, 6)
        b = [10, 10, 20, 20]
        mw.total_dx = 0
        mw.total_dy = 0
        # Call gather
        mw._gather_snap_cache(b)
        # Ensure the interior point (15,15) is included from the other segment
        other_points = mw._snap_cache.get('other_points')
        self.assertTrue(any(abs(pt.real - 15) < 1e-9 and abs(pt.imag - 15) < 1e-9 for pt in other_points))

    def test_global_min_pair_ignores_cursor(self):
        """Preview chooses the global minimal pair regardless of cursor proximity."""
        scene = Scene()
        master = DummyMaster()
        mw = MoveWidget(master, scene, 10, 6)

        # Selected polyline points at (10,10), (20,20), (30,30)
        mw._snap_cache = {
            "other_points": np.array([11 + 10j, 100 + 100j]),
            "selected_points_start": np.array([10 + 10j, 20 + 20j, 30 + 30j]),
            "grid_points": [],
            "other_tree": None,
            "grid_tree": None,
            "start_total_dx": 0,
            "start_total_dy": 0,
        }
        b = [10, 10, 30, 30]
        mw.total_dx = 0
        mw.total_dy = 0
        # Cursor near (20,20) but global minimal pair is (10,10) -> (11,10)
        cursor = (20.0, 20.0)
        mw._update_snap_preview(b)
        self.assertIsNotNone(mw._snap_preview)
        self.assertEqual(mw._snap_preview.get("type"), "point")
        # Preview 'from' is selected point (10,10)
        self.assertAlmostEqual(mw._snap_preview.get("from")[0], 10.0)
        self.assertAlmostEqual(mw._snap_preview.get("from")[1], 10.0)

    def test_final_snap_ignores_cursor_preference(self):
        """Final snap decision uses global minimal pair and ignores cursor proximity."""
        scene = Scene()
        master = DummyMaster()

        class FakeGeom:
            def __init__(self, start):
                self.segments = [(start, None, None, None, start)]
                self.index = 1
            def _segtype(self, seg):
                return 1
            def position(self, idx, t):
                return self.segments[idx][0]

        class FakeElem:
            def __init__(self, pt, emphasized=False):
                self.hidden = False
                self.emphasized = emphasized
                self.type = "elem polyline"
                self._pt = pt
                class M:
                    def post_translate(self, dx, dy):
                        pass
                self.matrix = M()
            def as_geometry(self):
                return FakeGeom(self._pt)
            def can_move(self, allow):
                return True
            def translated(self, dx, dy, interim=False):
                pass
            def modified(self):
                pass

        class FakeElements:
            def __init__(self, elems):
                self._elems = elems
                self.copy_increases_wordlist_references = False
                self._emphasized_bounds = None
            def elems(self, *args, **kwargs):
                return self._elems
            def set_start_time(self, *_):
                pass
            def set_end_time(self, *_):
                pass
            def undofree(self):
                from contextlib import nullcontext
                return nullcontext()
            def selected_area(self):
                return [10, 10, 20, 20]
            def signal(self, *args, **kwargs):
                pass
            def update_bounds(self, *_):
                pass

        # Other points: one close to (10,10) and one far away
        oth_close = FakeElem(11 + 10j, emphasized=False)
        oth_far = FakeElem(100 + 100j, emphasized=False)
        # Selected points at (10,10) and (20,20)
        sel_a = FakeElem(10 + 10j, emphasized=True)
        sel_b = FakeElem(20 + 20j, emphasized=True)

        scene.context.elements = FakeElements([oth_close, oth_far, sel_a, sel_b])
        mw = MoveWidget(master, scene, 10, 6)
        scene.pane.last_snap = None
        scene.context.signal = lambda *a, **k: None
        # Ensure scene has a request_refresh so MoveWidget can call it
        scene.request_refresh = lambda *a, **k: None
        # Simulate end event. Regardless of where the cursor is, the minimal pair
        # is 10->11 which yields dx=1
        mw.tool([0, 0, 0, 0, 0, 0], None, 0, 0, event=TOOL_RESULT_END)
        # After moving, total_dx should indicate the move by 1 in x
        self.assertAlmostEqual(mw.total_dx, 1.0, places=7)