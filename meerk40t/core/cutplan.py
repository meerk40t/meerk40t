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
from math import ceil
from os import times
from time import time
from typing import Any, List

from ..device.lhystudios.laserspeed import LaserSpeed
from ..device.lhystudios.lhystudiosdevice import LhystudiosDriver
from ..image.actualize import actualize
from ..svgelements import Group, Path, Polygon, SVGImage, SVGText
from ..tools.pathtools import VectorMontonizer
from ..tools.rastergrouping import group_elements_overlap, group_overlapped_rasters
from .cutcode import CutCode, CutGroup, CutObject, RasterCut
from .elements import LaserOperation

try:
    from PIL import Image

    PILLOW_LOADED = True
except ImportError:
    PILLOW_LOADED = False


class CutPlan:
    """
    Process LaserOperations into CutCode objects which are spooled
    """

    def __init__(self, name, context):
        self.name = name
        self.context = context
        self.plan = []
        self.original = []
        self.commands = []
        self.channel = context.channel("optimize", timestamp=True)
        self.context.setting(bool, "opt_rasters_split", True)

    def __str__(self):
        parts = []
        parts.append(self.name)
        if self.plan:
            parts.append("#%d" % len(self.plan))
            for p in self.plan:
                try:
                    parts.append(p.operation)
                except AttributeError:
                    try:
                        parts.append(p.__name__)
                    except AttributeError:
                        parts.append(p.__class__.__name__)
        else:
            parts.append("-- Empty --")
        return " ".join(parts)

    def grouped_inner(self):
        return self.context.opt_inner_first and self.context.opt_inners_grouped

    def execute(self):
        # Using copy of commands, so commands can add ops.
        cmds = self.commands[:]
        self.commands.clear()
        for cmd in cmds:
            cmd()

    def preprocess(self):
        """Add before, after and conditional auto-operations"""
        self.preprocess_before()
        self.preprocess_after()
        self.preprocess_conditional()

    def preprocess_before(self):
        context = self.context
        _ = context._
        rotary_context = context.get_context("rotary/1")

        # ==========
        # Before
        # ==========
        if context.prephysicalhome:
            if not rotary_context.rotary:
                self.plan.insert(0, context.registered["plan/physicalhome"])
            else:
                self.plan.insert(0, _("Physical Home Before: Disabled (Rotary On)"))
        if context.prehome:
            if not rotary_context.rotary:
                self.plan.insert(0, context.registered["plan/home"])
            else:
                self.plan.insert(0, _("Home Before: Disabled (Rotary On)"))

    def preprocess_after(self):
        context = self.context
        _ = context._
        rotary_context = context.get_context("rotary/1")

        # ==========
        # After
        # ==========
        if context.autohome:
            if not rotary_context.rotary:
                self.plan.append(context.registered["plan/home"])
            else:
                self.plan.append(_("Home After: Disabled (Rotary On)"))
        if context.autophysicalhome:
            if not rotary_context.rotary:
                self.plan.append(context.registered["plan/physicalhome"])
            else:
                self.plan.append(_("Physical Home After: Disabled (Rotary On)"))
        if context.autoorigin:
            self.plan.append(context.registered["plan/origin"])
        if context.postunlock:
            self.plan.append(context.registered["plan/unlock"])
        if context.autobeep:
            self.plan.append(context.registered["plan/beep"])
        if context.autointerrupt:
            self.plan.append(context.registered["plan/interrupt"])

    def preprocess_conditional(self):
        context = self.context
        rotary_context = context.get_context("rotary/1")

        # ==========
        # Conditional Ops
        # ==========
        self.conditional_jobadd_strip_text()
        if rotary_context.rotary:
            self.conditional_jobadd_scale_rotary()
        self.conditional_jobadd_actualize_image()
        self.conditional_jobadd_make_raster()

    def blob(self):
        """
        blob converts User operations to CutCode objects.

        In order to have CutCode objects in the correct sequence for merging we need to:
        a. Break operations into grouped sequences of LaserOperations and special operations.
           We can only merge within groups of Laser operations.
        b. The sequence of CutObjects needs to reflect merge settings
           Normal sequence is to iterate operations and then passes for each operation.
           With Merge ops and not Merge passes, we need to iterate on passes first and then ops within.
        """

        if not self.plan:
            return

        grouped_plan = self.blob_group_plans()
        blob_plan = self.blob_planner(grouped_plan)
        self.blob_merges(blob_plan)

    def blob_group_plans(self) -> List:
        """Group consecutive LaserOperations split by special operations"""
        grouped_plan = []
        group = [self.plan[0]]
        for c in self.plan[1:]:
            if (
                isinstance(group[-1], LaserOperation) or isinstance(c, LaserOperation)
            ) and type(group[-1]) != type(c):
                grouped_plan.append(group)
                group = []
            group.append(c)
        grouped_plan.append(group)
        return grouped_plan

    def blob_planner(self, grouped_plan: List) -> List:
        """Create CutCode objects from LaserOperations"""
        context = self.context

        # If Merge operations and not merge passes we need to iterate passes first and operations second
        passes_first = context.opt_merge_ops and not context.opt_merge_passes
        blob_plan = []
        for plan in grouped_plan:
            burning = True
            pass_idx = -1
            while burning:
                burning = False
                pass_idx += 1
                for op in plan:
                    if not isinstance(op, LaserOperation):
                        blob_plan.append(op)
                        continue
                    if op.operation == "Dots":
                        if pass_idx == 0:
                            blob_plan.append(op)
                        continue
                    copies = op.settings.implicit_passes
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
                            op.operation == "Cut" and context.opt_inner_first
                        )
                        cutcode.pass_index = pass_idx if passes_first else p
                        cutcode.original_op = op.operation
                        blob_plan.append(cutcode)

        return blob_plan

    def blob_merges(self, blob_plan: List) -> List:
        """Create the final cut plan by merging blobs where appropriate"""
        context = self.context

        self.plan.clear()

        for blob in blob_plan:
            try:
                blob.settings.jog_distance = context.opt_jog_minimum
                blob.settings.jog_enable = context.opt_rapid_between
            except AttributeError:
                pass
            # We can only merge and check for other criteria if we have the right objects
            merge = (
                self.plan
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
                and self.plan[-1].original_op == "Cut"
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
        context = self.context
        has_cutcode = False
        for op in self.plan:
            try:
                if op.operation == "CutCode":
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
        channel = self.context.channel("optimize", timestamp=True)
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                self.plan[i] = self.short_travel_cutcode_2opt(c)

    def optimize_cuts(self):
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                if c.constrained:
                    c = self.plan[i] = self.inner_first_ident(c)
                if self.grouped_inner() and PILLOW_LOADED:
                    c = self.plan[i] = self.inner_first_image_optimize(c)
                self.plan[i] = self.inner_selection_cutcode(c)

    def optimize_travel(self):
        last = None
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                if c.constrained:
                    c = self.plan[i] = self.inner_first_ident(c)
                if self.grouped_inner() and PILLOW_LOADED:
                    c = self.plan[i] = self.inner_first_image_optimize(c)
                if last is not None:
                    self.plan[i].start = last
                self.plan[i] = self.short_travel_cutcode(c)
                last = self.plan[i].end()

    def strip_text(self):
        for k in range(len(self.plan) - 1, -1, -1):
            op = self.plan[k]
            try:
                if op.operation in ("Cut", "Engrave"):
                    for i, e in enumerate(list(op.children)):
                        if isinstance(e.object, SVGText):
                            e.remove_node()
                    if len(op.children) == 0:
                        del self.plan[k]
            except AttributeError:
                pass

    def strip_rasters(self):
        stripped = False
        for i, op in enumerate(list(self.plan)):
            if isinstance(op, LaserOperation) and op.operation == "Raster":
                for j, node in enumerate(list(op.children)):
                    if hasattr(node, "object") and not isinstance(
                        node.object, SVGImage
                    ):
                        del op.children[j]
                if not op.children:
                    del self.plan[i]

    def make_image_from_raster(self, nodes, step=1):
        make_raster = self.context.registered.get("render-op/make_raster")
        objs = [n.object for n in nodes]
        bounds = Group.union_bbox(objs, with_stroke=True)
        if bounds is None:
            return None
        xmin, ymin, xmax, ymax = bounds
        image = make_raster(nodes, bounds, step=step)
        image_element = SVGImage(image=image)
        image_element.transform.post_scale(step, step)
        image_element.transform.post_translate(xmin, ymin)
        image_element.values["raster_step"] = step
        return image_element

    def get_raster_margins(self, op_settings, smallest=True):
        """
        Determine group raster margins based on:
            1. Whether cut inner first and group inners are both set
            2. Overscan - as a minimum small margin to group rasters that are close
            3. Device type - only have accel values for lhy devices
            4. Acceleration number (manual or automatic)
            5. Actual raster speed (adjusted if necessary from Op speed)
        If choice between merged or separated is evenly balanced, we prefer merged
        by adding a constant value of 50 (mils) to the margins.
        """

        # Determine raster direction(s)
        # T2B=0, B2T=1, R2L=2, L2R=3, X=4
        direction = op_settings.raster_direction
        h_sweep = direction in (0, 1, 4)
        v_sweep = direction in (2, 3, 4)

        # set minimum margins for inners_grouped
        dx = op_settings.overscan if h_sweep else 0
        dy = op_settings.overscan if v_sweep else 0

        # if cut inner first and group inner, minimise size so as to group correctly
        context = self.context
        root = context.root
        if smallest and context.opt_inner_first and context.opt_inners_grouped:
            return dx, dy

        # set minimum margins otherwise
        dx = 500 if h_sweep else 50
        dy = 500 if v_sweep else 50

        # Get device and check for lhystudios
        try:
            spooler, device, controller = root.registered["device/%s" % root.active]
        except (KeyError, ValueError):
            return dx, dy
        if not isinstance(device, LhystudiosDriver):
            return dx, dy

        # Determine actual speed and acceleration using LaserSpeed
        speed = LaserSpeed.get_actual_speed(
            op_settings.speed, device.context.fix_speeds
        )
        if op_settings.acceleration_custom:
            h_accel = v_accel = op_settings.acceleration
        else:
            h_accel = LaserSpeed.get_acceleration_for_speed(
                speed,
                raster=True,
                raster_horizontal=True,
            )
            v_accel = LaserSpeed.get_acceleration_for_speed(
                speed,
                raster=True,
                raster_horizontal=False,
            )

        # For cross-raster (type 4) it might make sense to group elements differently
        # and create different raster images, however this may be confusing,
        # could potentially lead to quality issues, and AFAIK cross-raster is rarely used.

        # Calculate margins
        if h_sweep:
            dx = max(dx, CutPlan.sweep_distance(speed, h_accel)) + 50
        if v_sweep:
            dy = max(dy, CutPlan.sweep_distance(speed, v_accel)) + 50

        return dx, dy

    @staticmethod
    def sweep_distance(speed, accel):
        """Calculate 1/2 sweep distance equivalent to acceleration time"""
        margin_um = speed * (LaserSpeed.get_acceleration_time(speed, accel) + 1.5)
        margin_mils = int(margin_um / 25.4)
        return margin_mils

    def make_image(self):
        for op in self.plan:
            if isinstance(op, LaserOperation) and op.operation == "Raster":
                self.make_image_raster_op(op)

    def make_image_raster_op(self, op: LaserOperation):
        nodes = list(op.flat(types=("elem", "opnode")))
        reverse = self.context.classify_reverse
        if reverse:
            nodes = list(reversed(nodes))

        raster_opt = self.context.opt_rasters_split
        if raster_opt:
            dx, dy = self.get_raster_margins(op.settings)

            def adjust_bbox(bbox):
                if bbox is None:
                    return None
                x1, y1, x2, y2 = bbox
                return x1 - dx, y1 - dy, x2 + dx, y2 + dy

            groups = group_overlapped_rasters(
                [
                    (node, adjust_bbox(node.object.bbox(with_stroke=True)))
                    for node in nodes
                ]
            )
        else:
            groups = [[(node, None) for node in nodes]]

        step = max(1, op.settings.raster_step)
        images = []
        for g in groups:
            g = [x[0] for x in g]
            if len(g) == 1 and isinstance(g[0].object, SVGImage):
                images.append(g[0].object)
                continue
            # Ensure rasters are in original sequence
            g.sort(key=nodes.index)
            image = self.make_image_from_raster(g, step=step)
            if image is None:
                continue
            if image.image_width == 1 and image.image_height == 1:
                """
                TODO: Solve this is a less kludgy manner. The call to make the image can fail the first
                    time around because the renderer is what sets the size of the text. If the size hasn't
                    already been set, the initial bounds are wrong.
                """
                print(
                    "Retrying make_image_from_raster ({w},{h})".format(
                        w=image.image_width, h=image.image_height
                    )
                )
                image = self.make_image_from_raster(g, step=step)
            images.append(image)

        op.children.clear()
        for image in images:
            op.add(image, type="opnode")

    def actualize(self):
        for op in self.plan:
            try:
                if op.operation == "Raster":
                    for elem in op.children:
                        elem = elem.object
                        if needs_actualization(elem, op.settings.raster_step):
                            make_actual(elem, op.settings.raster_step)
                if op.operation == "Image":
                    for elem in op.children:
                        elem = elem.object
                        if needs_actualization(elem, None):
                            make_actual(elem, None)
            except AttributeError:
                pass

    def scale_for_rotary(self):
        r = self.context.get_context("rotary/1")
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
        if input_driver is None:
            return
        scale_str = "scale(%f,%f,%f,%f)" % (
            r.scale_x,
            r.scale_y,
            input_driver.current_x,
            input_driver.current_y,
        )
        for o in self.plan:
            if isinstance(o, LaserOperation):
                for node in o.children:
                    e = node.object
                    try:
                        ne = e * scale_str
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
        for op in self.plan:
            try:
                if op.operation in ("Cut", "Engrave"):
                    for e in op.children:
                        if not isinstance(e.object, SVGText):
                            continue  # make raster not needed since its a single real raster.
                        self.commands.append(self.strip_text)
                        return True
            except AttributeError:
                pass
        return False

    def conditional_jobadd_make_raster(self):
        for op in self.plan:
            try:
                if op.operation == "Raster":
                    if len(op.children) == 0:
                        continue
                    for c in op.children:
                        if not isinstance(c, SVGImage):
                            break
                    else:
                        # make raster not needed since all children are already images
                        continue
                    make_raster = self.context.registered.get("render-op/make_raster")

                    if make_raster is None:
                        self.commands.append(self.strip_rasters)
                    else:
                        self.commands.append(self.make_image)
                    return True
            except AttributeError:
                pass
        return False

    def conditional_jobadd_actualize_image(self):
        for op in self.plan:
            try:
                if op.operation == "Raster":
                    for elem in op.children:
                        elem = elem.object
                        if needs_actualization(elem, op.settings.raster_step):
                            self.commands.append(self.actualize)
                            return
                if op.operation == "Image":
                    for elem in op.children:
                        elem = elem.object
                        if needs_actualization(elem, None):
                            self.commands.append(self.actualize)
                            return
            except AttributeError:
                pass

    def conditional_jobadd_scale_rotary(self):
        rotary_context = self.context.get_context("rotary/1")
        if rotary_context.scale_x != 1.0 or rotary_context.scale_y != 1.0:
            self.commands.append(self.scale_for_rotary)

    # @staticmethod
    # def bounding_box(elements):
    # if isinstance(elements, SVGElement):
    # elements = [elements]
    # elif isinstance(elements, list):
    # try:
    # elements = [e.object for e in elements if isinstance(e.object, SVGElement)]
    # except AttributeError:
    # pass
    # boundary_points = []
    # for e in elements:
    # box = e.bbox(False)
    # if box is None:
    # continue
    # top_left = e.transform.point_in_matrix_space([box[0], box[1]])
    # top_right = e.transform.point_in_matrix_space([box[2], box[1]])
    # bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
    # bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
    # boundary_points.append(top_left)
    # boundary_points.append(top_right)
    # boundary_points.append(bottom_left)
    # boundary_points.append(bottom_right)
    # if len(boundary_points) == 0:
    # return None
    # xmin = min([e[0] for e in boundary_points])
    # ymin = min([e[1] for e in boundary_points])
    # xmax = max([e[0] for e in boundary_points])
    # ymax = max([e[1] for e in boundary_points])
    # return xmin, ymin, xmax, ymax

    def inner_first_ident(self, context: CutGroup):
        """
        Identifies closed CutGroups and then identifies any other CutGroups which
        are entirely inside.

        The CutGroup candidate generator uses this information to not offer the outer CutGroup
        as a candidate for a burn unless all contained CutGroups are cut.

        The Cutcode is resequenced in either short_travel_cutcode or inner_selection_cutcode
        based on this information.
        """
        if self.channel:
            start_time = time()
            start_times = times()
            self.channel("Executing Inner-First Identification")

        groups = [cut for cut in context if isinstance(cut, (CutGroup, RasterCut))]
        closed_groups = [
            g
            for g in groups
            if isinstance(g, CutGroup) and g.closed and g.original_op == "Cut"
        ]

        constrained = False
        for outer in closed_groups:
            for inner in groups:
                if outer is inner:
                    continue
                # if outer is inside inner, then inner cannot be inside outer
                if inner.contains and outer in inner.contains:
                    continue
                if is_inside(inner, outer):
                    # if inner.bounding_box and outer.bounding_box:
                    # print(
                    # outer.__class__.__name__,outer.bounding_box,
                    # "contains"
                    # inner.__class__.__name__,inner.bounding_box
                    # )
                    constrained = True
                    if outer.contains is None:
                        outer.contains = []
                    outer.contains.append(inner)

                    if inner.inside is None:
                        inner.inside = []
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

        if self.channel:
            end_times = times()
            self.channel(
                (
                    "Inner paths identified in {elapsed:.3f} elapsed seconds "
                    + "using {cpu:.3f} seconds CPU"
                ).format(
                    elapsed=time() - start_time,
                    cpu=end_times[0] - start_times[0],
                )
            )

        return context

    def inner_first_image_optimize(self, context: CutGroup, channel=None):
        """
        If we have opt_inner_first and opt_inner_grouped, we have split rasters into
        smallest overlapping groups in order to best associate images with outer cuts.

        Now we need to combine images back together where they are not in different outers
        and they are close enough together to raster faster as one image.

        To be mergeable they need to have margins that overlap, and the same op setting object.
        """
        if self.channel:
            start_time = time()
            start_times = times()
            self.channel("Executing Inner-First Image merges")

        groups = []
        for img in context:
            if not isinstance(img, RasterCut):
                continue
            dx, dy = self.get_raster_margins(img.settings, smallest=False)
            bbox = (
                img.tx - dx,
                img.ty - dy,
                img.tx + img.width + dx,
                img.ty + img.height + dy,
            )
            groups.append([(img, bbox)])

        start_images = len(groups)

        # Group where margins overlap
        # We are using old fashioned iterators because Python cannot cope with consolidating a list whilst iterating over it.
        for i in range(len(groups) - 2, -1, -1):
            g1 = groups[i]
            for j in range(len(groups) - 1, i, -1):
                g2 = groups[j]
                if g1[0][0].settings is not g2[0][0].settings:
                    continue
                if g1[0][0].passes != g2[0][0].passes:
                    continue
                if (g1[0][0].inside is None and g2[0][0].inside is not None) or (
                    g1[0][0].inside is not None and g2[0][0].inside is None
                ):
                    continue

                if g1[0][0].inside:
                    if len(g1[0][0].inside) != len(g2[0][0].inside):
                        continue
                    for g in g1[0][0].inside:
                        if g not in g2[0][0].inside:
                            continue

                if group_elements_overlap(g1, g2):
                    g1.extend(g2)
                    del groups[j]

        # Combine images
        for grp in groups:
            if len(grp) == 1:
                continue
            images = [g[0] for g in grp]
            self.inner_first_image_merge(context, images)

        if self.channel:
            end_images = len(groups)
            end_times = times()
            self.channel(
                (
                    "{frm} images combined into {to} images "
                    + "in {elapsed:.3f} elapsed seconds "
                    + "using {cpu:.3f} seconds CPU."
                ).format(
                    frm=start_images,
                    to=end_images,
                    elapsed=time() - start_time,
                    cpu=end_times[0] - start_times[0],
                )
            )

        return context

    def inner_first_image_merge(self, context: CutGroup, images: List) -> None:
        """Combine raster images with same outer cuts and operations"""
        images.sort(key=context.index)

        xmin = min([i.tx for i in images])
        ymin = min([i.ty for i in images])
        xmax = max([i.tx + i.width for i in images])
        ymax = max([i.ty + i.height for i in images])
        width = ceil(xmax - xmin)
        height = ceil(ymax - ymin)

        image = Image.new("L", (width, height), "white")
        for i in images:
            image.paste(
                i.image, (int((i.tx - xmin) / i.step), int((i.ty - ymin) / i.step))
            )

        cut = RasterCut(
            image,
            xmin,
            ymin,
            settings=images[0].settings,
            passes=images[0].passes,
        )
        cut.path = Path(
            Polygon(
                (xmin, ymin),
                (xmin, ymax),
                (xmax, ymax),
                (xmax, ymin),
            )
        )

        # Replace first image in context with new one
        # aligning
        cut.original_op = images[0].original_op
        cut.inside = images[0].inside
        if cut.inside:
            for o in cut.inside:
                if not o.contains:
                    o.contains = []
                o.contains.append(cut)
                if images[0] in o.contains:
                    o.contains.remove(images[0])

        context[context.index(images[0])] = cut
        del images[0]
        for i in images:
            # First delete reference in inside groups contains list
            if i.inside:
                for outer in i.inside:
                    if outer.contains and i in outer.contains:
                        outer.contains.remove(i)
            if i in context:
                context.remove(i)

    def short_travel_cutcode(self, context: CutCode):
        """
        Selects cutcode from candidate cutcode (burns_done < passes in this CutCode),
        optimizing with greedy/brute for shortest distances optimizations.

        For paths starting at exactly the same point forward paths are preferred over reverse paths

        We start at either 0,0 or the value given in context.start

        This is time-intense hyper-optimized code, so it contains several seemingly redundant
        checks.
        """
        if self.channel:
            start_length = context.length_travel(True)
            start_time = time()
            start_times = times()
            self.channel("Executing Greedy Short-Travel optimization")
            self.channel(
                "Length at start: {length:.0f} mils".format(length=start_length)
            )

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
                        distance = abs(complex(closest.start()) - curr)
                else:
                    # Attempt to initialize value to previous segment in subpath
                    cut = last_segment.previous
                    if cut and cut.burns_done < cut.passes:
                        closest = cut
                        backwards = True
                        distance = abs(complex(closest.end()) - curr)
                # Gap or continuing on path not permitted, try reversing
                if (
                    distance > 50
                    and last_segment.burns_done < last_segment.passes
                    and last_segment.reversible()
                    and last_segment.next is not None
                ):
                    # last_segment is a copy so we need to get original
                    closest = last_segment.next.previous
                    backwards = last_segment.normal
                    distance = 0  # By definition since we are reversing and reburning

            # Stay on path in same direction if gap <= 1/20" i.e. path not quite closed
            # Travel only if path is completely burned or gap > 1/20"
            if distance > 50:
                closest, backwards = self.short_travel_cutcode_candidate(
                    context, closest, backwards, curr, distance
                )

            if closest is None:
                break

            # Change direction if other direction is coincident and has more burns remaining
            if backwards:
                if (
                    closest.next
                    and closest.next.burns_done <= closest.burns_done
                    and closest.next.start() == closest.end()
                ):
                    closest = closest.next
                    backwards = False
            elif closest.reversible():
                if (
                    closest.previous
                    and closest.previous is not closest
                    and closest.previous.burns_done < closest.burns_done
                    and closest.previous.end() == closest.start()
                ):
                    closest = closest.previous
                    backwards = True

            closest.burns_done += 1
            c = copy(closest)
            if backwards:
                c.reverse()
            end = c.end()
            curr = complex(end)
            ordered.append(c)

        ordered.start = context.start

        if self.channel:
            end_times = times()
            end_length = ordered.length_travel(True)
            self.channel(
                (
                    "Length at end: {length:.0f} mils ({delta:+.0%}), "
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

    def short_travel_cutcode_candidate(
        self,
        context: CutCode,
        closest: Any,
        backwards: Any,
        curr: complex,
        distance: float,
    ) -> Any:
        complete_path = self.context.opt_complete_subpaths
        for cut in context.candidate(
            complete_path=complete_path, grouped_inner=self.grouped_inner()
        ):
            s = cut.start()
            if (
                abs(s.x - curr.real) <= distance
                and abs(s.y - curr.imag) <= distance
                and (not complete_path or cut.closed or cut.first)
            ):
                d = abs(complex(s) - curr)
                if d < distance:
                    closest = cut
                    backwards = False
                    if d <= 0.1:  # Distance in px is zero, we cannot improve.
                        break
                    distance = d

            if not cut.reversible():
                continue
            e = cut.end()
            if (
                abs(e.x - curr.real) <= distance
                and abs(e.y - curr.imag) <= distance
                and (not complete_path or cut.closed or cut.last)
            ):
                d = abs(complex(e) - curr)
                if d < distance:
                    closest = cut
                    backwards = True
                    if d <= 0.1:  # Distance in px is zero, we cannot improve.
                        break
                    distance = d

        return closest, backwards

    def short_travel_cutcode_2opt(self, context: CutCode, passes: int = 50):
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

        if self.channel:
            start_length = context.length_travel(True)
            start_time = time()
            start_times = times()
            self.channel("Executing 2-Opt Short-Travel optimization")
            self.channel(
                "Length at start: {length:.0f} mils".format(length=start_length)
            )

        ordered = CutCode(context.flat())
        length = len(ordered)
        if length <= 1:
            if self.channel:
                self.channel("2-Opt: Not enough elements to optimize.")
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
            endpoints[i] = complex(ordered[i].start()), i, ~i, complex(ordered[i].end())
        indexes0 = np.arange(0, length - 1)
        indexes1 = indexes0 + 1

        def log_progress(pos):
            starts = endpoints[indexes0, -1]
            ends = endpoints[indexes1, 0]
            dists = np.abs(starts - ends)
            dist_sum = dists.sum() + abs(curr - endpoints[0][0])
            if self.channel:
                self.channel(
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
                if self.channel:
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
                    if self.channel:
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
                if self.channel:
                    log_progress(length)
            if current_pass >= passes:
                break
            current_pass += 1

        # Two-opt complete.
        order = endpoints[:, 1].real.astype(int)
        ordered.reordered(order)
        if self.channel:
            end_times = times()
            end_length = ordered.length_travel(True)
            self.channel(
                (
                    "Length at end: {length:.0f} mils ({delta:+.0%}), "
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

    def inner_selection_cutcode(self, context: CutCode):
        """
        Selects cutcode from candidate cutcode permitted but does nothing to optimize beyond
        finding a valid solution.

        This routine runs if opt_inner first is selected and opt_greedy is not selected.
        """
        if self.channel:
            start_length = context.length_travel(True)
            start_time = time()
            start_times = times()
            self.channel("Executing Inner Selection-Only optimization")
            self.channel(
                "Length at start: {length:.0f} mils".format(length=start_length)
            )

        for c in context.flat():
            c.burns_done = 0

        ordered = CutCode()
        iterations = 0
        while True:
            c = list(context.candidate(grouped_inner=self.grouped_inner()))
            if len(c) == 0:
                break
            for o in c:
                o.burns_done += 1
            ordered.extend(copy(c))
            iterations += 1

        if self.channel:
            end_times = times()
            end_length = ordered.length_travel(True)
            self.channel(
                (
                    "Length at end: {length:.0f} mils ({delta:+.0%}), "
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


def is_inside(inner, outer):
    """
    Test that path1 is inside path2.
    :param inner_path: inner path
    :param outer_path: outer path
    :return: whether path1 is wholly inside path2.
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


def needs_actualization(image_element, step_level=None):
    if not isinstance(image_element, SVGImage):
        return False
    if step_level is None:
        if "raster_step" in image_element.values:
            step_level = float(image_element.values["raster_step"])
        else:
            step_level = 1.0
    m = image_element.transform
    # Transformation must be uniform to permit native rastering.
    return m.a != step_level or m.b != 0.0 or m.c != 0.0 or m.d != step_level


def make_actual(image_element, step_level=None):
    """
    Makes PIL image actual in that it manipulates the pixels to actually exist
    rather than simply apply the transform on the image to give the resulting image.
    Since our goal is to raster the images real pixels this is required.

    SVG matrices are defined as follows.
    [a c e]
    [b d f]

    Pil requires a, c, e, b, d, f accordingly.
    """
    if not isinstance(image_element, SVGImage):
        return

    if step_level is None:
        # If we are not told the step amount either draw it from the object or set it to default.
        if "raster_step" in image_element.values:
            step_level = float(image_element.values["raster_step"])
        else:
            step_level = 1.0
    image_element.image, image_element.transform = actualize(
        image_element.image, image_element.transform, step_level=step_level
    )
    image_element.image_width, image_element.image_height = (
        image_element.image.width,
        image_element.image.height,
    )
    image_element.width, image_element.height = (
        image_element.image_width,
        image_element.image_height,
    )
    image_element.cache = None
