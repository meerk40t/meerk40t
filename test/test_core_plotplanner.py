import random
import unittest

from PIL import Image, ImageDraw

from meerk40t.core.cutcode.cutcode import CutCode
from meerk40t.core.cutcode.linecut import LineCut
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.device.basedevice import PLOT_AXIS, PLOT_SETTING
from meerk40t.svgelements import Circle, Matrix, Path, Point


class TestPlotplanner(unittest.TestCase):
    # def test_plotplanner_constant_move_x(self):
    #     """
    #     With raster_smooth set to 1 we should smooth the x axis so that no y=0 occurs.
    #     @return:
    #     """
    #     settings = {"power": 1000, "_constant_move_x": True}
    #     plan = PlotPlanner(settings, ppi=False)
    #     plan.push(LineCut(Point(0, 0), Point(20, 2), settings=settings))
    #     plan.push(LineCut(Point(20, 2), Point(20, 5), settings=settings))
    #     plan.push(LineCut(Point(20, 5), Point(100, 10), settings=settings))
    #     last_x = None
    #     last_y = None
    #     for x, y, on in plan.gen():
    #         if on == 4:
    #             last_x = x
    #             last_y = y
    #         if on > 1:
    #             continue
    #         cx = x
    #         cy = y
    #         if cx is None:
    #             continue
    #         if last_x is not None:
    #             total_dx = cx - last_x
    #             total_dy = cy - last_y
    #             dx = 1 if total_dx > 0 else 0 if total_dx == 0 else -1
    #             dy = 1 if total_dy > 0 else 0 if total_dy == 0 else -1
    #             self.assertFalse(dx == 0)
    #             for i in range(1, max(abs(total_dx), abs(total_dy)) + 1):
    #                 nx = last_x + (i * dx)
    #                 ny = last_y + (i * dy)
    #                 # print(nx, ny, on)
    #         # print(x, y, on)
    #         last_x = cx
    #         last_y = cy
    #         print(f"Moving to {x} {y}")

    # def test_plotplanner_constant_move_x_ppi(self):
    #     """
    #     With raster_smooth set to 1 we should smooth the x axis so that no y=0 occurs.
    #     @return:
    #     """
    #     settings = {"power": 500, "_constant_move_x": True}
    #     plan = PlotPlanner(settings)
    #     plan.push(LineCut(Point(0, 0), Point(20, 2), settings=settings))
    #     plan.push(LineCut(Point(20, 2), Point(20, 5), settings=settings))
    #     plan.push(LineCut(Point(20, 5), Point(100, 10), settings=settings))
    #     last_x = None
    #     last_y = None
    #     last_on = None
    #     for x, y, on in plan.gen():
    #         if on == 4:
    #             last_x = x
    #             last_y = y
    #         if on > 1:
    #             continue
    #         if last_on is not None:
    #             self.assertNotEqual(last_on, on)
    #         last_on = on
    #         cx = x
    #         cy = y
    #         if cx is None:
    #             continue
    #         if last_x is not None:
    #             total_dx = cx - last_x
    #             total_dy = cy - last_y
    #             dx = 1 if total_dx > 0 else 0 if total_dx == 0 else -1
    #             dy = 1 if total_dy > 0 else 0 if total_dy == 0 else -1
    #             self.assertFalse(dx == 0)
    #             for i in range(1, max(abs(total_dx), abs(total_dy)) + 1):
    #                 nx = last_x + (i * dx)
    #                 ny = last_y + (i * dy)
    #                 # print(nx, ny, on)
    #         # print(x, y, on)
    #         last_x = cx
    #         last_y = cy
    #         # print(f"Moving to {x} {y}")

    # def test_plotplanner_constant_move_y(self):
    #     """
    #     With smooth_raster set to 2 we should never have x = 0. The x should *always* be in motion.
    #     @return:
    #     """
    #     settings = {"power": 1000, "_constant_move_y": True}
    #     plan = PlotPlanner(settings)
    #     plan.push(LineCut(Point(0, 0), Point(2, 20), settings=settings))
    #     plan.push(LineCut(Point(2, 20), Point(5, 20), settings=settings))
    #     plan.push(LineCut(Point(5, 20), Point(10, 100), settings=settings))
    #     last_x = None
    #     last_y = None
    #     for x, y, on in plan.gen():
    #         if on == 4:
    #             last_x = x
    #             last_y = y
    #         if on > 1:
    #             continue
    #         cx = x
    #         cy = y
    #         if cx is None:
    #             continue
    #         if last_x is not None:
    #             total_dx = cx - last_x
    #             total_dy = cy - last_y
    #             dx = 1 if total_dx > 0 else 0 if total_dx == 0 else -1
    #             dy = 1 if total_dy > 0 else 0 if total_dy == 0 else -1
    #             self.assertFalse(dy == 0)
    #             for i in range(0, max(abs(total_dx), abs(total_dy))):
    #                 nx = last_x + (i * dx)
    #                 ny = last_y + (i * dy)
    #                 # print(nx, ny, on)
    #
    #         last_x = cx
    #         last_y = cy
    #         print(f"Moving to {x} {y}")

    def test_plotplanner_constant_move_xy(self):
        """
        With raster_smooth set to 1 we should smooth the x axis so that no y=0 occurs.
        @return:
        """
        settings = {"power": 1000, "_constant_move_x": True, "_constant_move_y": True}
        plan = PlotPlanner(settings)
        self.constant_move_x = True
        self.constant_move_y = True
        for i in range(100):
            plan.push(
                LineCut(
                    Point(random.randint(0, 1000), random.randint(0, 1000)),
                    Point(random.randint(0, 1000), random.randint(0, 1000)),
                    settings=settings,
                )
            )
        last_x = None
        last_y = None
        for x, y, on in plan.gen():
            if on == 4:
                last_x = x
                last_y = y
            if on > 1:
                continue
            cx = x
            cy = y
            if cx is None:
                continue
            if last_x is not None:
                total_dx = cx - last_x
                total_dy = cy - last_y
                dx = 1 if total_dx > 0 else 0 if total_dx == 0 else -1
                dy = 1 if total_dy > 0 else 0 if total_dy == 0 else -1
                for i in range(1, max(abs(total_dx), abs(total_dy)) + 1):
                    nx = last_x + (i * dx)
                    ny = last_y + (i * dy)
                    # print(nx, ny, on)
            # print(x, y, on)
            last_x = cx
            last_y = cy
            print(f"Moving to {x} {y}")

    def test_plotplanner_constant_xy_end(self):
        """
        With raster_smooth set to 1 we should smooth the x axis so that no y=0 occurs.
        @return:
        """
        for q in range(100):
            settings = {
                "power": 1000,
                "constant_move_x": bool(random.randint(0, 1)),
                "constant_move_y": bool(random.randint(0, 1)),
            }
            plan = PlotPlanner(settings)
            goal_x = None
            goal_y = None
            for i in range(10):
                goal_x = random.randint(0, 100)
                goal_y = random.randint(0, 100)
                start_x = random.randint(0, 100)
                start_y = random.randint(0, 100)
                while start_x == goal_x and start_y == goal_y:
                    # If exactly equal go ahead and randomize again.
                    start_x = random.randint(0, 100)
                    start_y = random.randint(0, 100)
                plan.push(
                    LineCut(
                        Point(start_x, start_y),
                        Point(goal_x, goal_y),
                        settings=settings,
                    )
                )
            break_list = list(plan.queue)
            last_x = None
            last_y = None
            for x, y, on in plan.gen():
                if on == 4:
                    last_x = x
                    last_y = y
                if on > 1:
                    continue
                last_x = x
                last_y = y

            if last_x != goal_x:
                print(settings.get("constant_move_x"))
                print(settings.get("constant_move_y"))
                for seg in break_list:
                    print(repr(seg))
            self.assertEqual(last_x, goal_x)
            if last_y != goal_y:
                print(settings.get("constant_move_x"))
                print(settings.get("constant_move_y"))
                for seg in break_list:
                    print(repr(seg))
            self.assertEqual(last_y, goal_y)

    def test_plotplanner_static_issue(self):
        settings = {
            "power": 1000,
            "constant_move_x": True,
            "constant_move_y": False,
        }
        plan = PlotPlanner(settings)
        plan.debug = True
        lines = (
            ((41, 45), (14, 43)),
            ((32, 67), (32, 61)),
        )
        for line in lines:
            plan.push(
                LineCut(
                    Point(line[0][0], line[0][1]),
                    Point(line[1][0], line[1][1]),
                    settings=settings,
                )
            )
        goal_x = lines[-1][-1][0]
        goal_y = lines[-1][-1][1]
        break_list = list(plan.queue)
        last_x = None
        last_y = None
        for x, y, on in plan.gen():
            if on == 4:
                last_x = x
                last_y = y
            if on > 1:
                continue
            last_x = x
            last_y = y

        if last_x != goal_x:
            for seg in break_list:
                print(repr(seg))
        self.assertEqual(last_x, goal_x)
        if last_y != goal_y:
            for seg in break_list:
                print(repr(seg))
        self.assertEqual(last_y, goal_y)

    def test_plotplanner_constant_move_xy_rect(self):
        """
        With raster_smooth set to 1 we should smooth the x axis so that no y=0 occurs.
        @return:
        """
        settings = {"power": 1000, "constant_move_x": True, "constant_move_y": True}
        plan = PlotPlanner(settings)
        plan.push(LineCut(Point(0, 0), Point(0, 100), settings=settings))
        plan.push(LineCut(Point(0, 100), Point(100, 100), settings=settings))
        plan.push(LineCut(Point(100, 100), Point(100, 0), settings=settings))
        plan.push(LineCut(Point(100, 0), Point(0, 0), settings=settings))
        last_x = None
        last_y = None
        for x, y, on in plan.gen():
            if on == 4:
                last_x = x
                last_y = y
            if on > 1:
                continue
            cx = x
            cy = y
            if cx is None:
                continue
            if last_x is not None:
                total_dx = cx - last_x
                total_dy = cy - last_y
                dx = 1 if total_dx > 0 else 0 if total_dx == 0 else -1
                dy = 1 if total_dy > 0 else 0 if total_dy == 0 else -1
                for i in range(1, max(abs(total_dx), abs(total_dy)) + 1):
                    nx = last_x + (i * dx)
                    ny = last_y + (i * dy)
                    # print(nx, ny, on)
            # print(x, y, on)
            last_x = cx
            last_y = cy
            print(f"Moving to {x} {y}")

    def test_plotplanner_flush(self):
        """
        Intro test for plotplanner.

        This is needlessly complex.

        final value is "on", and provides commands.
        128 means settings were changed.
        64 indicates x_axis major
        32 indicates x_dir, y_dir
        256 indicates ended.
        1 means cut.
        0 means move.

        :return:
        """
        settings = {"power": 1000}
        plan = PlotPlanner(settings)

        for i in range(211):
            plan.push(LineCut(Point(0, 0), Point(5, 100), settings=settings))
            plan.push(LineCut(Point(100, 50), Point(0, 0), settings=settings))
            plan.push(LineCut(Point(50, -50), Point(100, -100), settings={"power": 0}))
            q = 0
            for x, y, on in plan.gen():
                # print(x, y, on)
                if q == i:
                    # for x, y, on in plan.process_plots(None):
                    # print("FLUSH!", x, y, on)
                    plan.clear()
                    break
                q += 1

    def test_plotplanner_walk_raster(self):
        """
        Test plotplanner operation of walking to a raster.

        PLOT_FINISH = 256
        PLOT_RAPID = 4
        PLOT_JOG = 2
        PLOT_SETTING = 128
        PLOT_AXIS = 64
        PLOT_DIRECTION = 32
        PLOT_LEFT_UPPER = 512
        PLOT_RIGHT_LOWER = 1024

        1 means cut.
        0 means move.

        :return:
        """

        rasterop = RasterOpNode()
        image = Image.new("RGBA", (256, 256))
        draw = ImageDraw.Draw(image)
        draw.ellipse((0, 0, 255, 255), "black")
        image = image.convert("L")
        inode = ImageNode(image=image, dpi=1000.0, matrix=Matrix())
        inode.step_x = 1
        inode.step_y = 1
        inode.process_image()
        rasterop.add_node(inode)
        rasterop.raster_step_x = 1
        rasterop.raster_step_y = 1

        vectorop = EngraveOpNode()
        vectorop.add_node(
            PathNode(path=Path(Circle(cx=127, cy=127, r=128)), fill="black")
        )
        cutcode = CutCode()
        cutcode.extend(vectorop.as_cutobjects())
        cutcode.extend(rasterop.as_cutobjects())
        settings = {"power": 500}
        plan = PlotPlanner(settings)
        for c in cutcode.flat():
            plan.push(c)

        setting_changed = False
        for x, y, on in plan.gen():
            if on > 2:
                if setting_changed:
                    # Settings change happens at vector to raster switch and must repost the axis.
                    self.assertEqual(on, PLOT_AXIS)
                if on == PLOT_SETTING:
                    setting_changed = True
                else:
                    setting_changed = False
