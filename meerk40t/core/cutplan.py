"""
CutPlan contains code to process LaserOperations into CutCode objects which are spooled.

CutPlan handles the various complicated algorithms to optimising the sequence of CutObjects to:
*   Sort burns so that travel time is minimised
*   Do burns with multiple passes all at the same time (Merge Passes)
*   Sort burns for all operations at the same time rather than operation by operation
*   Ensure that elements inside closed cut paths are burned before the outside path
*   Group these inner burns so that one component on a sheet is completed before the next one is started
*   Ensure that non-closed paths start from one of the ends and burned in one continuous burn
    rather than being burned in 2 or more separate parts
*   Split raster images in to self-contained areas to avoid sweeping over large empty areas
    including splitting into individual small areas if burn inner first is set and then recombining
    those inside the same curves so that raster burns are fully optimised.
"""

from copy import copy
from math import isinf
from os import times
from time import perf_counter, time
from typing import Optional

import numpy as np

from ..svgelements import Group, Polygon
from ..tools.geomstr import Geomstr
from ..tools.pathtools import VectorMontonizer
from .cutcode.cutcode import CutCode
from .cutcode.cutgroup import CutGroup
from .cutcode.cutobject import CutObject
from .cutcode.rastercut import RasterCut
from .node.node import Node
from .node.util_console import ConsoleOperation
from .units import Length


class CutPlanningFailedError(Exception):
    pass


class CutPlan:
    """
    CutPlan is a centralized class to modify plans during cutplanning. It is typically is used to progress from
    copied operations through the stages to being properly optimized cutcode.

    The stages are:
    1. Copy: This can be `copy-selected` or `copy` to decide which operations are moved initially into the plan.
        a. Copied operations are copied to real. All the reference nodes are replaced with copies of the actual elements
    2. Preprocess: Convert from scene space to device space and add validation operations.
    3. Validate: Run all the validation operations, this could be anything the nodes added during preprocess.
        a. Calls `execute` operation.
    4. Blob: We convert all the operations/elements into proper cutcode. Some operations do not necessarily need to
        convert to cutcode. They merely need to convert to some type of spoolable operation.
    5. Preopt: Preoptimize adds in the relevant optimization operations into the cutcode.
    6. Optimize: This calls the added functions set during the preopt process.
        a. Calls `execute` operation.
    """

    def __init__(self, name, planner):
        self.name = name
        self.context = planner
        self.plan = list()
        self.spool_commands = list()
        self.commands = list()
        self.channel = self.context.channel("optimize", timestamp=True)
        self.outline = None
        self._previous_bounds = None

    def __str__(self):
        parts = list()
        parts.append(self.name)
        if len(self.plan):
            parts.append(f"#{len(self.plan)}")
            for p in self.plan:
                try:
                    parts.append(p.__name__)
                except AttributeError:
                    parts.append(p.__class__.__name__)
        else:
            parts.append("-- Empty --")
        return " ".join(parts)

    def execute(self):
        """
        Execute runs all the commands built during `preprocess` and `preopt` (preoptimize) stages.

        If a command's execution adds a command to commands, this command is also executed.
        @return:
        """
        # Using copy of commands, so commands can add ops.
        while self.commands:
            # Executing command can add a command, complete them all.
            commands = self.commands[:]
            self.commands.clear()
            for command in commands:
                command()

    def final(self):
        """
        Executes all the spool_commands built during the other stages.

        If a command's execution added a spool_command we run it during final.

        Final is called during at the time of spool. Just before the laserjob is created.
        @return:
        """
        # Using copy of commands, so commands can add ops.
        while self.spool_commands:
            # Executing command can add a command, complete them all.
            commands = self.spool_commands[:]
            self.spool_commands.clear()
            for command in commands:
                command()

    def preprocess(self):
        """
        Preprocess stage.

        All operation nodes are called with the current context, the matrix converting from scene to device, and
        commands.

        Nodes are expected to convert relevant properties and shapes from scene coordinates to device coordinate systems
        if they need operations. They are also expected to add any relevant commands to the commands list. The commands
        list sequentially in the next stage.
        """
        device = self.context.device

        scene_to_device_matrix = device.view.matrix

        # ==========
        # Determine the jobs bounds.
        # ==========
        bounds = Node.union_bounds(self.plan, bounds=self._previous_bounds)
        self._previous_bounds = bounds
        if bounds is not None:
            left, top, right, bottom = bounds
            min_x = min(right, left)
            min_y = min(top, bottom)
            max_x = max(right, left)
            max_y = max(top, bottom)
            if isinf(min_x) or isinf(min_y) or isinf(max_x) or isinf(max_y):
                # Infinite bounds are invalid.
                self.outline = None
            else:
                self.outline = (
                    device.view.position(min_x, min_y, margins=False),
                    device.view.position(max_x, min_y, margins=False),
                    device.view.position(max_x, max_y, margins=False),
                    device.view.position(min_x, max_y, margins=False),
                )

        # ==========
        # Query Placements
        # ==========
        placements = []
        for place in self.plan:
            if not hasattr(place, "type"):
                continue
            if place.type.startswith("place "):
                if hasattr(place, "output") and place.output:
                    loops = 1
                    if hasattr(place, "loops") and place.loops > 1:
                        loops = place.loops
                    for idx in range(loops):
                        placements.extend(
                            place.placements(
                                self.context, self.outline, scene_to_device_matrix, self
                            )
                        )
        if not placements:
            # Absolute coordinates.
            placements.append(scene_to_device_matrix)

        original_ops = copy(self.plan)
        if self.context.opt_raster_optimisation and self.context.do_optimization:
            try:
                margin = float(Length(self.context.opt_raster_opt_margin, "0"))
            except (AttributeError, ValueError):
                margin = 0
            self.optimize_rasters(original_ops, "op raster", margin)
            # We could do this as well, but images are burnt separately anyway...
            # self.optimize_rasters(original_ops, "op image", margin)
        self.plan.clear()

        idx = 0
        self.context.elements.mywordlist.push()

        perform_simplify = (
            self.context.opt_reduce_details and self.context.do_optimization
        )
        tolerance = self.context.opt_reduce_tolerance
        for placement in placements:
            # Adjust wordlist
            if idx > 0:
                self.context.elements.mywordlist.move_all_indices(1)

            for original_op in original_ops:
                # First, do we have a valid coolant aka airassist command?
                if hasattr(original_op, "coolant"):
                    cool = original_op.coolant
                    if cool is None:
                        cool = 0
                    if cool in (1, 2):  # Explicit on / off
                        if cool == 1:
                            cmd = "coolant_on"
                        else:
                            cmd = "coolant_off"
                        coolop = ConsoleOperation(command=cmd)
                        self.plan.append(coolop)
                try:
                    op = original_op.copy_with_reified_tree()
                except AttributeError:
                    op = original_op
                if not hasattr(op, "type") or op.type is None:
                    self.plan.append(op)
                    continue
                if op.type.startswith("place "):
                    continue
                self.plan.append(op)
                if op.type.startswith("op") or op.type.startswith("util"):
                    # Call preprocess on any op or util ops in our list.
                    if hasattr(op, "preprocess"):
                        op.preprocess(self.context, placement, self)
                if op.type.startswith("op"):
                    for node in op.flat():
                        if node is op:
                            continue
                        if hasattr(node, "geometry") and perform_simplify:
                            # We are still in scene reolution and not yet at device level
                            node.geometry = node.geometry.simplify(tolerance=tolerance)
                        if hasattr(node, "mktext") and hasattr(node, "_cache"):
                            newtext = self.context.elements.wordlist_translate(
                                node.mktext, elemnode=node, increment=False
                            )
                            oldtext = getattr(node, "_translated_text", "")
                            # print (f"Was called inside preprocess for {node.type} with {node.mktext}, old: {oldtext}, new:{newtext}")
                            if newtext != oldtext:
                                node._translated_text = newtext
                                kernel = self.context.elements.kernel
                                for property_op in kernel.lookup_all("path_updater/.*"):
                                    property_op(kernel.root, node)
                                if hasattr(node, "_cache"):
                                    node._cache = None
                        if hasattr(node, "preprocess"):
                            node.preprocess(self.context, placement, self)
            idx += 1
        self.context.elements.mywordlist.pop()

    def _to_grouped_plan(self, plan):
        """
        Break operations into grouped sequences of Operations and utility operations.

        We can only merge between contiguous groups of operations. We cannot merge util node types with op node types.

        Anything that does not have a type is likely able to spool, but cannot merge and are not grouped. Only grouped
        operations are candidates for cutcode merging.
        @return:
        """
        last_type = None
        group = list()
        for c in plan:
            c_type = (
                c.type
                if hasattr(c, "type") and c.type is not None
                else type(c).__name__
            )
            if c_type.startswith("effect"):
                # Effects should not be used here.
                continue
            if last_type is not None:
                if c_type.startswith("op") != last_type.startswith("op"):
                    # This cannot merge
                    yield group
                    group = list()
            group.append(c)
            last_type = c_type
        if group:
            yield group

    def _to_blob_plan_passes_first(self, grouped_plan):
        """
        If Merge operations and not merge passes we need to iterate passes first and operations second.

        This function is specific to that case, when passes first operations second.

        Converts the operations to cutcode.
        @param grouped_plan:
        @return:
        """
        for plan in grouped_plan:
            pass_idx = 0
            while True:
                more_passes_possible = False
                for op in plan:
                    if (
                        not hasattr(op, "type")
                        or op.type == "util console"
                        or (
                            not op.type.startswith("op")
                            and not op.type.startswith("util")
                        )
                    ):
                        # This is an irregular object and can't become cutcode.
                        if pass_idx == 0:
                            # irregular objects have an implicit single pass.
                            yield op
                        continue
                    if pass_idx > op.implicit_passes - 1:
                        continue
                    more_passes_possible = True
                    yield from self._blob_convert(op, 1, 1, force_idx=pass_idx)
                if not more_passes_possible:
                    # No operation needs additional passes.
                    break
                pass_idx += 1

    def _to_blob_plan(self, grouped_plan):
        """
        Iterate operations first and passes second. Operation first mode. Passes are done within cutcode pass value.

        Converts the operations to cutcode.

        @param grouped_plan:
        @return:
        """
        context = self.context
        for plan in grouped_plan:
            for op in plan:
                if not hasattr(op, "type") or op.type is None:
                    yield op
                    continue
                if (
                    not op.type.startswith("op")
                    and not op.type.startswith("util")
                    or op.type == "util console"
                ):
                    yield op
                    continue
                passes = op.implicit_passes
                if context.opt_merge_passes and (
                    context.opt_nearest_neighbor or context.opt_inner_first
                ):
                    # Providing we do some sort of post-processing of blobs,
                    # then merge passes is handled by the greedy or inner_first algorithms

                    # So, we only need 1 copy and to set the passes.
                    yield from self._blob_convert(op, copies=1, passes=passes)
                else:
                    # We do passes by making copies of the cutcode.
                    yield from self._blob_convert(op, copies=passes, passes=1)

    def _blob_convert(self, op, copies, passes, force_idx=None):
        """
        Converts the given op into cutcode. Provides `copies` copies of that cutcode, sets
        the passes to passes for each cutcode object.

        @param op:
        @param copies:
        @param passes:
        @param force_idx:
        @return:
        """
        context = self.context
        for pass_idx in range(copies):
            # if the settings dictionary doesn't exist we use the defined instance dictionary
            try:
                settings_dict = op.settings
            except AttributeError:
                settings_dict = op.__dict__
            # If passes isn't equal to implicit passes then we need a different settings to permit change
            settings = (
                settings_dict if op.implicit_passes == passes else dict(settings_dict)
            )
            cutcode = CutCode(
                op.as_cutobjects(
                    closed_distance=context.opt_closed_distance,
                    passes=passes,
                    plan=self,
                ),
                settings=settings,
            )
            if len(cutcode) == 0:
                break
            cutcode.constrained = op.type == "op cut" and context.opt_inner_first
            cutcode.pass_index = pass_idx if force_idx is None else force_idx
            cutcode.original_op = op.type
            yield cutcode

    def _to_merged_plan(self, blob_plan):
        """
        Convert the blobbed plan of cutcode (rather than operations) into a merged plan for those cutcode operations
        which are permitted to merge into the same cutcode object. All items within the same cutcode object are
        candidates for optimizations. For example, if a HomeCut was merged LineCut in the cutcode, that entire group
        would merge together, finding the most optimized time to home the machine (if optimization was enabled).

        @param blob_plan:
        @return:
        """
        last_item = None
        context = self.context
        for blob in blob_plan:
            try:
                blob.jog_distance = context.opt_jog_minimum
                blob.jog_enable = context.opt_rapid_between
            except AttributeError:
                pass
            if last_item and self._should_merge(context, last_item, blob):
                # Do not check empty plan.
                if blob.constrained:
                    # if any merged object is constrained, then combined blob is also constrained.
                    last_item.constrained = True
                last_item.extend(blob)

            else:
                if isinstance(blob, CutObject) and not isinstance(blob, CutCode):
                    cc = CutCode([blob])
                    cc.original_op = blob.original_op
                    cc.pass_index = blob.pass_index
                    last_item = cc
                    yield last_item
                else:
                    last_item = blob
                    yield last_item

    def _should_merge(self, context, last_item, current_item):
        """
        Checks whether we should merge the blob with the current plan.

        We can only merge things if we have the right objects and settings.
        """
        if not isinstance(last_item, CutCode):
            # The last plan item is not cutcode, merge is only between cutobjects adding to cutcode.
            return False
        if not isinstance(current_item, CutObject):
            # The object to be merged is not a cutObject and cannot be added to Cutcode.
            return False
        last_op = last_item.original_op
        if last_op is None:
            last_op = ""
        current_op = current_item.original_op
        if current_op is None:
            current_op = ""
        if last_op.startswith("util") or current_op.startswith("util"):
            return False

        if (
            not context.opt_merge_passes
            and last_item.pass_index != current_item.pass_index
        ):
            # Do not merge if opt_merge_passes is off, and pass_index do not match
            return False
        if (
            not context.opt_merge_ops
            and last_item.settings is not current_item.settings
        ):
            # Do not merge if opt_merge_ops is off, and the original ops do not match
            # Same settings object implies same original operation
            return False
        if not context.opt_inner_first and last_item.original_op == "op cut":
            # Do not merge if opt_inner_first is off, and operation was originally a cut.
            return False
        return True  # No reason these should not be merged.

    def geometry(self):
        """
        Geometry converts User operations to naked geomstr objects.
        """

        if not self.plan:
            return

        plan = list(self.plan)
        self.plan.clear()
        g = Geomstr()
        settings_index = 0
        for c in plan:
            c_type = (
                c.type
                if hasattr(c, "type") and c.type is not None
                else type(c).__name__
            )
            settings_index += 1
            if hasattr(c, "settings"):
                settings = dict(c.settings)
            else:
                settings = dict(c.__dict__)
            g.settings(settings_index, settings)

            if c_type in ("op cut", "op engrave"):
                for elem in c.children:
                    if hasattr(elem, "final_geometry"):
                        start_index = g.index
                        g.append(elem.final_geometry())
                        end_index = g.index
                        g.flag_settings(settings_index, start_index, end_index)
                    elif hasattr(elem, "as_geometry"):
                        start_index = g.index
                        g.append(elem.as_geometry())
                        end_index = g.index
                        g.flag_settings(settings_index, start_index, end_index)
            elif c_type in ("op raster", "op image"):
                for elem in c.children:
                    if hasattr(elem, "as_image"):
                        settings["raster"] = True
                        image, box = elem.as_image()
                        m = elem.matrix
                        start_index = g.index
                        image_geom = Geomstr.image(image)
                        image_geom.transform(m)
                        g.append(image_geom)
                        end_index = g.index
                        g.flag_settings(settings_index, start_index, end_index)
            else:
                if g:
                    self.plan.append(g)
                    g = Geomstr()
                self.plan.append(c)
        if g:
            self.plan.append(g)

    def blob(self):
        """
        Blob converts User operations to CutCode objects.

        In order to have CutCode objects in the correct sequence for merging we need to:
        1. Break operations into grouped sequences of Operations and utility operations.
           We can only merge between contiguous groups of operations (with option set)
        2. The sequence of CutObjects needs to reflect merge settings
           Normal sequence is to iterate operations and then passes for each operation.
           With Merge ops and not Merge passes, we need to iterate on passes first and then ops within.
        """

        if not self.plan:
            return
        context = self.context
        grouped_plan = list(self._to_grouped_plan(self.plan))
        if context.opt_merge_ops and not context.opt_merge_passes:
            blob_plan = list(self._to_blob_plan_passes_first(grouped_plan))
        else:
            blob_plan = list(self._to_blob_plan(grouped_plan))
        self.plan.clear()
        self.plan.extend(self._to_merged_plan(blob_plan))

    def preopt(self):
        """
        Add commands for optimize stage. This stage tends to do very little but checks the settings and adds the
        relevant operations.

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
                self.commands.append(self.optimize_travel_2opt)

        elif context.opt_inner_first:
            self.commands.append(self.optimize_cuts)
        self.commands.append(self.merge_cutcode)
        if context.opt_reduce_directions:
            pass
        if context.opt_remove_overlap:
            pass

    def optimize_travel_2opt(self):
        """
        Optimize travel 2opt at optimize stage on cutcode
        @return:
        """
        busy = self.context.kernel.busyinfo
        _ = self.context.kernel.translation
        if busy.shown:
            busy.change(msg=_("Optimize inner travel"), keep=1)
            busy.show()
        channel = self.context.channel("optimize", timestamp=True)
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                self.plan[i] = short_travel_cutcode_2opt(
                    self.plan[i], kernel=self.context.kernel, channel=channel
                )

    def optimize_cuts(self):
        """
        Optimize cuts at optimize stage on cutcode
        @return:
        """
        # Update Info-panel if displayed
        busy = self.context.kernel.busyinfo
        _ = self.context.kernel.translation
        if busy.shown:
            busy.change(msg=_("Optimize cuts"), keep=1)
            busy.show()
        tolerance = 0
        if self.context.opt_inner_first:
            stol = self.context.opt_inner_tolerance
            try:
                tolerance = (
                    float(Length(stol))
                    * 2
                    / (
                        self.context.device.view.native_scale_x
                        + self.context.device.view.native_scale_y
                    )
                )
            except ValueError:
                pass
        # print(f"Tolerance: {tolerance}")

        channel = self.context.channel("optimize", timestamp=True)
        grouped_inner = self.context.opt_inner_first and self.context.opt_inners_grouped
        for i, c in enumerate(self.plan):
            if busy.shown:
                busy.change(
                    msg=_("Optimize cuts") + f" {i + 1}/{len(self.plan)}", keep=1
                )
                busy.show()
            if isinstance(c, CutCode):
                if c.constrained:
                    self.plan[i] = inner_first_ident(
                        c,
                        kernel=self.context.kernel,
                        channel=channel,
                        tolerance=tolerance,
                    )
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
        # Update Info-panel if displayed
        busy = self.context.kernel.busyinfo
        _ = self.context.kernel.translation
        if busy.shown:
            busy.change(msg=_("Optimize travel"), keep=1)
            busy.show()
        try:
            last = self.context.device.native
        except AttributeError:
            last = None
        tolerance = 0
        if self.context.opt_inner_first:
            stol = self.context.opt_inner_tolerance
            try:
                tolerance = (
                    float(Length(stol))
                    * 2
                    / (
                        self.context.device.view.native_scale_x
                        + self.context.device.view.native_scale_y
                    )
                )
            except ValueError:
                pass
        # print(f"Tolerance: {tolerance}")

        channel = self.context.channel("optimize", timestamp=True)
        grouped_inner = self.context.opt_inner_first and self.context.opt_inners_grouped
        for i, c in enumerate(self.plan):
            if busy.shown:
                busy.change(
                    msg=_("Optimize travel") + f" {i + 1}/{len(self.plan)}", keep=1
                )
                busy.show()

            if isinstance(c, CutCode):
                if c.constrained:
                    self.plan[i] = inner_first_ident(
                        c,
                        kernel=self.context.kernel,
                        channel=channel,
                        tolerance=tolerance,
                    )
                    c = self.plan[i]
                if last is not None:
                    c._start_x, c._start_y = last
                self.plan[i] = short_travel_cutcode(
                    c,
                    kernel=self.context.kernel,
                    channel=channel,
                    complete_path=self.context.opt_complete_subpaths,
                    grouped_inner=grouped_inner,
                )
                last = self.plan[i].end

    def merge_cutcode(self):
        """
        Merge all adjacent optimized cutcode into single cutcode objects.
        @return:
        """
        busy = self.context.kernel.busyinfo
        _ = self.context.kernel.translation
        if busy.shown:
            busy.change(msg=_("Merging cutcode"), keep=1)
            busy.show()
        for i in range(len(self.plan) - 1, 0, -1):
            cur = self.plan[i]
            prev = self.plan[i - 1]
            if isinstance(cur, CutCode) and isinstance(prev, CutCode):
                prev.extend(cur)
                del self.plan[i]

    def clear(self):
        self._previous_bounds = None
        self.plan.clear()
        self.commands.clear()

    def optimize_rasters(self, operation_list, op_type, margin):
        def generate_clusters(operation):
            def overlapping(bounds1, bounds2, margin):
                # The rectangles don't overlap if
                # one rectangle's minimum in some dimension
                # is greater than the other's maximum in
                # that dimension.
                flagx = (bounds1[0] > bounds2[2] + margin) or (
                    bounds2[0] > bounds1[2] + margin
                )
                flagy = (bounds1[1] > bounds2[3] + margin) or (
                    bounds2[1] > bounds1[3] + margin
                )
                return bool(not (flagx or flagy))

            clusters = list()
            cluster_bounds = list()
            for child in operation.children:
                try:
                    if child.type == "reference":
                        child = child.node
                    bb = child.paint_bounds
                except AttributeError:
                    # Either no element node or does not have bounds
                    continue
                clusters.append([child])
                cluster_bounds.append(
                    (
                        bb[0],
                        bb[1],
                        bb[2],
                        bb[3],
                    )
                )

            def detail_overlap(index1, index2):
                # But is there a real overlap, or just one with the union bounds?
                for outer_node in clusters[index1]:
                    try:
                        bb_outer = outer_node.paint_bounds
                    except AttributeError:
                        continue
                    for inner_node in clusters[index2]:
                        try:
                            bb_inner = inner_node.paint_bounds
                        except AttributeError:
                            continue
                        if overlapping(bb_outer, bb_inner, margin):
                            return True
                # We did not find anything...
                return False

            needs_repeat = True
            while needs_repeat:
                needs_repeat = False
                for outer_idx in range(len(clusters) - 1, -1, -1):
                    # Loop downwards as we are manipulating the arrays
                    bb = cluster_bounds[outer_idx]
                    for inner_idx in range(outer_idx - 1, -1, -1):
                        cc = cluster_bounds[inner_idx]
                        if not overlapping(bb, cc, margin):
                            continue
                        # Overlap!
                        # print (f"Reuse cluster {inner_idx} for {outer_idx}")
                        real_overlap = detail_overlap(outer_idx, inner_idx)
                        if real_overlap:
                            needs_repeat = True
                            # We need to extend the inner cluster by the outer
                            clusters[inner_idx].extend(clusters[outer_idx])
                            cluster_bounds[inner_idx] = (
                                min(bb[0], cc[0]),
                                min(bb[1], cc[1]),
                                max(bb[2], cc[2]),
                                max(bb[3], cc[3]),
                            )
                            clusters.pop(outer_idx)
                            cluster_bounds.pop(outer_idx)
                            # We are done with the inner loop, as we effectively
                            # destroyed the cluster element we compared
                            break

            return clusters

        stime = perf_counter()
        scount = 0
        ecount = 0
        for idx in range(len(operation_list) - 1, -1, -1):
            op = operation_list[idx]
            if (
                not hasattr(op, "type")
                or not hasattr(op, "children")
                or op.type != op_type
            ):
                # That's not what we are looking for
                continue
            scount += 1
            clusters = generate_clusters(op)
            ecount += len(clusters)
            if len(clusters) > 0:
                # Create cluster copies of the raster op
                for entry in clusters:
                    newop = copy(op)
                    newop._references.clear()
                    for node in entry:
                        newop.add_reference(node)
                    newop.set_dirty_bounds()
                    operation_list.insert(idx + 1, newop)

                # And remove the original one...
                operation_list.pop(idx)
        etime = perf_counter()
        if self.channel:
            self.channel(
                f"Optimise {op_type} finished after {etime-stime:.2f} seconds, inflated {scount} operations to {ecount}"
            )


def is_inside(inner, outer, tolerance=0):
    """
    Test that path1 is inside path2.
    @param inner: inner path
    @param outer: outer path
    @param tolerance: 0
    @return: whether path1 is wholly inside path2.
    """
    # We still consider a path to be inside another path if it is
    # within a certain tolerance
    inner_path = inner
    outer_path = outer
    if outer == inner:  # This is the same object.
        return False
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
            inner.bounding_box[0] <= outer.bounding_box[2] + tolerance
            and inner.bounding_box[1] <= outer.bounding_box[3] + tolerance
            and inner.bounding_box[2] >= outer.bounding_box[0] - tolerance
            and inner.bounding_box[3] >= outer.bounding_box[1] - tolerance
        )
    if outer.bounding_box[0] > inner.bounding_box[0] + tolerance:
        # outer minx > inner minx (is not contained)
        return False
    if outer.bounding_box[1] > inner.bounding_box[1] + tolerance:
        # outer miny > inner miny (is not contained)
        return False
    if outer.bounding_box[2] < inner.bounding_box[2] - tolerance:
        # outer maxx < inner maxx (is not contained)
        return False
    if outer.bounding_box[3] < inner.bounding_box[3] - tolerance:
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

    # def vm_code(outer, outer_path, inner, inner_path):
    #     if not hasattr(outer, "vm"):
    #         outer_path = Polygon(
    #             [outer_path.point(i / 1000.0, error=1e4) for i in range(1001)]
    #         )
    #         vm = VectorMontonizer()
    #         vm.add_polyline(outer_path)
    #         outer.vm = vm
    #     for i in range(101):
    #         p = inner_path.point(
    #             i / 100.0, error=1e4
    #         )  # Point(4633.110682926033,1788.413481872459)
    #         if not outer.vm.is_point_inside(p.x, p.y, tolerance=tolerance):
    #             return False
    #     return True

    def sb_code(out_cut, out_path, in_cut, in_path):
        from ..tools.geomstr import Polygon as Gpoly
        from ..tools.geomstr import Scanbeam

        if not hasattr(out_cut, "sb"):
            pg = out_path.npoint(np.linspace(0, 1, 1001), error=1e4)
            pg = pg[:, 0] + pg[:, 1] * 1j

            out_path = Gpoly(*pg)
            sb = Scanbeam(out_path.geomstr)
            out_cut.sb = sb
        p = in_path.npoint(np.linspace(0, 1, 101), error=1e4)
        points = p[:, 0] + p[:, 1] * 1j

        q = out_cut.sb.points_in_polygon(points)
        return q.all()

    return sb_code(outer, outer_path, inner, inner_path)
    # return vm_code(outer, outer_path, inner, inner_path)


def reify_matrix(self):
    """Apply the matrix to the path and reset matrix."""
    self.element = abs(self.element)
    self.scene_bounds = None


# def bounding_box(elements):
#     if isinstance(elements, SVGElement):
#         elements = [elements]
#     elif isinstance(elements, list):
#         try:
#             elements = [e.object for e in elements if isinstance(e.object, SVGElement)]
#         except AttributeError:
#             pass
#     boundary_points = []
#     for e in elements:
#         box = e.bbox(False)
#         if box is None:
#             continue
#         top_left = e.transform.point_in_matrix_space([box[0], box[1]])
#         top_right = e.transform.point_in_matrix_space([box[2], box[1]])
#         bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
#         bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
#         boundary_points.append(top_left)
#         boundary_points.append(top_right)
#         boundary_points.append(bottom_left)
#         boundary_points.append(bottom_right)
#     if len(boundary_points) == 0:
#         return None
#     xmin = min([e[0] for e in boundary_points])
#     ymin = min([e[1] for e in boundary_points])
#     xmax = max([e[0] for e in boundary_points])
#     ymax = max([e[1] for e in boundary_points])
#     return xmin, ymin, xmax, ymax


def correct_empty(context: CutGroup):
    """
    Iterates through backwards deleting any entries that are empty.
    """
    for index in range(len(context) - 1, -1, -1):
        c = context[index]
        if not isinstance(c, CutGroup):
            continue
        correct_empty(c)
        if len(c) == 0:
            del context[index]


def inner_first_ident(context: CutGroup, kernel=None, channel=None, tolerance=0):
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
    total_pass = len(groups) * len(closed_groups)
    context.contains = closed_groups
    if channel:
        channel(
            f"Compare {len(groups)} groups against {len(closed_groups)} closed groups"
        )

    constrained = False
    current_pass = 0
    if kernel:
        busy = kernel.busyinfo
        _ = kernel.translation
    else:
        busy = None
    for outer in closed_groups:
        for inner in groups:
            current_pass += 1
            if outer is inner:
                continue
            # if outer is inside inner, then inner cannot be inside outer
            if inner.contains and outer in inner.contains:
                continue
            if current_pass % 50 == 0 and busy and busy.shown:
                # Can't execute without kernel, reference before assignment is safe.
                message = _("Pass {cpass}/{tpass}").format(
                    cpass=current_pass, tpass=total_pass
                )
                busy.change(msg=message, keep=2)
                busy.show()

            if is_inside(inner, outer, tolerance):
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
            f"Inner paths identified in {time() - start_time:.3f} elapsed seconds: {constrained} "
            f"using {end_times[0] - start_times[0]:.3f} seconds CPU"
        )
    return context


def short_travel_cutcode(
    context: CutCode,
    kernel=None,
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
        channel(f"Length at start: {start_length:.0f} steps")

    curr = context.start
    if curr is None:
        curr = 0
    else:
        curr = complex(curr[0], curr[1])

    cutcode_len = 0
    for c in context.flat():
        cutcode_len += 1
        c.burns_done = 0

    ordered = CutCode()
    current_pass = 0
    if kernel:
        busy = kernel.busyinfo
        _ = kernel.translation
    else:
        busy = None
    # print (f"Cutcode-Len={cutcode_len}")
    while True:
        current_pass += 1
        if current_pass % 50 == 0 and busy and busy.shown:
            # That may not be a fully correct approximation
            # in terms of the total passes required, but it
            # should give an idea...
            message = _("Pass {cpass}/{tpass}").format(
                cpass=current_pass, tpass=cutcode_len
            )
            busy.change(msg=message, keep=2)
            busy.show()
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
    if context.start is not None:
        ordered._start_x, ordered._start_y = context.start
    else:
        ordered._start_x = 0
        ordered._start_y = 0
    if channel:
        end_times = times()
        end_length = ordered.length_travel(True)
        try:
            delta = (end_length - start_length) / start_length
        except ZeroDivisionError:
            delta = 0
        channel(
            f"Length at end: {end_length:.0f} steps "
            f"({delta:+.0%}), "
            f"optimized in {time() - start_time:.3f} "
            f"elapsed seconds using {end_times[0] - start_times[0]:.3f} seconds CPU"
        )
    return ordered


def short_travel_cutcode_2opt(
    context: CutCode, kernel=None, passes: int = 50, channel=None
):
    """
    This implements 2-opt algorithm using numpy.

    Skipping of the candidate code it does not perform inner first optimizations.
    Due to the numpy requirement, doesn't work without numpy.
    --
    Uses code I wrote for vpype:
    https://github.com/abey79/vpype/commit/7b1fad6bd0fcfc267473fdb8ba2166821c80d9cd

    @param context: cutcode to be optimized
    @param kernel: kernel value
    @param passes: max passes to perform 2-opt
    @param channel: Channel to send data about the optimization process.
    @return:
    """
    if channel:
        start_length = context.length_travel(True)
        start_time = time()
        start_times = times()
        channel("Executing 2-Opt Short-Travel optimization")
        channel(f"Length at start: {start_length:.0f} steps")

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
            f"optimize: laser-off distance is {dist_sum}. {100 * pos / length:.02f}% done with pass {current_pass}/{passes}"
        )
        if kernel:
            busy = kernel.busyinfo
            _ = kernel.translation
            if busy.shown:
                busy.change(
                    msg=_("Pass {cpass}/{tpass}").format(
                        cpass=current_pass, tpass=passes
                    ),
                    keep=2,
                )
                busy.show()

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
            f"Length at end: {end_length:.0f} steps "
            f"({(end_length - start_length) / start_length:+.0%}), "
            f"optimized in {time() - start_time:.3f} "
            f"elapsed seconds using {end_times[0] - start_times[0]:.3f} seconds CPU"
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
        channel(f"Length at start: {start_length:.0f} steps")

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
        msg = f"Length at end: {end_length:.0f} steps "
        if start_length != 0:
            msg += f"({(end_length - start_length) / start_length:+.0%}), "
        msg += f"optimized in {time() - start_time:.3f} "
        msg += f"elapsed seconds using {end_times[0] - start_times[0]:.3f} "
        msg += f"seconds CPU in {iterations} iterations"

        channel(msg)
    return ordered
