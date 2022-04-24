"""
CutPlan contains code to process LaserOperations into CutCode objects which are spooled.

CutPlan handles the various complicated algorithms to optimising the sequence of CutObjects to:
*   Sort burns so that travel time is minimised
*   Do burns with multiple passes all at the same time (Merge Passes)
*   Sort burns for all operations at the same time rather than operation by operation
*   Ensure that elements inside closed cut paths are burned before the outside path
*   Group these inner burns so that one component on a sheet is completed before the next one is started
*   Ensure that non-closed paths are started from one of the ends and burned in one continuous burn
    rather than being burned in 2 or more separate parts
*   Split raster images in to self-contained areas to avoid sweeping over large empty areas
    including splitting into individual small areas if burn inner first is set and then recombining
    those inside the same curves so that raster burns are fully optimised.
"""

from copy import copy
from os import times
from time import time
from typing import Optional

from .node.elem_image import ImageNode
from ..image.actualize import actualize
from ..svgelements import Group, Matrix, Polygon, SVGElement, SVGImage, SVGText
from ..tools.pathtools import VectorMontonizer
from .cutcode import CutCode, CutGroup, CutObject, RasterCut
from .elements import elem_ref_nodes


class CutPlanningFailedError(Exception):
    pass


class CutPlan:
    """
    Cut Plan is a centralized class to modify plans with specific methods.
    """

    def __init__(self, name, planner):
        self.name = name
        self.context = planner
        self.plan = list()
        self.original = list()
        self.commands = list()
        self.channel = self.context.channel("optimize", timestamp=True)
        # self.setting(bool, "opt_rasters_split", True)

    def __str__(self):
        parts = list()
        parts.append(self.name)
        if len(self.plan):
            parts.append("#%d" % len(self.plan))
            for p in self.plan:
                try:
                    parts.append(p.__name__)
                except AttributeError:
                    parts.append(p.__class__.__name__)
        else:
            parts.append("-- Empty --")
        return " ".join(parts)

    def execute(self):
        # Using copy of commands, so commands can add ops.
        cmds = self.commands[:]
        self.commands.clear()
        try:
            for cmd in cmds:
                cmd()
        except AssertionError:
            raise CutPlanningFailedError("Raster too large.")

    def preprocess(self):
        """ "
        Preprocess stage, all small functions from the settings to the job.
        """
        context = self.context
        _ = context._
        rotary = context.rotary
        # ==========
        # before
        # ==========
        if context.prephysicalhome:
            if not rotary.rotary_enabled:
                self.plan.insert(0, context.lookup("plan/physicalhome"))
            else:
                self.plan.insert(0, _("Physical Home Before: Disabled (Rotary On)"))
        if context.prehome:
            if not rotary.rotary_enabled:
                self.plan.insert(0, context.lookup("plan/home"))
            else:
                self.plan.insert(0, _("Home Before: Disabled (Rotary On)"))
        # ==========
        # After
        # ==========
        if context.autohome:
            if not rotary.rotary_enabled:
                self.plan.append(context.lookup("plan/home"))
            else:
                self.plan.append(_("Home After: Disabled (Rotary On)"))
        if context.autophysicalhome:
            if not rotary.rotary_enabled:
                self.plan.append(context.lookup("plan/physicalhome"))
            else:
                self.plan.append(_("Physical Home After: Disabled (Rotary On)"))
        if context.autoorigin:
            self.plan.append(context.lookup("plan/origin"))
        if context.postunlock:
            self.plan.append(context.lookup("plan/unlock"))
        if context.autobeep:
            self.plan.append(context.lookup("plan/beep"))
        if context.autointerrupt:
            self.plan.append(context.lookup("plan/interrupt"))

        # ==========
        # Conditional Ops
        # ==========
        self.conditional_jobadd_strip_text()
        self.conditional_jobadd_scale()
        self.conditional_jobadd_make_raster()
        self.conditional_jobadd_actualize_image()

    def blob(self):
        """
        blob converts User operations to CutCode objects.

        In order to have CutCode objects in the correct sequence for merging we need to:
        1. Break operations into grouped sequences of LaserOperations and special operations.
           We can only merge within groups of Laser operations.
        2. The sequence of CutObjects needs to reflect merge settings
           Normal sequence is to iterate operations and then passes for each operation.
           With Merge ops and not Merge passes, we need to iterate on passes first and then ops within.
        """

        if not self.plan:
            return
        context = self.context

        grouped_plan = list()
        last_type = ""
        group = [self.plan[0]]
        for c in self.plan[1:]:
            if hasattr(c, "type"):
                c_type = c.type
            else:
                c_type = type(c).__name__
            if c_type.startswith("op") != last_type.startswith("op"):
                grouped_plan.append(group)
                group = []
            group.append(c)
            last_type = c_type
        grouped_plan.append(group)

        # If Merge operations and not merge passes we need to iterate passes first and operations second
        passes_first = context.opt_merge_ops and not context.opt_merge_passes
        blob_plan = list()
        for plan in grouped_plan:
            burning = True
            pass_idx = -1
            while burning:
                burning = False
                pass_idx += 1
                for op in plan:
                    if not hasattr(op, "type"):
                        blob_plan.append(op)
                        continue
                    if not op.type.startswith("op") or op.type == "op console":
                        blob_plan.append(op)
                        continue
                    if op.type == "op dots":
                        if pass_idx == 0:
                            blob_plan.append(op)
                        continue
                    copies = op.implicit_passes
                    if passes_first:
                        if pass_idx > copies - 1:
                            continue
                        copies = 1
                        burning = True
                    # Providing we do some sort of post-processing of blobs,
                    # then merge passes is handled by the greedy or inner_first algorithms
                    passes = 1
                    if context.opt_merge_passes and (
                        context.opt_nearest_neighbor or context.opt_inner_first
                    ):
                        passes = copies
                        copies = 1
                    for p in range(copies):
                        cutcode = CutCode(
                            op.as_cutobjects(
                                closed_distance=context.opt_closed_distance,
                                passes=passes,
                            ),
                            settings=op.settings,
                        )
                        if len(cutcode) == 0:
                            break
                        cutcode.constrained = (
                            op.type == "op cut" and context.opt_inner_first
                        )
                        cutcode.pass_index = pass_idx if passes_first else p
                        cutcode.original_op = op.type
                        blob_plan.append(cutcode)

        self.plan.clear()
        for blob in blob_plan:
            try:
                blob.jog_distance = context.opt_jog_minimum
                blob.jog_enable = context.opt_rapid_between
            except AttributeError:
                pass
            # We can only merge and check for other criteria if we have the right objects
            merge = (
                len(self.plan)
                and isinstance(self.plan[-1], CutCode)
                and isinstance(blob, CutObject)
            )
            # Override merge if opt_merge_passes is off, and pass_index do not match
            if (
                merge
                and not context.opt_merge_passes
                and self.plan[-1].pass_index != blob.pass_index
            ):
                merge = False
            # Override merge if opt_merge_ops is off, and operations original ops do not match
            # Same settings object implies same original operation
            if (
                merge
                and not context.opt_merge_ops
                and self.plan[-1].settings is not blob.settings
            ):
                merge = False
            # Override merge if opt_inner_first is off, and operation was originally a cut.
            if (
                merge
                and not context.opt_inner_first
                and self.plan[-1].original_op == "op cut"
            ):
                merge = False

            if merge:
                if blob.constrained:
                    self.plan[
                        -1
                    ].constrained = (
                        True  # if merge is constrained new blob is constrained.
                    )
                self.plan[-1].extend(blob)
            else:
                if isinstance(blob, CutObject) and not isinstance(blob, CutCode):
                    cc = CutCode([blob])
                    cc.original_op = blob.original_op
                    cc.pass_index = blob.pass_index
                    self.plan.append(cc)
                else:
                    self.plan.append(blob)

    def preopt(self):
        """
        Add commands for optimize stage.
        @return:
        """
        context = self.context
        has_cutcode = False
        for op in self.plan:
            try:
                if isinstance(op, CutCode):
                    has_cutcode = True
                    break
            except AttributeError:
                pass
        if not has_cutcode:
            return

        if context.opt_reduce_travel and (
            context.opt_nearest_neighbor or context.opt_2opt
        ):
            if context.opt_nearest_neighbor:
                self.commands.append(self.optimize_travel)
            if context.opt_2opt and not context.opt_inner_first:
                try:
                    # Check for numpy before adding additional 2opt
                    # pylint: disable=unused-import
                    import numpy as np

                    self.commands.append(self.optimize_travel_2opt)
                except ImportError:
                    pass

        elif context.opt_inner_first:
            self.commands.append(self.optimize_cuts)
        if context.opt_reduce_directions:
            pass
        if context.opt_remove_overlap:
            pass

    def optimize_travel_2opt(self):
        """
        Optimize travel 2opt at optimize stage on cutcode
        @return:
        """
        channel = self.context.channel("optimize", timestamp=True)
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                self.plan[i] = short_travel_cutcode_2opt(self.plan[i], channel=channel)

    def optimize_cuts(self):
        """
        Optimize cuts at optimize stage on cutcode
        @return:
        """
        channel = self.context.channel("optimize", timestamp=True)
        grouped_inner = self.context.opt_inner_first and self.context.opt_inners_grouped
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                if c.constrained:
                    self.plan[i] = inner_first_ident(c, channel=channel)
                    c = self.plan[i]
                self.plan[i] = inner_selection_cutcode(
                    c,
                    channel=channel,
                    grouped_inner=grouped_inner,
                )

    def optimize_travel(self):
        """
        Optimize travel at optimize stage on cutcode.
        @return:
        """
        last = None
        channel = self.context.channel("optimize", timestamp=True)
        grouped_inner = self.context.opt_inner_first and self.context.opt_inners_grouped
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                if c.constrained:
                    self.plan[i] = inner_first_ident(c, channel=channel)
                    c = self.plan[i]
                if last is not None:
                    cur = self.plan[i]
                    cur._start_x, cur._start_y = last
                self.plan[i] = short_travel_cutcode(
                    c,
                    channel=channel,
                    complete_path=self.context.opt_complete_subpaths,
                    grouped_inner=grouped_inner,
                )
                last = self.plan[i].end

    def strip_text(self):
        """
        Perform strip text on the current plan
        @return:
        """
        for k in range(len(self.plan) - 1, -1, -1):
            op = self.plan[k]
            if not hasattr(op, "type"):
                continue
            try:
                if op.type in ("op cut", "op engrave", "op hatch"):
                    for i, e in enumerate(list(op.children)):
                        if isinstance(e.object, SVGText):
                            e.remove_node()
                    if len(op.children) == 0:
                        del self.plan[k]
            except AttributeError:
                pass

    def strip_rasters(self):
        """
        Strip rasters if there is no method of converting vectors to rasters. Rasters must
        be stripped at the `validate` stage.
        @return:
        """
        stripped = False
        for k, op in enumerate(self.plan):
            if not hasattr(op, "type"):
                continue
            if op.type == "op raster":
                if len(op.children) == 1 and isinstance(op[0], SVGImage):
                    continue
                self.plan[k] = None
                stripped = True
        if stripped:
            p = [q for q in self.plan if q is not None]
            self.plan.clear()
            self.plan.extend(p)

    def _make_image_for_op(self, op):
        subitems = list(op.flat(types=elem_ref_nodes))
        reverse = self.context.elements.classify_reverse
        if reverse:
            subitems = list(reversed(subitems))
        objs = [s.object for s in subitems]
        bounds = Group.union_bbox(objs, with_stroke=True)
        if bounds is None:
            return None
        xmin, ymin, xmax, ymax = bounds
        step_x = op.raster_step_x
        step_y = op.raster_step_y
        make_raster = self.context.lookup("render-op/make_raster")
        image = make_raster(subitems, bounds, step_x=step_x, step_y=step_y)
        matrix = Matrix()
        matrix.post_scale(step_x, step_y)
        matrix.post_translate(xmin, ymin)
        image_node = ImageNode(None, image=image, matrix=matrix, step_x=step_x, step_y=step_y)
        return image_node

    def make_image(self):
        for op in self.plan:
            if not hasattr(op, "type"):
                continue
            if op.type == "op raster":
                if len(op.children) == 1 and isinstance(op.children[0], SVGImage):
                    continue
                image_node = self._make_image_for_op(op)
                if image_node is None:
                    continue
                if image_node.image.width == 1 and image_node.image.height == 1:
                    # TODO: Solve this is a less kludgy manner. The call to make the image can fail the first time
                    #  around because the renderer is what sets the size of the text. If the size hasn't already
                    #  been set, the initial bounds are wrong.
                    image_node = self._make_image_for_op(op)
                op.children.clear()
                op.add(image_node, type="elem image")

    def actualize_job_command(self):
        """
        Actualize the image at validate stage on operations.
        @return:
        """
        for op in self.plan:
            if not hasattr(op, "type"):
                continue
            if op.type == "op raster":
                dpi = float(op.settings['dpi'])
                oneinch_x = self.context.device.physical_to_device_length("1in", 0)[0]
                oneinch_y = self.context.device.physical_to_device_length(0, "1in")[1]
                step_x = float(oneinch_x / dpi)
                step_y = float(oneinch_y / dpi)
                op.settings['raster_step_x'] = step_x
                op.settings['raster_step_y'] = step_y
                for node in op.children:
                    node.step_x = step_x
                    node.step_y = step_y
                    m = node.matrix
                    # Transformation must be uniform to permit native rastering.
                    if m.a != step_x or m.b != 0.0 or m.c != 0.0 or m.d != step_y:
                        node.image, node.matrix = actualize(
                            node.image, node.matrix, step_x=step_x, step_y=step_y
                        )
                        node.cache = None
            if op.type == "op image":
                for node in op.children:
                    dpi = node.dpi
                    oneinch_x = self.context.device.physical_to_device_length("1in", 0)[0]
                    oneinch_y = self.context.device.physical_to_device_length(0, "1in")[1]
                    step_x = float(oneinch_x / dpi)
                    step_y = float(oneinch_y / dpi)
                    node.step_x = step_x
                    node.step_y = step_y
                    m1 = node.matrix
                    # Transformation must be uniform to permit native rastering.
                    if m1.a != step_x or m1.b != 0.0 or m1.c != 0.0 or m1.d != step_y:
                        node.image, node.matrix = actualize(
                            node.image, node.matrix, step_x=step_x, step_y=step_y
                        )
                        node.cache = None

    def scale_to_device_native(self):
        """
        Scale to device native at validate stage on operations.
        @return:
        """
        matrix = Matrix(self.context.device.scene_to_device_matrix())

        # TODO: Correct rotary.
        # rotary = self.context.rotary
        # if rotary.rotary_enabled:
        #     axis = rotary.axis

        for op in self.plan:
            if not hasattr(op, "type"):
                continue
            if op.type.startswith("op"):
                if hasattr(op, "scale_native"):
                    op.scale_native(matrix)
                for node in op.children:
                    e = node.object
                    try:
                        ne = e * matrix
                        node.replace_object(ne)
                    except AttributeError:
                        pass
        self.conditional_jobadd_actualize_image()

    def clear(self):
        self.plan.clear()
        self.commands.clear()

    # ==========
    # CONDITIONAL JOB ADDS
    # ==========

    def conditional_jobadd_strip_text(self):
        """
        Add strip_text command if conditions are met.
        @return:
        """
        for op in self.plan:
            if not hasattr(op, "type"):
                continue
            if op.type in ("op cut", "op engrave", "op hatch"):
                for e in op.children:
                    if not isinstance(e.object, SVGText):
                        continue  # make raster not needed since it's a single real raster.
                    self.commands.append(self.strip_text)
                    return True
        return False

    def conditional_jobadd_make_raster(self):
        """
        Add make_make raster command if conditions are met.
        @return:
        """
        for op in self.plan:
            if not hasattr(op, "type"):
                continue
            if op.type == "op raster":
                if len(op.children) == 0:
                    continue
                if len(op.children) == 1 and isinstance(op.children[0], SVGImage):
                    continue  # make raster not needed since it's a single real raster.
                make_raster = self.context.lookup("render-op/make_raster")

                if make_raster is None:
                    self.commands.append(self.strip_rasters)
                else:
                    self.commands.append(self.make_image)
                return True
        return False

    def conditional_jobadd_actualize_image(self):
        """
        Conditional actualize image if conditions are met.
        @return:
        """
        for op in self.plan:
            if not hasattr(op, "type"):
                continue
            # if op.type == "op raster":
            #     dpi = float(op.settings['dpi'])
            #     oneinch_x = self.context.device.physical_to_device_length("1in", 0)[0]
            #     oneinch_y = self.context.device.physical_to_device_length(0, "1in")[1]
            #     step_x = float(oneinch_x / dpi)
            #     step_y = float(oneinch_y / dpi)
            #     op.settings['raster_step_x'] = step_x
            #     op.settings['raster_step_y'] = step_y
            #     for node in op.children:
            #         m = node.object.transform
            #         # Transformation must be uniform to permit native rastering.
            #         if m.a != step_x or m.b != 0.0 or m.c != 0.0 or m.d != step_y:
            #             self.commands.append(self.actualize_job_command)
            #             return
            if op.type == "op image":
                for node in op.children:
                    dpi = node.dpi
                    oneinch_x = self.context.device.physical_to_device_length("1in", 0)[0]
                    oneinch_y = self.context.device.physical_to_device_length(0, "1in")[1]
                    step_x = float(oneinch_x / dpi)
                    step_y = float(oneinch_y / dpi)
                    node.step_x = step_x
                    node.step_y = step_y
                    m1 = node.matrix
                    # Transformation must be uniform to permit native rastering.
                    if m1.a != step_x or m1.b != 0.0 or m1.c != 0.0 or m1.d != step_y:
                        self.commands.append(self.actualize_job_command)
                        return

    def conditional_jobadd_scale(self):
        """
        Add scale to device native if conditions are met.
        @return:
        """
        self.commands.append(self.scale_to_device_native)


def is_inside(inner, outer):
    """
    Test that path1 is inside path2.
    @param inner: inner path
    @param outer: outer path
    @return: whether path1 is wholly inside path2.
    """
    inner_path = inner
    outer_path = outer
    if hasattr(inner, "path") and inner.path is not None:
        inner_path = inner.path
    if hasattr(outer, "path") and outer.path is not None:
        outer_path = outer.path
    if not hasattr(inner, "bounding_box"):
        inner.bounding_box = Group.union_bbox([inner_path])
    if not hasattr(outer, "bounding_box"):
        outer.bounding_box = Group.union_bbox([outer_path])
    if outer.bounding_box is None:
        return False
    if inner.bounding_box is None:
        return False
    # Raster is inner if the bboxes overlap anywhere
    if isinstance(inner, RasterCut):
        return (
            inner.bounding_box[0] <= outer.bounding_box[2]
            and inner.bounding_box[1] <= outer.bounding_box[3]
            and inner.bounding_box[2] >= outer.bounding_box[0]
            and inner.bounding_box[3] >= outer.bounding_box[1]
        )
    if outer.bounding_box[0] > inner.bounding_box[0]:
        # outer minx > inner minx (is not contained)
        return False
    if outer.bounding_box[1] > inner.bounding_box[1]:
        # outer miny > inner miny (is not contained)
        return False
    if outer.bounding_box[2] < inner.bounding_box[2]:
        # outer maxx < inner maxx (is not contained)
        return False
    if outer.bounding_box[3] < inner.bounding_box[3]:
        # outer maxy < inner maxy (is not contained)
        return False
    if outer.bounding_box == inner.bounding_box:
        if outer == inner:  # This is the same object.
            return False

    # Inner bbox is entirely inside outer bbox,
    # however that does not mean that inner is actually inside outer
    # i.e. inner could be small and between outer and the bbox corner,
    # or small and  contained in a concave indentation.
    #
    # VectorMontonizer can determine whether a point is inside a polygon.
    # The code below uses a brute force approach by considering a fixed number of points,
    # however we should consider a future enhancement whereby we create
    # a polygon more intelligently based on size and curvature
    # i.e. larger bboxes need more points and
    # tighter curves need more points (i.e. compare vector directions)
    if not hasattr(outer, "vm"):
        outer_path = Polygon(
            [outer_path.point(i / 1000.0, error=1e4) for i in range(1001)]
        )
        vm = VectorMontonizer()
        vm.add_cluster(outer_path)
        outer.vm = vm
    for i in range(101):
        p = inner_path.point(i / 100.0, error=1e4)
        if not outer.vm.is_point_inside(p.x, p.y):
            return False
    return True


def reify_matrix(self):
    """Apply the matrix to the path and reset matrix."""
    self.element = abs(self.element)
    self.scene_bounds = None


def bounding_box(elements):
    if isinstance(elements, SVGElement):
        elements = [elements]
    elif isinstance(elements, list):
        try:
            elements = [e.object for e in elements if isinstance(e.object, SVGElement)]
        except AttributeError:
            pass
    boundary_points = []
    for e in elements:
        box = e.bbox(False)
        if box is None:
            continue
        top_left = e.transform.point_in_matrix_space([box[0], box[1]])
        top_right = e.transform.point_in_matrix_space([box[2], box[1]])
        bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
        bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
        boundary_points.append(top_left)
        boundary_points.append(top_right)
        boundary_points.append(bottom_left)
        boundary_points.append(bottom_right)
    if len(boundary_points) == 0:
        return None
    xmin = min([e[0] for e in boundary_points])
    ymin = min([e[1] for e in boundary_points])
    xmax = max([e[0] for e in boundary_points])
    ymax = max([e[1] for e in boundary_points])
    return xmin, ymin, xmax, ymax


def correct_empty(context: CutGroup):
    """
    Iterates through backwards deleting any entries that empty.
    """
    for index in range(len(context) - 1, -1, -1):
        c = context[index]
        if not isinstance(c, CutGroup):
            continue
        correct_empty(c)
        if len(c) == 0:
            del context[index]


def inner_first_ident(context: CutGroup, channel=None):
    """
    Identifies closed CutGroups and then identifies any other CutGroups which
    are entirely inside.

    The CutGroup candidate generator uses this information to not offer the outer CutGroup
    as a candidate for a burn unless all contained CutGroups are cut.

    The Cutcode is resequenced in either short_travel_cutcode or inner_selection_cutcode
    based on this information, as used in the
    """
    if channel:
        start_time = time()
        start_times = times()
        channel("Executing Inner-First Identification")

    groups = [cut for cut in context if isinstance(cut, (CutGroup, RasterCut))]
    closed_groups = [g for g in groups if isinstance(g, CutGroup) and g.closed]
    context.contains = closed_groups

    constrained = False
    for outer in closed_groups:
        for inner in groups:
            if outer is inner:
                continue
            # if outer is inside inner, then inner cannot be inside outer
            if inner.contains and outer in inner.contains:
                continue
            if is_inside(inner, outer):
                constrained = True
                if outer.contains is None:
                    outer.contains = list()
                outer.contains.append(inner)

                if inner.inside is None:
                    inner.inside = list()
                inner.inside.append(outer)

    context.constrained = constrained

    # for g in groups:
    # if g.contains is not None:
    # for inner in g.contains:
    # assert inner in groups
    # assert inner is not g
    # assert g in inner.inside
    # if g.inside is not None:
    # for outer in g.inside:
    # assert outer in groups
    # assert outer is not g
    # assert g in outer.contains

    if channel:
        end_times = times()
        channel(
            (
                "Inner paths identified in {elapsed:.3f} elapsed seconds "
                + "using {cpu:.3f} seconds CPU"
            ).format(
                elapsed=time() - start_time,
                cpu=end_times[0] - start_times[0],
            )
        )
    return context


def short_travel_cutcode(
    context: CutCode,
    channel=None,
    complete_path: Optional[bool] = False,
    grouped_inner: Optional[bool] = False,
):
    """
    Selects cutcode from candidate cutcode (burns_done < passes in this CutCode),
    optimizing with greedy/brute for shortest distances optimizations.

    For paths starting at exactly the same point forward paths are preferred over reverse paths

    We start at either 0,0 or the value given in `context.start`

    This is time-intense hyper-optimized code, so it contains several seemingly redundant
    checks.
    """
    if channel:
        start_length = context.length_travel(True)
        start_time = time()
        start_times = times()
        channel("Executing Greedy Short-Travel optimization")
        channel("Length at start: {length:.0f} steps".format(length=start_length))

    curr = context.start
    if curr is None:
        curr = 0
    else:
        curr = complex(curr[0], curr[1])

    for c in context.flat():
        c.burns_done = 0

    ordered = CutCode()
    while True:
        closest = None
        backwards = False
        distance = float("inf")

        try:
            last_segment = ordered[-1]
        except IndexError:
            pass
        else:
            if last_segment.normal:
                # Attempt to initialize value to next segment in subpath
                cut = last_segment.next
                if cut and cut.burns_done < cut.passes:
                    closest = cut
                    backwards = False
                    start = closest.start
                    distance = abs(complex(start[0], start[1]) - curr)
            else:
                # Attempt to initialize value to previous segment in subpath
                cut = last_segment.previous
                if cut and cut.burns_done < cut.passes:
                    closest = cut
                    backwards = True
                    end = closest.end
                    distance = abs(complex(end[0], end[1]) - curr)
            # Gap or continuing on path not permitted, try reversing
            if (
                distance > 50
                and last_segment.burns_done < last_segment.passes
                and last_segment.reversible()
                and last_segment.next is not None
            ):
                # last_segment is a copy, so we need to get original
                closest = last_segment.next.previous
                backwards = last_segment.normal
                distance = 0  # By definition since we are reversing and reburning

        # Stay on path in same direction if gap <= 1/20" i.e. path not quite closed
        # Travel only if path is completely burned or gap > 1/20"
        if distance > 50:
            for cut in context.candidate(
                complete_path=complete_path, grouped_inner=grouped_inner
            ):
                s = cut.start
                if (
                    abs(s[0] - curr.real) <= distance
                    and abs(s[1] - curr.imag) <= distance
                    and (not complete_path or cut.closed or cut.first)
                ):
                    d = abs(complex(s[0], s[1]) - curr)
                    if d < distance:
                        closest = cut
                        backwards = False
                        if d <= 0.1:  # Distance in px is zero, we cannot improve.
                            break
                        distance = d

                if not cut.reversible():
                    continue
                e = cut.end
                if (
                    abs(e[0] - curr.real) <= distance
                    and abs(e[1] - curr.imag) <= distance
                    and (not complete_path or cut.closed or cut.last)
                ):
                    d = abs(complex(e[0], e[1]) - curr)
                    if d < distance:
                        closest = cut
                        backwards = True
                        if d <= 0.1:  # Distance in px is zero, we cannot improve.
                            break
                        distance = d

        if closest is None:
            break

        # Change direction if other direction is coincident and has more burns remaining
        if backwards:
            if (
                closest.next
                and closest.next.burns_done <= closest.burns_done
                and closest.next.start == closest.end
            ):
                closest = closest.next
                backwards = False
        elif closest.reversible():
            if (
                closest.previous
                and closest.previous is not closest
                and closest.previous.burns_done < closest.burns_done
                and closest.previous.end == closest.start
            ):
                closest = closest.previous
                backwards = True

        closest.burns_done += 1
        c = copy(closest)
        if backwards:
            c.reverse()
        end = c.end
        curr = complex(end[0], end[1])
        ordered.append(c)

    ordered._start_x, ordered._start_y = context.start
    if channel:
        end_times = times()
        end_length = ordered.length_travel(True)
        channel(
            (
                "Length at end: {length:.0f} steps ({delta:+.0%}), "
                + "optimized in {elapsed:.3f} elapsed seconds "
                + "using {cpu:.3f} seconds CPU"
            ).format(
                length=end_length,
                delta=(end_length - start_length) / start_length,
                elapsed=time() - start_time,
                cpu=end_times[0] - start_times[0],
            )
        )
    return ordered


def short_travel_cutcode_2opt(context: CutCode, passes: int = 50, channel=None):
    """
    This implements 2-opt algorithm using numpy.

    Skipping of the candidate code it does not perform inner first optimizations.
    Due to the numpy requirement, doesn't work without numpy.
    --
    Uses code I wrote for vpype:
    https://github.com/abey79/vpype/commit/7b1fad6bd0fcfc267473fdb8ba2166821c80d9cd

    @param context:cutcode: cutcode to be optimized
    @param passes: max passes to perform 2-opt
    @param channel: Channel to send data about the optimization process.
    @return:
    """
    try:
        import numpy as np
    except ImportError:
        return context

    if channel:
        start_length = context.length_travel(True)
        start_time = time()
        start_times = times()
        channel("Executing 2-Opt Short-Travel optimization")
        channel("Length at start: {length:.0f} steps".format(length=start_length))

    ordered = CutCode(context.flat())
    length = len(ordered)
    if length <= 1:
        if channel:
            channel("2-Opt: Not enough elements to optimize.")
        return ordered

    curr = context.start
    if curr is None:
        curr = 0
    else:
        curr = complex(curr)

    current_pass = 1
    min_value = -1e-10  # Do not swap on rounding error.

    endpoints = np.zeros((length, 4), dtype="complex")
    # start, index, reverse-index, end
    for i in range(length):
        endpoints[i] = complex(ordered[i].start), i, ~i, complex(ordered[i].end)
    indexes0 = np.arange(0, length - 1)
    indexes1 = indexes0 + 1

    def log_progress(pos):
        starts = endpoints[indexes0, -1]
        ends = endpoints[indexes1, 0]
        dists = np.abs(starts - ends)
        dist_sum = dists.sum() + abs(curr - endpoints[0][0])
        channel(
            "optimize: laser-off distance is %f. %.02f%% done with pass %d/%d"
            % (dist_sum, 100 * pos / length, current_pass, passes)
        )

    improved = True
    while improved:
        improved = False

        first = endpoints[0][0]
        cut_ends = endpoints[indexes0, -1]
        cut_starts = endpoints[indexes1, 0]

        # delta = np.abs(curr - first) + np.abs(first - cut_starts) - np.abs(cut_ends - cut_starts)
        delta = (
            np.abs(curr - cut_ends)
            + np.abs(first - cut_starts)
            - np.abs(cut_ends - cut_starts)
            - np.abs(curr - first)
        )
        index = int(np.argmin(delta))
        if delta[index] < min_value:
            endpoints[: index + 1] = np.flip(
                endpoints[: index + 1], (0, 1)
            )  # top to bottom, and right to left flips.
            improved = True
            if channel:
                log_progress(1)
        for mid in range(1, length - 1):
            idxs = np.arange(mid, length - 1)

            mid_source = endpoints[mid - 1, -1]
            mid_dest = endpoints[mid, 0]
            cut_ends = endpoints[idxs, -1]
            cut_starts = endpoints[idxs + 1, 0]
            delta = (
                np.abs(mid_source - cut_ends)
                + np.abs(mid_dest - cut_starts)
                - np.abs(cut_ends - cut_starts)
                - np.abs(mid_source - mid_dest)
            )
            index = int(np.argmin(delta))
            if delta[index] < min_value:
                endpoints[mid : mid + index + 1] = np.flip(
                    endpoints[mid : mid + index + 1], (0, 1)
                )
                improved = True
                if channel:
                    log_progress(mid)

        last = endpoints[-1, -1]
        cut_ends = endpoints[indexes0, -1]
        cut_starts = endpoints[indexes1, 0]

        delta = np.abs(cut_ends - last) - np.abs(cut_ends - cut_starts)
        index = int(np.argmin(delta))
        if delta[index] < min_value:
            endpoints[index + 1 :] = np.flip(
                endpoints[index + 1 :], (0, 1)
            )  # top to bottom, and right to left flips.
            improved = True
            if channel:
                log_progress(length)
        if current_pass >= passes:
            break
        current_pass += 1

    # Two-opt complete.
    order = endpoints[:, 1].real.astype(int)
    ordered.reordered(order)
    if channel:
        end_times = times()
        end_length = ordered.length_travel(True)
        channel(
            (
                "Length at end: {length:.0f} steps ({delta:+.0%}), "
                + "optimized in {elapsed:.3f} elapsed seconds "
                + "using {cpu:.3f} seconds CPU"
            ).format(
                length=end_length,
                delta=(end_length - start_length) / start_length,
                elapsed=time() - start_time,
                cpu=end_times[0] - start_times[0],
            )
        )
    return ordered


def inner_selection_cutcode(
    context: CutCode, channel=None, grouped_inner: Optional[bool] = False
):
    """
    Selects cutcode from candidate cutcode permitted but does nothing to optimize beyond
    finding a valid solution.

    This routine runs if opt_inner first is selected and opt_greedy is not selected.
    """
    if channel:
        start_length = context.length_travel(True)
        start_time = time()
        start_times = times()
        channel("Executing Inner Selection-Only optimization")
        channel("Length at start: {length:.0f} steps".format(length=start_length))

    for c in context.flat():
        c.burns_done = 0

    ordered = CutCode()
    iterations = 0
    while True:
        c = list(context.candidate(grouped_inner=grouped_inner))
        if len(c) == 0:
            break
        for o in c:
            o.burns_done += 1
        ordered.extend(copy(c))
        iterations += 1

    if channel:
        end_times = times()
        end_length = ordered.length_travel(True)
        channel(
            (
                "Length at end: {length:.0f} steps ({delta:+.0%}), "
                + "optimized in {elapsed:.3f} elapsed seconds "
                + "using {cpu:.3f} seconds CPU "
                + "in {iterations} iterations"
            ).format(
                length=end_length,
                delta=(end_length - start_length) / start_length,
                elapsed=time() - start_time,
                cpu=end_times[0] - start_times[0],
                iterations=iterations,
            )
        )
    return ordered
