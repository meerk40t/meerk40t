"""
CutPlan contains code to process LaserOperations into CutCode objects which are spooled.

CutPlan handles the various complicated algorithms to optimising the sequence of CutObjects to:
*   Sort burns so that travel time is minimised
*   Do burns with multiple passes all at the same time (Merge Passes)
*   Sort burns for all operations at the same time rather than operation by operation
*   Ensure that elements inside closed cut paths are burned before the outside path
*   Group related inner/outer burns into spatial pieces so that each component on a sheet
    is completed before the next one is started, with inner-first constraints maintained within each piece
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

from ..svgelements import Group, Matrix
from .geomstr import Geomstr, stitch_geometries, stitcheable_nodes
from .cutcode.cutcode import CutCode
from .cutcode.cutgroup import CutGroup
from .cutcode.cutobject import CutObject
from .cutcode.rastercut import RasterCut
from .elements.element_types import op_vector_nodes
from .node.node import Node
from .node.util_console import ConsoleOperation
from .units import Length

"""
The time to compile does outweigh the benefit...
try:
    from numba import jit
except Exception as e:
    # Jit does not exist, add a dummy decorator and continue.
    # print (f"Encountered error: {e}")
    def jit(*args, **kwargs):
        def inner(func):
            return func

        return inner
"""


class CutPlanningFailedError(Exception):
    pass


class CutPlan:
    """
    CutPlan is a centralized class to modify plans during cutplanning. It is typically used to progress from
    copied operations through the stages to being properly optimized cutcode.

    The stages are:
    1. Copy: This can be `copy-selected` or `copy` to decide which operations are moved initially into the plan.
        a. Copied operations are copied to real. All the reference nodes are replaced with copies of the actual elements
    2. Preprocess: Convert from scene space to device space and add validation operations.
    3. Validate: Run all the validation operations, this could be anything the nodes added during preprocess.
        a. Calls `execute` operation.
    4. Blob: We convert all the operations/elements into proper cutcode. Some operations do not necessarily need to
        convert to cutcode. They merely need to convert to some type of spoolable operation.
    5. Preopt: Preoptimize adds in the relevant optimization operations into the cutcode. This stage now includes
        three optimization paths: travel optimization, inner-first optimization, and basic cutcode sequencing
        (fallback when no optimization is enabled to ensure proper burns_done handling).
    6. Optimize: This calls the added functions set during the preopt process.
        a. Calls `execute` operation.
    """

    def __init__(self, name, planner):
        self.name = name
        self.context = planner
        self.plan = []
        self.spool_commands = []
        self.commands = []
        self.channel = self.context.channel("optimize", timestamp=True)
        self.outline = None
        self._previous_bounds = None

    def __str__(self):
        parts = [self.name]
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
        self._debug_me("At start of execute")

        while self.commands:
            # Executing command can add a command, complete them all.
            commands = self.commands[:]
            self.commands.clear()
            for command in commands:
                command()
                self._debug_me(f"At end of {command.__name__}")

    def final(self):
        """
        Executes all the spool_commands built during the other stages.

        If a command's execution added a spool_command we run it during final.

        Final is called during at the time of spool. Just before the laserjob is created.
        @return:
        """
        busy = self.context.kernel.busyinfo
        _ = self.context.kernel.translation
        # Using copy of commands, so commands can add ops.
        c_count = 0
        while self.spool_commands:
            # Executing command can add a command, complete them all.
            commands = self.spool_commands[:]
            self.spool_commands.clear()
            for command in commands:
                c_count += 1
                if busy.shown:
                    busy.change(
                        msg=_("Spooling data {count}").format(count=c_count), keep=2
                    )
                    busy.show()
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
            if place.type.startswith("place ") and (
                hasattr(place, "output") and place.output
            ):
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

            current_cool = 0
            for original_op in original_ops:
                # First, do we have a valid coolant aka airassist command?
                # And is this relevant, as in does the device support it?
                coolid = getattr(self.context.device, "device_coolant", "")
                if hasattr(original_op, "coolant"):
                    cool = original_op.coolant
                    if cool is None:
                        cool = 0
                    if cool in (1, 2):  # Explicit on / off
                        if cool != current_cool:
                            cmd = "coolant_on" if cool == 1 else "coolant_off"
                            if coolid:
                                coolop = ConsoleOperation(command=cmd)
                                self.plan.append(coolop)
                            else:
                                self.channel(
                                    "The current device does not support a coolant method"
                                )
                        current_cool = cool
                # Is there already a coolant operation?
                if getattr(original_op, "type", "") == "util console":
                    if original_op.command == "coolant_on":
                        current_cool = 1
                    elif original_op.command == "coolant_off":
                        current_cool = 2

                try:
                    op = original_op.copy_with_reified_tree()
                except AttributeError:
                    op = original_op
                if not hasattr(op, "type") or op.type is None:
                    self.plan.append(op)
                    continue
                op_type = getattr(op, "type", "")
                if op_type.startswith("place "):
                    continue
                if (
                    op_type in op_vector_nodes
                    and self.context.opt_stitching
                    and self.context.do_optimization
                ):
                    # This isn't a lossless operation: dotted/dashed lines will be treated as solid lines
                    try:
                        stitch_tolerance = float(
                            Length(self.context.opt_stitch_tolerance)
                        )
                    except ValueError:
                        stitch_tolerance = 0
                    default_stroke = None
                    default_strokewidth = None
                    geoms = []
                    to_be_deleted = []
                    data = stitcheable_nodes(list(op.flat()), stitch_tolerance)
                    for node in data:
                        if node is op:
                            continue
                        if hasattr(node, "as_geometry"):
                            geom: Geomstr = node.as_geometry()
                            geoms.extend(iter(geom.as_contiguous()))
                            if default_stroke is None and hasattr(node, "stroke"):
                                default_stroke = node.stroke
                            if default_strokewidth is None and hasattr(
                                node, "stroke_width"
                            ):
                                default_strokewidth = node.stroke_width
                            to_be_deleted.append(node)
                    result = stitch_geometries(geoms, stitch_tolerance)
                    if result is not None:
                        # print (f"Paths at start of action: {len(list(op.flat()))}")
                        for node in to_be_deleted:
                            node.remove_node()
                        for idx, g in enumerate(result):
                            node = op.add(
                                label=f"Stitch # {idx + 1}",
                                stroke=default_stroke,
                                stroke_width=default_strokewidth,
                                geometry=g,
                                type="elem path",
                            )
                        # print (f"Paths at start of action: {len(list(op.flat()))}")

                self.plan.append(op)
                if (op_type.startswith("op") or op_type.startswith("util")) and hasattr(
                    op, "preprocess"
                ):
                    op.preprocess(self.context, placement, self)
                if op_type.startswith("op"):
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
        group = []
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
                    group = []
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
                ),
                settings=settings,
            )
            if len(cutcode) == 0:
                break
            op_type = getattr(op, "type", "")
            cutcode.constrained = op_type == "op cut" and context.opt_inner_first
            cutcode.pass_index = pass_idx if force_idx is None else force_idx
            cutcode.original_op = op_type
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
            self.channel(
                f"last_item is no cutcode ({type(last_item).__name__}), can't merge"
            )
            return False
        if not isinstance(current_item, CutObject):
            # The object to be merged is not a cutObject and cannot be added to Cutcode.
            self.channel(
                f"current_item is no cutcode ({type(current_item).__name__}), can't merge"
            )
            return False
        last_op = last_item.original_op
        if last_op is None:
            last_op = ""
        current_op = current_item.original_op
        if current_op is None:
            current_op = ""
        if last_op.startswith("util") or current_op.startswith("util"):
            self.channel(
                f"{last_op} / {current_op} - at least one is a util operation, can't merge"
            )
            return False

        if (
            not context.opt_merge_passes
            and last_item.pass_index != current_item.pass_index
        ):
            # Do not merge if opt_merge_passes is off, and pass_index do not match
            self.channel(
                f"{last_item.pass_index} / {current_item.pass_index} - pass indices are different, can't merge"
            )
            return False

        if (
            not context.opt_merge_ops
            and last_item.settings is not current_item.settings
        ):
            # Do not merge if opt_merge_ops is off, and the original ops do not match
            # Same settings object implies same original operation
            self.channel(
                f"Settings do differ from {last_op} to {current_op} and merge ops= {context.opt_merge_ops}"
            )
            return False
        if not context.opt_inner_first and last_item.original_op == "op cut":
            # Do not merge if opt_inner_first is off, and operation was originally a cut.
            self.channel(
                f"Inner first {context.opt_inner_first}, last op= {last_item.original_op} - Last op was a cut, can't merge"
            )
            return False
        return True  # No reason these should not be merged.

    def _debug_me(self, message):
        debug_level = 0
        if not self.channel:
            return
        self.channel(f"Plan at {message}")
        for pitem in self.plan:
            if isinstance(pitem, (tuple, list)):
                self.channel(f"-{type(pitem).__name__}: {len(pitem)} items")
                if debug_level > 0:
                    for cut in pitem:
                        if isinstance(cut, (tuple, list)):
                            self.channel(
                                f"--{type(pitem).__name__}: {type(cut).__name__}: {len(cut)} items"
                            )
                        else:
                            self.channel(
                                f"--{type(pitem).__name__}: {type(cut).__name__}: --childless--"
                            )

            elif hasattr(pitem, "children"):
                self.channel(
                    f"  {type(pitem).__name__}: {len(pitem.children)} children"
                )
            else:
                self.channel(f"  {type(pitem).__name__}: --childless--")

        self.channel("------------")

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
        t0 = perf_counter()
        context = self.context
        grouped_plan = list(self._to_grouped_plan(self.plan))
        t1 = perf_counter()
        if context.opt_merge_ops and not context.opt_merge_passes:
            blob_plan = list(self._to_blob_plan_passes_first(grouped_plan))
        else:
            blob_plan = list(self._to_blob_plan(grouped_plan))
        t2 = perf_counter()
        self.plan.clear()
        self.plan.extend(self._to_merged_plan(blob_plan))
        t3 = perf_counter()
        if self.channel:
            self.channel(
                f"Blobbed in {t1 - t0:.3f}s, converted to cutcode in {t2 - t1:.3f}s, merged in {t3 - t2:.3f}s, total {t3 - t0:.3f}s"
            )

    def preopt(self):
        """
        Add commands for optimize stage. This stage checks the settings and adds the
        relevant optimization operations.

        The optimization pipeline includes three main paths with clear priority hierarchy:
        1. Inner-first optimization (when opt_inner_first is enabled) - highest priority
           - Takes precedence over travel-only optimization
           - Includes travel optimization within the inner-first algorithm
           - Uses piece-based processing when grouped_inner is enabled
        2. Travel optimization (when opt_reduce_travel is enabled but opt_inner_first is disabled)
           - Uses nearest neighbor and/or 2-opt algorithms
           - Optimizes travel distance without inner-first constraints
        3. Basic cutcode sequencing (fallback when no optimization is enabled)
           - Ensures proper burns_done logic for multi-pass cuts
           - Maintains cut sequence without optimization

        The basic_cutcode_sequencing fallback ensures burns_done logic is properly
        handled for multi-pass cuts even when all optimization is disabled.

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

        if context.opt_effect_combine:
            self.commands.append(self.combine_effects)
        if self.channel:
            pass  # Channel available but nothing to do right now
            # self.channel("Dumping scenarios:")
            # self.commands.append(self._dump_scenario)

        # When effect_combine is True but effect_optimize is False, skip travel optimization
        # and use basic sequencing to prevent skip-marked groups from being optimized
        if context.opt_effect_combine and not context.opt_effect_optimize:
            # Skip all travel optimization for effect-combined groups
            self.commands.append(self.basic_cutcode_sequencing)
        elif context.opt_inner_first:
            # Inner-first optimization takes priority and includes travel optimization
            self.commands.append(self.optimize_cuts)
        elif context.opt_reduce_travel and (
            context.opt_nearest_neighbor or context.opt_2opt
        ):
            # Travel optimization only (when inner-first is not enabled)
            if context.opt_nearest_neighbor:
                self.commands.append(self.optimize_travel)
            if context.opt_2opt:
                self.commands.append(self.optimize_travel_2opt)
        else:
            # Fallback: ensure burns_done logic is handled even when optimization is disabled
            self.commands.append(self.basic_cutcode_sequencing)
        self.commands.append(self.merge_cutcode)

    def combine_effects(self):
        """
        Will browse through the cutcode entries grouping everything together
        that as a common 'source' attribute
        """

        def update_group_sequence(group):
            if len(group) == 0:
                return
            glen = len(group)
            for i, cut_obj in enumerate(group):
                cut_obj.first = i == 0
                cut_obj.last = i == glen - 1
                next_idx = i + 1 if i < glen - 1 else 0
                cut_obj.next = group[next_idx]
                cut_obj.previous = group[i - 1]
            group.path = group._geometry.as_path()

        def update_busy_info(busy, idx, l_pitem, plan_idx, l_plan):
            busy.change(
                msg=_("Combine effect primitives")
                + f" {idx + 1}/{l_pitem} ({plan_idx + 1}/{l_plan})",
                keep=1,
            )
            busy.show()

        def process_plan_item(pitem, busy, total, plan_idx, l_plan):
            grouping = {}
            l_pitem = len(pitem)
            to_be_deleted = []
            combined = 0
            for idx, cut in enumerate(pitem):
                total += 1
                # Reduce progress reporting frequency for better performance
                if busy.shown and total % 200 == 0:  # Less frequent than every 100
                    update_busy_info(busy, idx, l_pitem, plan_idx, l_plan)
                if not isinstance(cut, CutGroup) or cut.origin is None:
                    continue
                combined += process_cut(cut, grouping, pitem, idx, to_be_deleted)
            return grouping, to_be_deleted, combined, total

        def process_cut(cut, grouping, pitem, idx, to_be_deleted):
            # Use dict.get() to avoid double lookup - more efficient than separate 'in' check
            mastercut_idx = grouping.get(cut.origin)
            if mastercut_idx is None:
                grouping[cut.origin] = idx
                return 0
            geom = cut._geometry
            pitem[mastercut_idx].skip = True
            pitem[mastercut_idx].extend(cut)
            pitem[mastercut_idx]._geometry.append(geom)
            cut.clear()
            to_be_deleted.append(idx)
            return 1

        busy = self.context.kernel.busyinfo
        _ = self.context.kernel.translation
        if busy.shown:
            busy.change(msg=_("Combine effect primitives"), keep=1)
            busy.show()
        combined = 0
        l_plan = len(self.plan)
        total = -1
        group_count = 0
        for plan_idx, pitem in enumerate(self.plan):
            # We don't combine across plan boundaries
            if not isinstance(pitem, CutGroup):
                continue
            grouping, to_be_deleted, item_combined, total = process_plan_item(
                pitem, busy, total, plan_idx, l_plan
            )
            combined += item_combined
            group_count += len(grouping)

            for key, item in grouping.items():
                update_group_sequence(pitem[item])

            for p in reversed(to_be_deleted):
                pitem.pop(p)

        if self.channel:
            self.channel(f"Combined: {combined}, groups: {group_count}")

    def basic_cutcode_sequencing(self):
        """
        Basic cutcode sequencing when no optimization is enabled.

        Ensures burns_done logic is properly handled for multi-pass cuts
        even when travel optimization is disabled. Based on the inner_selection_cutcode
        function from 0.98b2 that handled this case.
        """
        busy = self.context.kernel.busyinfo
        _ = self.context.kernel.translation
        if busy.shown:
            busy.change(msg=_("Basic cutcode sequencing"), keep=1)
            busy.show()

        for i, cutcode in enumerate(self.plan):
            if isinstance(cutcode, CutCode):
                if busy.shown:
                    busy.change(
                        msg=_("Basic cutcode sequencing")
                        + f" {i + 1}/{len(self.plan)}",
                        keep=1,
                    )
                    busy.show()

                # Initialize burns_done for all cuts
                for cut in cutcode.flat():
                    cut.burns_done = 0

                # Process cuts respecting burns_done and passes
                ordered = CutCode()
                iterations = 0

                while True:
                    # Get available candidates (burns_done < passes)
                    candidates = list(cutcode.candidate(grouped_inner=False))
                    if not candidates:
                        break

                    # Increment burns_done for all candidates
                    for cut in candidates:
                        cut.burns_done += 1

                    # Add copies to the ordered sequence
                    ordered.extend(copy(candidates))
                    iterations += 1

                # Set start position if available
                if cutcode.start is not None:
                    ordered._start_x, ordered._start_y = cutcode.start
                else:
                    ordered._start_x = 0
                    ordered._start_y = 0

                # Replace the original cutcode with the sequenced version
                self.plan[i] = ordered

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
                self.plan[i] = short_travel_cutcode(
                    self.plan[i], kernel=self.context.kernel, channel=channel
                )

    def optimize_cuts(self):
        """
        Optimize cuts using inner-first algorithm and travel optimization.

        This method handles both inner-first identification (when constrained cutcode
        is present) and travel optimization. The grouped_inner setting determines
        the optimization strategy:

        - grouped_inner=True: Piece-based optimization where related inner/outer
          groups are spatially grouped into pieces. Travel optimization occurs
          between pieces while inner-first constraints are maintained within each piece.

        - grouped_inner=False: Hierarchical processing where groups are processed
          individually while respecting containment relationships.

        The piece-based approach ensures that each spatial component on the sheet
        is completed before moving to the next, minimizing overall travel distance
        while preserving inner-first cutting constraints.

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
                self.plan[i] = short_travel_cutcode(
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
                if last is not None:
                    c._start_x, c._start_y = last
                self.plan[i] = short_travel_cutcode(
                    c,
                    kernel=self.context.kernel,
                    channel=channel,
                    complete_path=self.context.opt_complete_subpaths,
                    grouped_inner=grouped_inner,
                    hatch_optimize=self.context.opt_effect_optimize,
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

    def _dump_scenario(self):
        # Only used for debugging purposes.
        self.save_scenario(
            filename="test_cutplan.json",
            description="Intermediate scenario dump for algorithm testing",
            algorithm_testing=True,
        )
        return

    def save_scenario(self, filename=None, description="", algorithm_testing=False):
        """
        Save the current cutplan state for scenario testing and algorithm validation.

        Saves comprehensive information needed to recreate and test this cutplan:
        - Individual cut data with coordinates for algorithm testing
        - Plan contents (operations and cutcode) for plan reconstruction
        - Key optimization settings from context
        - Plan metadata and travel baselines
        - Algorithm start position

        @param filename: Optional filename to save to. If None, returns the data dict.
        @param description: Optional description of this scenario
        @param algorithm_testing: If True, saves detailed cut data for algorithm validation
        @return: Scenario data dict if filename is None, otherwise saves to file
        """
        import datetime
        import json

        # Extract key optimization settings that affect cutplan behavior
        opt_settings = {}
        if hasattr(self.context, "opt_nearest_neighbor"):
            opt_settings["opt_nearest_neighbor"] = self.context.opt_nearest_neighbor
        if hasattr(self.context, "opt_inner_first"):
            opt_settings["opt_inner_first"] = self.context.opt_inner_first
        if hasattr(self.context, "opt_merge_passes"):
            opt_settings["opt_merge_passes"] = self.context.opt_merge_passes
        if hasattr(self.context, "opt_merge_ops"):
            opt_settings["opt_merge_ops"] = self.context.opt_merge_ops
        if hasattr(self.context, "opt_complete_subpaths"):
            opt_settings["opt_complete_subpaths"] = self.context.opt_complete_subpaths
        if hasattr(self.context, "opt_inners_grouped"):
            opt_settings["opt_inners_grouped"] = self.context.opt_inners_grouped
        if hasattr(self.context, "opt_effect_optimize"):
            opt_settings["opt_effect_optimize"] = self.context.opt_effect_optimize
        if hasattr(self.context, "opt_closed_distance"):
            opt_settings["opt_closed_distance"] = self.context.opt_closed_distance
        if hasattr(self.context, "opt_jog_minimum"):
            opt_settings["opt_jog_minimum"] = self.context.opt_jog_minimum
        if hasattr(self.context, "opt_rapid_between"):
            opt_settings["opt_rapid_between"] = self.context.opt_rapid_between

        # Extract plan contents
        plan_data = []
        individual_cuts = []
        total_unoptimized_travel = 0
        algorithm_start_position = None

        for item in self.plan:
            item_data = {
                "type": type(item).__name__,
            }

            # Handle different item types
            if hasattr(item, "type") and item.type:
                item_data["item_type"] = item.type
            if hasattr(item, "original_op"):
                item_data["original_op"] = item.original_op
            if hasattr(item, "pass_index"):
                item_data["pass_index"] = item.pass_index
            if hasattr(item, "constrained"):
                item_data["constrained"] = item.constrained
            if hasattr(item, "length_travel"):
                try:
                    item_data["travel_length"] = item.length_travel(True)
                except Exception:
                    pass

            # For CutCode objects, save cut count and basic structure
            if hasattr(item, "__len__"):
                item_data["length"] = len(item)
                if hasattr(item, "_start_x") and item._start_x is not None:
                    item_data["start_pos"] = (item._start_x, item._start_y)
                    # Use first cut's start as algorithm start position if not set
                    if algorithm_start_position is None:
                        algorithm_start_position = (item._start_x, item._start_y)
                if hasattr(item, "end"):
                    try:
                        end_pos = item.end
                        if end_pos:
                            item_data["end_pos"] = (end_pos[0], end_pos[1])
                    except Exception:
                        pass

                # Extract individual cuts for algorithm testing
                if algorithm_testing and hasattr(item, "__iter__"):
                    try:
                        # For algorithm testing, we want individual cuts, not group structure
                        # Use flat() method to get all cuts from groups
                        def get_flat_cuts(cut_container):
                            """Get flat list of individual cuts for algorithm testing."""
                            for cut in cut_container:
                                if isinstance(cut, CutGroup):
                                    # Use flat() method to get all individual cuts from the group
                                    yield from cut.flat()
                                else:
                                    # Regular cut object
                                    yield cut

                        for cut in get_flat_cuts(item):
                            if hasattr(cut, "start") and hasattr(cut, "end"):
                                cut_data = {
                                    "cut_type": type(cut).__name__,
                                    "start": [float(cut.start[0]), float(cut.start[1])],
                                    "end": [float(cut.end[0]), float(cut.end[1])],
                                    "passes": getattr(cut, "passes", 1),
                                    "reversible": getattr(
                                        cut, "reversible", lambda: True
                                    )()
                                    if callable(getattr(cut, "reversible", None))
                                    else True,
                                }

                                # Save cut-type specific data
                                if hasattr(cut, "_control1") and hasattr(
                                    cut, "_control2"
                                ):
                                    # CubicCut
                                    cut_data["control1"] = [
                                        float(cut._control1[0]),
                                        float(cut._control1[1]),
                                    ]
                                    cut_data["control2"] = [
                                        float(cut._control2[0]),
                                        float(cut._control2[1]),
                                    ]
                                elif hasattr(cut, "_control"):
                                    # QuadCut
                                    cut_data["control"] = [
                                        float(cut._control[0]),
                                        float(cut._control[1]),
                                    ]

                                # Add cut settings if available
                                if hasattr(cut, "settings") and cut.settings:
                                    settings_copy = {}
                                    for key, value in cut.settings.items():
                                        try:
                                            json.dumps(value)  # Test serializability
                                            settings_copy[key] = value
                                        except (TypeError, ValueError):
                                            settings_copy[key] = str(
                                                type(value).__name__
                                            )
                                    cut_data["settings"] = settings_copy

                                # Add parent group information for reconstruction
                                if hasattr(cut, "parent") and isinstance(
                                    cut.parent, CutGroup
                                ):
                                    cut_data["parent_group_id"] = id(cut.parent)
                                    cut_data["parent_closed"] = getattr(
                                        cut.parent, "closed", False
                                    )
                                    # Find position within parent group
                                    try:
                                        cut_data["group_index"] = list(
                                            cut.parent
                                        ).index(cut)
                                        cut_data["group_size"] = len(cut.parent)
                                    except (ValueError, TypeError):
                                        pass

                                    # Save parent group path information for geometric testing
                                    if (
                                        hasattr(cut.parent, "path")
                                        and cut.parent.path is not None
                                    ):
                                        try:
                                            cut_data[
                                                "parent_path_d"
                                            ] = cut.parent.path.d()
                                        except Exception:
                                            pass

                                    # Save parent group bounding box for faster containment checks
                                    if (
                                        hasattr(cut.parent, "bounding_box")
                                        and cut.parent.bounding_box is not None
                                    ):
                                        try:
                                            cut_data["parent_bounding_box"] = list(
                                                cut.parent.bounding_box
                                            )
                                        except Exception:
                                            pass

                                individual_cuts.append(cut_data)

                                # Calculate unoptimized travel distance for cuts with start positions
                                if cut_data.get("start") and individual_cuts:
                                    prev_end = (
                                        individual_cuts[-2]["end"]
                                        if len(individual_cuts) > 1
                                        and individual_cuts[-2].get("end")
                                        else (algorithm_start_position or [0, 0])
                                    )
                                    if prev_end:
                                        travel_dist = (
                                            (cut_data["start"][0] - prev_end[0]) ** 2
                                            + (cut_data["start"][1] - prev_end[1]) ** 2
                                        ) ** 0.5
                                        total_unoptimized_travel += travel_dist
                    except Exception as e:
                        if self.channel:
                            self.channel(
                                f"Warning: Could not extract cuts from {type(item).__name__}: {e}"
                            )

            # For operations, save key attributes
            if hasattr(item, "settings") and item.settings:
                # Save a copy of settings, excluding any non-serializable objects
                settings_copy = {}
                for key, value in item.settings.items():
                    try:
                        json.dumps(value)  # Test serializability
                        settings_copy[key] = value
                    except (TypeError, ValueError):
                        settings_copy[key] = str(type(value).__name__)
                item_data["settings"] = settings_copy

            plan_data.append(item_data)

        # If no algorithm start position found, use reasonable default
        if algorithm_start_position is None:
            algorithm_start_position = [0, 0]

        # Create base scenario data
        scenario_data = {
            "metadata": {
                "description": description,
                "timestamp": datetime.datetime.now().isoformat(),
                "plan_name": self.name,
                "total_items": len(self.plan),
                "total_travel": self._calculate_total_travel(),
                "algorithm_testing_enabled": algorithm_testing,
            },
            "optimization_settings": opt_settings,
            "plan_contents": plan_data,
        }

        # Add algorithm testing data if requested
        if algorithm_testing and individual_cuts:
            scenario_data["algorithm_testing"] = {
                "start_position": algorithm_start_position,
                "cuts": individual_cuts,
                "original_travel": max(
                    total_unoptimized_travel, self._calculate_total_travel()
                ),
                "cut_count": len(individual_cuts),
            }

            # Add work area bounds for analysis
            if individual_cuts:
                all_x = [cut["start"][0] for cut in individual_cuts] + [
                    cut["end"][0] for cut in individual_cuts
                ]
                all_y = [cut["start"][1] for cut in individual_cuts] + [
                    cut["end"][1] for cut in individual_cuts
                ]
                scenario_data["algorithm_testing"]["work_area"] = {
                    "min_x": min(all_x),
                    "max_x": max(all_x),
                    "min_y": min(all_y),
                    "max_y": max(all_y),
                    "width": max(all_x) - min(all_x),
                    "height": max(all_y) - min(all_y),
                }

        if filename:
            with open(filename, "w") as f:
                json.dump(scenario_data, f, indent=2, default=str)
            if self.channel:
                if algorithm_testing:
                    self.channel(
                        f"Saved algorithm testing scenario to {filename} ({len(individual_cuts)} cuts)"
                    )
                else:
                    self.channel(f"Saved cutplan scenario to {filename}")
            return None
        else:
            return scenario_data

    def _calculate_total_travel(self):
        """Calculate total travel distance across all cutcode in the plan."""
        total_travel = 0
        for item in self.plan:
            if hasattr(item, "length_travel"):
                try:
                    total_travel += item.length_travel(True)
                except Exception:
                    pass
        return total_travel

    def load_scenario(self, filename_or_data):
        """
        Load a previously saved scenario (for informational purposes and algorithm testing).

        Note: This doesn't recreate the full CutPlan as that would require
        the original operations and context. It's primarily for analysis and
        algorithm testing when the scenario includes algorithm_testing data.

        @param filename_or_data: Filename to load from, or scenario data dict
        @return: Scenario data dict
        """
        import json

        if isinstance(filename_or_data, str):
            with open(filename_or_data, "r") as f:
                scenario_data = json.load(f)
        else:
            scenario_data = filename_or_data

        if self.channel:
            meta = scenario_data.get("metadata", {})
            self.channel(
                f"Loaded scenario: {meta.get('description', 'No description')}"
            )
            self.channel(
                f"Items: {meta.get('total_items', 0)}, Travel: {meta.get('total_travel', 0):.0f}"
            )

            # Report algorithm testing capability
            if (
                meta.get("algorithm_testing_enabled", False)
                and "algorithm_testing" in scenario_data
            ):
                alg_data = scenario_data["algorithm_testing"]
                self.channel(
                    f"Algorithm testing data: {len(alg_data.get('cuts', []))} cuts, "
                    f"start at {alg_data.get('start_position', [0, 0])}"
                )

        return scenario_data

    def reconstruct_cutgroups_from_cuts(self, cuts, closed_distance=15):
        """
        Reconstruct CutGroup objects from individual cuts by analyzing connectivity
        and using saved parent group information when available.

        This is needed for algorithm testing scenarios where cuts were flattened
        but we need to recreate the original closed path structure for inner-first
        optimization to work correctly.
        """

        if not cuts:
            return []

        # Check if we have saved parent group information
        has_parent_info = any(
            hasattr(cut, "parent_group_id")
            or (hasattr(cut, "__dict__") and "parent_group_id" in cut.__dict__)
            for cut in cuts
        )

        if has_parent_info:
            # Use saved parent group information for accurate reconstruction
            return self._reconstruct_from_parent_info(cuts)
        else:
            # Fall back to connectivity analysis
            return self._reconstruct_from_connectivity(cuts, closed_distance)

    def _reconstruct_from_parent_info(self, cuts):
        """Reconstruct CutGroups using saved parent group information"""
        from collections import defaultdict

        from meerk40t.core.cutcode.cutgroup import CutGroup

        # Group cuts by their parent group ID
        groups_by_id = defaultdict(list)

        for cut in cuts:
            parent_id = getattr(cut, "parent_group_id", None)
            if parent_id is not None:
                groups_by_id[parent_id].append(cut)
            else:
                # Standalone cut without parent - create individual group
                groups_by_id[id(cut)].append(cut)

        cutgroups = []

        for group_id, group_cuts in groups_by_id.items():
            if not group_cuts:
                continue

            # Sort cuts by their group_index if available
            group_cuts.sort(key=lambda c: getattr(c, "group_index", 0))

            # Get closed status from first cut's parent info
            is_closed = getattr(group_cuts[0], "parent_closed", False)

            # Create CutGroup
            group = CutGroup(
                parent=None,
                children=group_cuts,
                closed=is_closed,
                settings=group_cuts[0].settings if group_cuts else None,
                passes=group_cuts[0].passes if group_cuts else 1,
            )

            # CRITICAL: Populate geometric attributes needed by is_inside function
            # This mirrors what path_to_cutobjects does in nutils.py

            # First, try to restore saved path information if available
            first_cut = group_cuts[0]
            path_restored = False

            if hasattr(first_cut, "parent_path_d"):
                try:
                    from ..svgelements import Path
                    from .geomstr import Geomstr

                    path_obj = Path(first_cut.parent_path_d)
                    setattr(group, "path", path_obj)
                    setattr(group, "_geometry", Geomstr.svg(path_obj.d()))
                    path_restored = True
                except Exception:
                    pass

            # If no saved path, reconstruct from individual cuts
            if not path_restored and len(group_cuts) > 0:
                try:
                    from ..svgelements import Close, Line, Move, Path
                    from .geomstr import Geomstr

                    path_segments = []
                    path_segments.append(Move(group_cuts[0].start))

                    for cut in group_cuts:
                        if hasattr(cut, "end") and hasattr(cut, "start"):
                            path_segments.append(Line(cut.start, cut.end))

                    # Close the path if the group is marked as closed
                    if is_closed and len(group_cuts) > 2:
                        first_start = group_cuts[0].start
                        last_end = group_cuts[-1].end
                        # Add closing line if needed
                        if abs(complex(*first_start) - complex(*last_end)) > 0.1:
                            path_segments.append(Line(last_end, first_start))
                        path_segments.append(Close(first_start))

                    # Create the path and geometry objects (essential for is_inside)
                    constructed_path = Path(*path_segments)
                    setattr(group, "path", constructed_path)
                    setattr(group, "_geometry", Geomstr.svg(constructed_path.d()))

                except Exception:
                    # If path creation fails, at least try to set basic bounding box
                    pass

            # Restore saved bounding box if available
            if hasattr(first_cut, "parent_bounding_box"):
                try:
                    setattr(group, "bounding_box", first_cut.parent_bounding_box)
                except Exception:
                    pass

            # Set up cut relationships within group
            for i, cut in enumerate(group_cuts):
                cut.parent = group
                cut.closed = is_closed
                cut.first = i == 0
                cut.last = i == len(group_cuts) - 1
                cut.next = group_cuts[(i + 1) % len(group_cuts)]
                cut.previous = group_cuts[i - 1]

            cutgroups.append(group)

        return cutgroups

    def _reconstruct_from_connectivity(self, cuts, closed_distance):
        """Reconstruct CutGroups using connectivity analysis (fallback method)"""
        from collections import defaultdict

        from meerk40t.core.cutcode.cutgroup import CutGroup

        # Build connectivity mapping
        cut_endpoints = {}
        connections = defaultdict(list)

        for i, cut in enumerate(cuts):
            start = cut.start
            end = cut.end
            cut_endpoints[i] = (start, end)
            connections[start].append((i, "start"))
            connections[end].append((i, "end"))

        # Find connected components (paths)
        visited = set()
        cutgroups = []

        for start_idx in range(len(cuts)):
            if start_idx in visited:
                continue

            # Trace connected path
            path_cuts = []
            current_cut = start_idx

            while current_cut is not None and current_cut not in visited:
                visited.add(current_cut)
                path_cuts.append(cuts[current_cut])

                # Find next connected cut
                start, end = cut_endpoints[current_cut]

                # Try to continue the path (prefer connected endpoints)
                next_cut = None
                for next_point in [end, start]:  # Try end first, then start
                    for cut_idx, connection_type in connections[next_point]:
                        if cut_idx not in visited:
                            next_cut = cut_idx
                            break
                    if next_cut is not None:
                        break

                current_cut = next_cut

            if path_cuts:
                # Determine if path is closed
                if len(path_cuts) > 1:
                    first_start = path_cuts[0].start
                    last_end = path_cuts[-1].end
                    distance = (
                        (first_start[0] - last_end[0]) ** 2
                        + (first_start[1] - last_end[1]) ** 2
                    ) ** 0.5
                    is_closed = distance <= closed_distance
                else:
                    is_closed = False

                # Create CutGroup
                group = CutGroup(
                    parent=None,
                    children=path_cuts,
                    closed=is_closed,
                    settings=path_cuts[0].settings if path_cuts else None,
                    passes=path_cuts[0].passes if path_cuts else 1,
                )

                # Set up cut relationships within group
                for i, cut in enumerate(path_cuts):
                    cut.parent = group
                    cut.closed = is_closed
                    cut.first = i == 0
                    cut.last = i == len(path_cuts) - 1
                    cut.next = path_cuts[(i + 1) % len(path_cuts)]
                    cut.previous = path_cuts[i - 1]

                cutgroups.append(group)

        return cutgroups

    def create_cuts_from_scenario(self, scenario_data):
        """
        Create cut objects from saved scenario data for algorithm testing.

        This function converts saved algorithm testing data back into cut objects
        that can be used with optimization algorithms. When parent group information
        is available, it reconstructs the original CutGroup structure needed for
        proper inner-first hierarchy detection.

        @param scenario_data: Scenario data dict (from load_scenario)
        @return: Tuple of (cuts, start_position, original_travel) or None if no algorithm data
        """
        if "algorithm_testing" not in scenario_data:
            if self.channel:
                self.channel("No algorithm testing data in scenario")
            return None

        from meerk40t.core.cutcode.cubiccut import CubicCut
        from meerk40t.core.cutcode.linecut import LineCut
        from meerk40t.core.cutcode.quadcut import QuadCut

        alg_data = scenario_data["algorithm_testing"]
        cuts = []

        for cut_data in alg_data["cuts"]:
            cut_type = cut_data.get("cut_type", "LineCut")

            # Create the appropriate cut type
            if (
                cut_type == "CubicCut"
                and "control1" in cut_data
                and "control2" in cut_data
            ):
                cut = CubicCut(
                    (cut_data["start"][0], cut_data["start"][1]),
                    (cut_data["control1"][0], cut_data["control1"][1]),
                    (cut_data["control2"][0], cut_data["control2"][1]),
                    (cut_data["end"][0], cut_data["end"][1]),
                    settings=cut_data.get("settings", {"speed": 1000}),
                    passes=cut_data.get("passes", 1),
                )
            elif cut_type == "QuadCut" and "control" in cut_data:
                cut = QuadCut(
                    (cut_data["start"][0], cut_data["start"][1]),
                    (cut_data["control"][0], cut_data["control"][1]),
                    (cut_data["end"][0], cut_data["end"][1]),
                    settings=cut_data.get("settings", {"speed": 1000}),
                    passes=cut_data.get("passes", 1),
                )
            else:
                # Default to LineCut for all other types (including CutGroup from old files)
                cut = LineCut(
                    (cut_data["start"][0], cut_data["start"][1]),
                    (cut_data["end"][0], cut_data["end"][1]),
                    settings=cut_data.get("settings", {"speed": 1000}),
                    passes=cut_data.get("passes", 1),
                )

            # Set up reversibility
            is_reversible = cut_data.get("reversible", True)
            cut.reversible = lambda: is_reversible
            cut.passes = cut_data.get("passes", 1)
            cut.burns_done = 0

            # Store parent group information for reconstruction
            if "parent_group_id" in cut_data:
                cut._parent_group_id = cut_data["parent_group_id"]
                cut._parent_closed = cut_data.get("parent_closed", False)
                cut._group_index = cut_data.get("group_index", 0)
                cut._group_size = cut_data.get("group_size", 1)
                if "parent_path_d" in cut_data:
                    cut._parent_path_d = cut_data["parent_path_d"]
                if "parent_bounding_box" in cut_data:
                    cut._parent_bounding_box = cut_data["parent_bounding_box"]

            cuts.append(cut)

        start_position = tuple(alg_data["start_position"])
        original_travel = alg_data["original_travel"]

        # Check if we have parent group information to reconstruct CutGroups
        has_parent_info = any(hasattr(cut, "_parent_group_id") for cut in cuts)

        if has_parent_info:
            # Reconstruct CutGroups from parent information for proper hierarchy detection
            if self.channel:
                self.channel("Reconstructing CutGroups from saved parent information")
            cutgroups = self._reconstruct_cutgroups_from_cuts(cuts)
            return cutgroups, start_position, original_travel
        else:
            # No group information available - return individual cuts
            if self.channel:
                self.channel("No parent group information - returning individual cuts")
            return cuts, start_position, original_travel

    def _reconstruct_cutgroups_from_cuts(self, cuts):
        """
        Reconstruct CutGroup objects from individual cuts using saved parent group information.

        This is essential for algorithm testing scenarios where the original CutGroup structure
        with closed path detection and geometric properties needs to be restored for proper
        inner-first hierarchy detection to work.
        """
        from collections import defaultdict

        from meerk40t.core.cutcode.cutgroup import CutGroup

        # Group cuts by their parent group ID
        groups_by_id = defaultdict(list)

        for cut in cuts:
            parent_id = getattr(cut, "_parent_group_id", None)
            if parent_id is not None:
                groups_by_id[parent_id].append(cut)
            else:
                # Standalone cut without parent - create individual group
                groups_by_id[id(cut)].append(cut)

        cutgroups = []

        for group_id, group_cuts in groups_by_id.items():
            if not group_cuts:
                continue

            # Sort cuts by their group_index if available
            group_cuts.sort(key=lambda c: getattr(c, "_group_index", 0))

            # Get closed status from first cut's parent info
            is_closed = getattr(group_cuts[0], "_parent_closed", False)

            # Create CutGroup
            group = CutGroup(
                parent=None,
                children=group_cuts,
                closed=is_closed,
                settings=group_cuts[0].settings if group_cuts else None,
                passes=group_cuts[0].passes if group_cuts else 1,
            )

            # Restore geometric properties essential for is_inside detection
            first_cut = group_cuts[0]

            # Restore saved path information if available
            if hasattr(first_cut, "_parent_path_d"):
                try:
                    from ..svgelements import Path
                    from .geomstr import Geomstr

                    path_obj = Path(first_cut._parent_path_d)
                    setattr(group, "path", path_obj)
                    setattr(group, "_geometry", Geomstr.svg(path_obj.d()))
                except Exception:
                    # If path restoration fails, construct from cuts
                    self._construct_path_from_cuts(group, group_cuts, is_closed)
            else:
                # Construct path from individual cuts
                self._construct_path_from_cuts(group, group_cuts, is_closed)

            # Restore saved bounding box if available
            if hasattr(first_cut, "_parent_bounding_box"):
                try:
                    setattr(group, "bounding_box", first_cut._parent_bounding_box)
                except Exception:
                    pass

            # Set up cut relationships within group
            for i, cut in enumerate(group_cuts):
                cut.parent = group
                cut.closed = is_closed
                cut.first = i == 0
                cut.last = i == len(group_cuts) - 1
                cut.next = group_cuts[(i + 1) % len(group_cuts)]
                cut.previous = group_cuts[i - 1]

            cutgroups.append(group)

        return cutgroups

    def _construct_path_from_cuts(self, group, group_cuts, is_closed):
        """
        Construct Path and geometry objects from individual cuts.
        This is essential for the is_inside function to work properly.
        """
        try:
            from ..svgelements import Close, Line, Move, Path
            from .geomstr import Geomstr

            path_segments = []
            if group_cuts:
                path_segments.append(Move(group_cuts[0].start))

                for cut in group_cuts:
                    if hasattr(cut, "end") and hasattr(cut, "start"):
                        path_segments.append(Line(cut.start, cut.end))

                # Close the path if the group is marked as closed
                if is_closed and len(group_cuts) > 2:
                    first_start = group_cuts[0].start
                    last_end = group_cuts[-1].end
                    # Add closing line if needed
                    if abs(complex(*first_start) - complex(*last_end)) > 0.1:
                        path_segments.append(Line(last_end, first_start))
                    path_segments.append(Close(first_start))

                # Create the path and geometry objects (essential for is_inside)
                constructed_path = Path(*path_segments)
                setattr(group, "path", constructed_path)
                setattr(group, "_geometry", Geomstr.svg(constructed_path.d()))

        except Exception as e:
            # If path construction fails, at least log it
            if self.channel:
                self.channel(f"Failed to construct path for group: {e}")

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
                return not (flagx or flagy)

            clusters = []
            cluster_bounds = []
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
                f"Optimise {op_type} finished after {etime - stime:.2f} seconds, inflated {scount} operations to {ecount}"
            )


def is_inside(inner, outer, tolerance=0, debug=False):
    """
    Test that path1 is inside path2.
    @param inner: inner path
    @param outer: outer path
    @param tolerance: 0
    @param debug: if True, print debug information
    @return: whether path1 is wholly inside path2.
    """

    def convex_geometry(raster) -> Geomstr:
        dx = raster.bounding_box[0]
        dy = raster.bounding_box[1]
        dw = raster.bounding_box[2] - raster.bounding_box[0]
        dh = raster.bounding_box[3] - raster.bounding_box[1]
        if raster.image is None:
            return Geomstr.rect(dx, dy, dw, dh)
        image_np = np.array(raster.image.convert("L"))
        # Find non-white pixels
        # Iterate over each row in the image
        left_side = []
        right_side = []
        for y in range(image_np.shape[0]):
            row = image_np[y]
            non_white_indices = np.where(row < 255)[0]

            if non_white_indices.size > 0:
                leftmost = non_white_indices[0]
                rightmost = non_white_indices[-1]
                left_side.append((leftmost, y))
                right_side.insert(0, (rightmost, y))
        left_side.extend(right_side)
        non_white_pixels = left_side
        # Compute convex hull
        pts = list(Geomstr.convex_hull(None, non_white_pixels))
        if pts:
            pts.append(pts[0])
        geom = Geomstr.lines(*pts)
        sx = dw / raster.image.width
        sy = dh / raster.image.height
        matrix = Matrix()
        matrix.post_scale(sx, sy)
        matrix.post_translate(dx, dy)
        geom.transform(matrix)
        return geom

    # We still consider a path to be inside another path if it is
    # within a certain tolerance
    inner_path = inner
    outer_path = outer
    if outer == inner:  # This is the same object.
        if debug:
            print("DEBUG is_inside: Same object - returning False")
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
        if debug:
            print("DEBUG is_inside: outer.bounding_box is None - returning False")
        return False
    if inner.bounding_box is None:
        if debug:
            print("DEBUG is_inside: inner.bounding_box is None - returning False")
        return False
    if isinstance(inner, RasterCut):
        if not hasattr(inner, "convex_path"):
            inner.convex_path = convex_geometry(inner).as_path()
        inner_path = inner.convex_path

    # Fast bounding box check first
    if outer.bounding_box[0] > inner.bounding_box[2] + tolerance:
        # outer minx > inner maxx (is not contained)
        if debug:
            print(
                f"DEBUG is_inside: Fast bounds check failed - outer.left ({outer.bounding_box[0]}) > inner.right ({inner.bounding_box[2]})"
            )
        return False
    if outer.bounding_box[1] > inner.bounding_box[3] + tolerance:
        # outer miny > inner maxy (is not contained)
        if debug:
            print(
                f"DEBUG is_inside: Fast bounds check failed - outer.top ({outer.bounding_box[1]}) > inner.bottom ({inner.bounding_box[3]})"
            )
        return False
    if outer.bounding_box[2] < inner.bounding_box[0] - tolerance:
        # outer maxx < inner minx (is not contained)
        if debug:
            print(
                f"DEBUG is_inside: Fast bounds check failed - outer.right ({outer.bounding_box[2]}) < inner.left ({inner.bounding_box[0]})"
            )
        return False
    if outer.bounding_box[3] < inner.bounding_box[1] - tolerance:
        # outer maxy < inner maxy (is not contained)
        if debug:
            print(
                f"DEBUG is_inside: Fast bounds check failed - outer.bottom ({outer.bounding_box[3]}) < inner.top ({inner.bounding_box[1]})"
            )
        return False

    # Special case for degenerate shapes (lines with zero height/width)
    inner_width = inner.bounding_box[2] - inner.bounding_box[0]
    inner_height = inner.bounding_box[3] - inner.bounding_box[1]

    if inner_width == 0 or inner_height == 0:
        # This is a degenerate shape (line), use simple point-in-bounds test
        if debug:
            print(
                f"DEBUG is_inside: Degenerate shape detected (w={inner_width}, h={inner_height})"
            )

        # For lines, check if both endpoints are within outer bounds
        inner_center_x = (inner.bounding_box[0] + inner.bounding_box[2]) / 2
        inner_center_y = (inner.bounding_box[1] + inner.bounding_box[3]) / 2

        is_contained = (
            outer.bounding_box[0] <= inner_center_x <= outer.bounding_box[2]
            and outer.bounding_box[1] <= inner_center_y <= outer.bounding_box[3]
        )

        if debug:
            print(f"DEBUG is_inside: Degenerate shape containment: {is_contained}")
            print(f"  Inner center: ({inner_center_x}, {inner_center_y})")
            print(f"  Outer bounds: {outer.bounding_box}")

        return is_contained

    if debug:
        print("DEBUG is_inside: Fast bounds check passed")
        print(f"  Outer bounds: {outer.bounding_box}")
        print(f"  Inner bounds: {inner.bounding_box}")
        print("  Trying geometric algorithms...")

    # ADVANCED GEOMETRIC ALGORITHMS - Multiple approaches for maximum performance

    def scanbeam_algorithm():
        """
        Scanbeam-based approach: Fastest algorithm for complex polygons.
        Uses advanced sweep-line algorithm for O(log n) point-in-polygon testing.
        """
        try:
            from .geomstr import Polygon as Gpoly
            from .geomstr import Scanbeam

            # Use existing ._geometry properties - no conversion needed!
            outer_geom = getattr(outer, "_geometry", None)
            inner_geom = getattr(inner, "_geometry", None)

            if outer_geom is None or inner_geom is None:
                return None  # Fall back if geometry not available

            # Build scanbeam from outer geometry
            outer_points = list(outer_geom.as_equal_interpolated_points(distance=20))
            outer_polygon = Gpoly(*outer_points)
            scanbeam = Scanbeam(outer_polygon.geomstr)

            # Adaptive sampling: fewer points for simple shapes
            inner_bbox = getattr(inner, "bounding_box", None)
            if inner_bbox:
                bbox_perimeter = 2 * (
                    (inner_bbox[2] - inner_bbox[0]) + (inner_bbox[3] - inner_bbox[1])
                )
                sample_distance = max(15, min(50, bbox_perimeter / 100))
            else:
                sample_distance = 25

            # Sample points from inner geometry directly
            test_points = np.array(
                list(inner_geom.as_equal_interpolated_points(distance=sample_distance))
            )

            # Use scanbeam's optimized point-in-polygon test
            results = scanbeam.points_in_polygon(test_points)
            return np.all(results)

        except (ImportError, AttributeError, Exception) as e:
            if debug:
                print(f"  DEBUG: Scanbeam algorithm failed: {e}")
            return None  # Fall back to next algorithm

    def winding_number_algorithm():
        """
        Winding number approach: More robust than ray casting, especially for complex polygons.
        """
        try:

            def winding_number(point, polygon):
                """Calculate winding number for point with respect to polygon"""
                wn = 0
                n = len(polygon)

                for i in range(n):
                    p1 = polygon[i]
                    p2 = polygon[(i + 1) % n]

                    if p1[1] <= point[1]:
                        if p2[1] > point[1]:  # upward crossing
                            if is_left(p1, p2, point) > 0:  # point left of edge
                                wn += 1
                    else:
                        if p2[1] <= point[1]:  # downward crossing
                            if is_left(p1, p2, point) < 0:  # point right of edge
                                wn -= 1
                return wn != 0

            def is_left(p0, p1, p2):
                """Test if point p2 is left|on|right of line p0p1"""
                return (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (
                    p1[1] - p0[1]
                )

            # Use existing ._geometry properties - no conversion needed!
            inner_geom = getattr(inner, "_geometry", None)
            outer_geom = getattr(outer, "_geometry", None)

            if inner_geom is None or outer_geom is None:
                return None  # Fall back if geometry not available

            # Optimized sampling based on polygon complexity
            inner_bbox = getattr(inner, "bounding_box", None)
            if inner_bbox:
                bbox_area = (inner_bbox[2] - inner_bbox[0]) * (
                    inner_bbox[3] - inner_bbox[1]
                )
                sample_distance = max(20, min(40, bbox_area / 5000))
            else:
                sample_distance = 25

            # Sample points directly from geometry
            points = [
                (p.real, p.imag)
                for p in inner_geom.as_equal_interpolated_points(
                    distance=sample_distance
                )
            ]
            vertices = [
                (p.real, p.imag)
                for p in outer_geom.as_equal_interpolated_points(
                    distance=sample_distance
                )
            ]

            # Early exit: return False as soon as any point is found outside
            for point in points:
                if not winding_number(point, vertices):
                    return False
            return True

        except Exception as e:
            if debug:
                print(f"  DEBUG: Winding number algorithm failed: {e}")
            return None  # Fall back to next algorithm

    def optimized_ray_tracing():
        """
        Improved ray tracing: Our previously optimized algorithm as fallback.
        """
        try:

            def sq_length(a, b):
                return a * a + b * b

            def ray_tracing(x, y, poly, tolerance):
                tolerance_square = tolerance * tolerance
                n = len(poly)
                inside = False

                p1x, p1y = poly[0]
                old_sq_dist = sq_length(p1x - x, p1y - y)
                for i in range(n + 1):
                    p2x, p2y = poly[i % n]
                    new_sq_dist = sq_length(p2x - x, p2y - y)
                    reldist = (
                        old_sq_dist
                        + new_sq_dist
                        + 2.0 * np.sqrt(old_sq_dist * new_sq_dist)
                        - sq_length(p2x - p1x, p2y - p1y)
                    )
                    if reldist < tolerance_square:
                        return True

                    # Optimized condition merging
                    if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
                        if p1y != p2y:
                            xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xints:
                            inside = not inside
                    p1x, p1y = p2x, p2y
                    old_sq_dist = new_sq_dist
                return inside

            # Use existing ._geometry properties - no conversion needed!
            inner_geom = getattr(inner, "_geometry", None)
            outer_geom = getattr(outer, "_geometry", None)

            if inner_geom is None or outer_geom is None:
                # Fallback to path conversion if geometry not available
                inner_geom = Geomstr.svg(inner_path.d())
                outer_geom = Geomstr.svg(outer_path.d())

            # Adaptive sampling based on polygon size
            inner_bbox = getattr(inner, "bounding_box", None)
            if inner_bbox:
                bbox_area = (inner_bbox[2] - inner_bbox[0]) * (
                    inner_bbox[3] - inner_bbox[1]
                )
                adaptive_distance = max(12, min(25, bbox_area / 10000))
            else:
                adaptive_distance = 15

            # Sample points directly from geometry
            points = [
                (p.real, p.imag)
                for p in inner_geom.as_equal_interpolated_points(
                    distance=adaptive_distance
                )
            ]
            vertices = [
                (p.real, p.imag)
                for p in outer_geom.as_equal_interpolated_points(
                    distance=adaptive_distance
                )
            ]

            # Early exit optimization: return False as soon as any point is found outside
            for x, y in points:
                if not ray_tracing(x, y, vertices, tolerance):
                    return False
            return True

        except Exception as e:
            if debug:
                print(f"  DEBUG: Ray tracing algorithm failed: {e}")
            return False  # Ultimate fallback

    # Try algorithms in order of expected performance: Scanbeam -> Winding Number -> Ray Tracing
    if debug:
        print("  Trying scanbeam algorithm...")
    result = scanbeam_algorithm()
    if result is not None:
        if debug:
            print(f"  Scanbeam result: {result}")
        return result

    if debug:
        print("  Trying winding number algorithm...")
    result = winding_number_algorithm()
    if result is not None:
        if debug:
            print(f"  Winding number result: {result}")
        return result

    if debug:
        print("  Trying ray tracing algorithm...")
    result = optimized_ray_tracing()
    if debug:
        print(f"  Ray tracing result: {result}")
    return result


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
        # min_res = min(
        #     kernel.device.view.native_scale_x, kernel.device.view.native_scale_y
        # )
        # a 0.5 mm resolution is enough
        # resolution = int(0.5 * UNITS_PER_MM / min_res)
        # print(f"Chosen resolution: {resolution} - minscale = {min_res}")
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

            if is_inside(inner, outer, tolerance, debug=False):
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

    if channel:
        end_times = times()
        channel(
            f"Inner paths identified in {time() - start_time:.3f} elapsed seconds: {constrained} "
            f"using {end_times[0] - start_times[0]:.3f} seconds CPU"
        )
        for outer in closed_groups:
            if outer is None:
                continue
            channel(
                f"Outer {type(outer).__name__} contains: {'None' if outer.contains is None else str(len(outer.contains))} cutcode elements"
            )
    return context


def short_travel_cutcode(
    context: CutCode,
    kernel=None,
    channel=None,
    complete_path: Optional[bool] = False,
    grouped_inner: Optional[bool] = False,
    hatch_optimize: Optional[bool] = False,
):
    return short_travel_cutcode_optimized(
        context=context,
        kernel=kernel,
        channel=channel,
        complete_path=complete_path,
        grouped_inner=grouped_inner,
        hatch_optimize=hatch_optimize,
    )


def _sequence_skip_groups(unordered, hatch_optimize, kernel=None, channel=None):
    """
    Helper function to sequence skip-marked groups (hatches) separately from main optimization.
    
    When hatch_optimize=True: applies travel optimization to skip groups.
    When hatch_optimize=False: applies basic cutcode sequencing without travel optimization.
    
    Args:
        unordered: List of skip-marked CutGroups to sequence
        hatch_optimize: Whether to apply travel optimization to skip groups
        kernel: Optional kernel for progress reporting
        channel: Optional logging channel
    
    Returns:
        Tuple of (ordered_skip_cutcode, unordered_list) where ordered_skip contains
        all sequenced cuts from skip groups, and unordered_list is reset for final assembly.
    """
    ordered_skip = CutCode()
    
    if hatch_optimize:
        # When hatch_optimize=True, apply travel optimization to skip groups
        for idx, c in enumerate(unordered):
            if isinstance(c, CutGroup):
                c.skip = False
                unordered[idx] = short_travel_cutcode(
                    context=c,
                    kernel=kernel,
                    complete_path=False,
                    grouped_inner=False,
                    channel=channel,
                )
    else:
        # When hatch_optimize=False, apply basic cutcode sequencing without travel optimization
        for c in unordered:
            if isinstance(c, CutGroup):
                c.skip = False
                # Initialize burns_done for all cuts in this group
                for cut in c.flat():
                    cut.burns_done = 0
                
                # Apply basic cutcode sequencing
                ordered_group = CutCode()
                while True:
                    candidates = list(c.candidate(grouped_inner=False))
                    if not candidates:
                        break
                    for cut in candidates:
                        cut.burns_done += 1
                    ordered_group.extend(copy(candidates))
                
                # Set start position if available
                if c.start is not None:
                    ordered_group._start_x, ordered_group._start_y = c.start
                else:
                    ordered_group._start_x = 0
                    ordered_group._start_y = 0
                
                ordered_skip.extend(ordered_group)
    
    return ordered_skip, unordered


def short_travel_cutcode_legacy(
    context: CutCode,
    kernel=None,
    channel=None,
    complete_path: Optional[bool] = False,
    grouped_inner: Optional[bool] = False,
    hatch_optimize: Optional[bool] = False,
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
    
    # CRITICAL FIX FOR HATCHED GEOMETRIES:
    # When hatch_optimize=True, extract skip groups for separate travel optimization.
    # When hatch_optimize=False, extract skip groups for unoptimized processing.
    # In both cases, skip groups (marked during combine_effects) must be handled separately.
    unordered = []
    skip_groups = []
    non_skip_groups = []
    
    # Separate skip and non-skip groups
    for c in context:
        if isinstance(c, CutGroup) and c.skip:
            skip_groups.append(c)
        else:
            non_skip_groups.append(c)
    
    # Extract skip groups when:
    # 1. hatch_optimize=True: always (for travel optimization), OR
    # 2. hatch_optimize=False: always (to avoid any optimization via greedy loop)
    # This ensures skip-marked groups are never mixed with optimization logic
    if skip_groups:
        if channel:
            channel(f"Found {len(skip_groups)} skip groups, {len(non_skip_groups)} non-skip groups, hatch_optimize={hatch_optimize}")
        if non_skip_groups:
            # CRITICAL: Before removing skip groups, filter containment hierarchy
            # to prevent outer groups from referencing removed inner groups.
            # This is important for algorithms that respect inner-first constraints.
            for group in non_skip_groups:
                if hasattr(group, "contains") and group.contains:
                    # Filter .contains to only include groups that remain in context
                    group.contains = [
                        inner for inner in group.contains
                        if not (isinstance(inner, CutGroup) and inner.skip)
                    ]
            
            context.clear()
            context.extend(non_skip_groups)
            unordered = skip_groups
        else:
            # ALL items are skip-marked: move them to unordered for non-optimized processing
            if channel:
                channel("All groups are skip-marked, moving to unordered for basic processing")
            unordered = skip_groups
            context.clear()
    # else: No skip groups, keep context as-is

    curr = context.start
    curr = 0 if curr is None else complex(curr[0], curr[1])

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
    # print (f"Cutcode-Len={cutcode_len}, unordered: {len(unordered)}")
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
                distance > 5  # Fixed: 1/20" = ~5 pixels, not 50
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
        # Fixed: Original 1/20" = ~5 pixels, not 50. This restores 0.98b3 performance.
        if distance > 5:
            for cut in context.candidate(
                complete_path=complete_path, grouped_inner=grouped_inner
            ):
                s = cut.start
                if (
                    abs(s[0] - curr.real) <= distance
                    and abs(s[1] - curr.imag) <= distance
                    and (not complete_path or cut.closed or cut.first or cut.original_op in ("op cut", "op engrave"))
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
                    and (not complete_path or cut.closed or cut.last or cut.original_op in ("op cut", "op engrave"))
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
    # print (f"Now we have {len(ordered)} items in list")
    if unordered:
        # Sequence skip groups using helper function
        ordered_skip_groups, unordered = _sequence_skip_groups(
            unordered, hatch_optimize, kernel=kernel, channel=channel
        )
        # As these are reversed, we reverse again...
        ordered.extend(reversed(unordered))
        ordered.extend(ordered_skip_groups)
    # print (f"And after extension {len(ordered)} items in list")
    # for c in ordered:
    #     print (f"{type(c).__name__} - {len(c) if isinstance(c, (list, tuple)) else '-childless-'}")
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


def short_travel_cutcode_optimized(
    context: CutCode,
    kernel=None,
    channel=None,
    complete_path: Optional[bool] = False,
    grouped_inner: Optional[bool] = False,
    hatch_optimize: Optional[bool] = False,
):
    """
    Optimized short-travel cutcode algorithm with adaptive strategy selection.

    Chooses the best optimization strategy based on dataset characteristics:
    - Group-aware: When grouped_inner=True, processes related inner/outer groups together
    - Group-preserving: When inner-first constraints exist, processes groups individually
    - Standard algorithms: For unconstrained optimization, uses size-appropriate algorithms

    Args:
        context: CutCode containing cuts and groups to optimize
        kernel: Optional kernel for progress reporting
        channel: Optional logging channel
        complete_path: Whether to require complete path traversal
        grouped_inner: Whether to group inner/outer relationships together
        hatch_optimize: Whether to optimize hatch patterns

    Returns:
        CutCode with optimized travel order
    """
    # Check for group-aware optimization first
    if grouped_inner:
        if channel:
            channel("Using group-aware optimization for containment hierarchy")
        # Use group-aware optimization to preserve hierarchy
        return _group_aware_selection(
            context=context,
            all_candidates=context,
            complete_path=complete_path,
            channel=channel,
        )

    if channel:
        start_length = context.length_travel(True)
        start_time = time()
        start_times = times()
        channel("Executing adaptive short-travel optimization")
        channel(f"Length at start: {start_length:.0f} steps")

    # CRITICAL FIX FOR HATCHED GEOMETRIES:
    # When hatch_optimize=True, skip groups represent hatch patterns that should be
    # processed separately from regular shapes. Extract them for separate handling.
    # When hatch_optimize=False, skip groups should be included in regular optimization.
    #
    # The key insight: if ALL items are skip-marked, we still need to optimize them.
    # Don't remove them if it would leave an empty context for optimization.
    
    unordered = []  # Will hold skip-marked groups for separate processing when hatch_optimize=True
    
    if hatch_optimize:
        # When optimizing hatch patterns separately:
        # 1. Extract skip groups for later processing
        # 2. Optimize remaining non-skip groups first
        # 3. If nothing remains, we have only hatch patterns - optimize them anyway
        
        skip_groups = []
        non_skip_groups = []
        
        for c in context:
            if isinstance(c, CutGroup) and c.skip:
                skip_groups.append(c)
            else:
                non_skip_groups.append(c)
        
        # Remove skip groups from context for first optimization pass
        # But only if there are non-skip groups to optimize
        if non_skip_groups:
            # We have regular shapes, so remove hatch patterns for this pass
            # CRITICAL: Before removing skip groups, filter containment hierarchy
            # to prevent outer groups from referencing removed inner groups.
            # This is important for _group_preserving_selection which expects
            # all referenced groups to be in the context.
            # 
            # This filtering is REQUIRED and intentional: we're removing skip groups
            # from context and their references MUST be updated to maintain consistency.
            # Not doing this would leave broken references that cause incorrect behavior
            # in hierarchy-aware optimization algorithms.
            for group in non_skip_groups:
                if hasattr(group, "contains") and group.contains:
                    # Filter .contains to only include groups that remain in context
                    group.contains = [
                        inner for inner in group.contains
                        if not (isinstance(inner, CutGroup) and inner.skip)
                    ]
            
            context.clear()
            context.extend(non_skip_groups)
            unordered = skip_groups
        else:
            # All items are skip-marked (hatches only), keep them for optimization
            # They'll be optimized as regular cuts
            unordered = []
    else:
        # When hatch_optimize=False, include skip groups in regular optimization
        # Don't remove them
        unordered = []

    # Initialize burns_done for all cuts BEFORE getting candidates
    for c in context.flat():
        c.burns_done = 0

    # Get all candidates first to determine dataset size
    all_candidates = list(
        context.candidate(complete_path=complete_path, grouped_inner=grouped_inner)
    )

    dataset_size = len(all_candidates)

    if channel:
        channel(f"Dataset size: {dataset_size} cuts")

    if not all_candidates:
        # No candidates from regular shapes
        if unordered and hatch_optimize:
            # We have skip-marked hatch patterns to process
            ordered = CutCode()
            for idx, c in enumerate(unordered):
                if isinstance(c, CutGroup):
                    unordered[idx] = short_travel_cutcode_optimized(
                        context=c,
                        kernel=kernel,
                        complete_path=False,
                        grouped_inner=False,
                        channel=channel,
                        hatch_optimize=False,  # Don't recursively apply hatch_optimize
                    )
            
            ordered.extend(unordered)
            if context.start is not None:
                ordered._start_x, ordered._start_y = context.start
            else:
                ordered._start_x = 0
                ordered._start_y = 0
            return ordered
        
        # No candidates at all, return empty CutCode
        ordered = CutCode()
        if context.start is not None:
            ordered._start_x, ordered._start_y = context.start
        else:
            ordered._start_x = 0
            ordered._start_y = 0
        return ordered

    # Check optimization strategy based on constraints and dataset
    if grouped_inner:
        # Use group-aware optimization that respects containment relationships
        if channel:
            channel("Using group-aware optimization for inner-first hierarchy")
        return _group_aware_selection(context, all_candidates, complete_path, channel)
    
    # Check if we have inner-first hierarchy that should be preserved
    has_containment_hierarchy = any(
        hasattr(group, "contains") and group.contains
        for group in context
        if hasattr(group, "contains")
    )

    if has_containment_hierarchy:
        # Use group-preserving optimization that respects inner-first without grouping pieces
        if channel:
            channel("Using group-preserving optimization for inner-first hierarchy")
        return _group_preserving_selection(context, complete_path, channel)
    
    # Use standard travel optimization on individual cuts
    start_pos = context.start or (0, 0)
    
    if dataset_size < 50:
        # Very small dataset: Use simple greedy algorithm
        if channel:
            channel("Using simple greedy algorithm for small dataset")
        ordered_cuts = _simple_greedy_selection(all_candidates, start_pos)

    elif dataset_size < 100:
        # Small-medium dataset: Use improved greedy with active set optimization
        if channel:
            channel("Using improved greedy algorithm for medium dataset")
        ordered_cuts = _improved_greedy_selection(all_candidates, start_pos)

    elif dataset_size <= 500:
        # Medium-large dataset: Use spatial-indexed algorithm
        if channel:
            channel("Using spatial-indexed algorithm for large dataset")
        ordered_cuts = _spatial_optimized_selection(all_candidates, start_pos)

    else:
        # Very large dataset: Use legacy algorithm
        if channel:
            channel("Using legacy algorithm for very large dataset")
        return short_travel_cutcode_legacy(
            context=context,
            kernel=kernel,
            channel=channel,
            complete_path=complete_path,
            grouped_inner=grouped_inner,
            hatch_optimize=hatch_optimize,
        )

    # Create ordered CutCode from selected cuts
    ordered = CutCode()
    ordered.extend(ordered_cuts)

    # Handle unordered groups (same as original)
    if hatch_optimize:
        for idx, c in enumerate(unordered):
            if isinstance(c, CutGroup):
                c.skip = False
                unordered[idx] = short_travel_cutcode_optimized(
                    context=c,
                    kernel=kernel,
                    complete_path=False,
                    grouped_inner=False,
                    channel=channel,
                )

    ordered.extend(reversed(unordered))

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


def process_piece_with_inner_first(
    piece_groups, start_position, complete_path, channel
):
    """
    Process a piece (collection of related groups) with inner-first constraints within the piece.

    Args:
        piece_groups: List of CutGroups that belong to this piece
        start_position: Starting (x, y) position
        complete_path: Path completion requirement
        channel: Optional logging channel

    Returns:
        List of cuts in optimized order maintaining inner-first within piece
    """
    if not piece_groups:
        return []

    # Separate groups within this piece into inner and outer
    inner_groups = [g for g in piece_groups if hasattr(g, "inside") and g.inside]
    outer_groups = [g for g in piece_groups if hasattr(g, "contains") and g.contains]
    other_groups = [
        g for g in piece_groups if g not in inner_groups and g not in outer_groups
    ]

    piece_cuts = []
    curr_x, curr_y = start_position

    if channel and (inner_groups or outer_groups):
        channel(
            f"  Piece has {len(inner_groups)} inner, {len(outer_groups)} outer, {len(other_groups)} other groups"
        )

    # Phase 1: Process inner groups within this piece first
    if inner_groups:
        inner_cuts = []
        for group in inner_groups:
            for cut in group.candidate(complete_path=complete_path, grouped_inner=True):
                if cut.burns_done < cut.passes:
                    inner_cuts.append(cut)

        if inner_cuts:
            # Travel optimize within inner cuts of this piece
            inner_optimized = _simple_greedy_selection(inner_cuts, (curr_x, curr_y))
            piece_cuts.extend(inner_optimized)
            if inner_optimized:
                curr_x, curr_y = inner_optimized[-1].end

    # Phase 2: Process outer groups within this piece
    if outer_groups:
        outer_cuts = []
        for group in outer_groups:
            for cut in group.candidate(complete_path=complete_path, grouped_inner=True):
                if cut.burns_done < cut.passes:
                    outer_cuts.append(cut)

        if outer_cuts:
            # Travel optimize within outer cuts of this piece
            outer_optimized = _simple_greedy_selection(outer_cuts, (curr_x, curr_y))
            piece_cuts.extend(outer_optimized)
            if outer_optimized:
                curr_x, curr_y = outer_optimized[-1].end

    # Phase 3: Process other groups within this piece
    if other_groups:
        other_cuts = []
        for group in other_groups:
            for cut in group.candidate(complete_path=complete_path, grouped_inner=True):
                if cut.burns_done < cut.passes:
                    other_cuts.append(cut)

        if other_cuts:
            # Travel optimize within other cuts of this piece
            other_optimized = _simple_greedy_selection(other_cuts, (curr_x, curr_y))
            piece_cuts.extend(other_optimized)

    return piece_cuts


def _group_aware_selection(context, all_candidates, complete_path, channel):
    """
    Group-aware travel optimization for opt_inners_grouped=True.

    Processes inner and outer groups together as cohesive pieces to ensure
    inner groups are burned before their containing outer groups, while
    optimizing travel distance within each piece.

    This creates pieces where all inner groups and their outer container
    are processed together, then applies travel optimization to all cuts
    within each piece.

    Args:
        context: CutCode containing CutGroups with containment relationships
        all_candidates: All candidate cuts (not used in this implementation)
        complete_path: Path completion requirement (not used in this implementation)
        channel: Optional logging channel

    Returns:
        CutCode with optimized individual cuts maintaining inner-first hierarchy
    """
    if channel:
        channel(f"Group-aware optimization: processing {len(context)} groups")

    # Work directly with CutGroups from context - these should be our candidate groups
    candidate_groups = list(context)

    # Check if we have proper CutGroups with containment relationships
    has_cutgroups = any(isinstance(group, CutGroup) for group in candidate_groups)
    has_containment = any(
        hasattr(group, "contains") and group.contains is not None
        for group in candidate_groups
        if isinstance(group, CutGroup)
    )

    if not has_cutgroups:
        if channel:
            channel(
                "No CutGroups found - this suggests inner_first_ident was not run properly"
            )
            channel("Falling back to simple greedy optimization")
        # Fall back to simple greedy optimization for individual cuts
        individual_cuts = []
        for item in candidate_groups:
            if hasattr(item, "flat"):
                individual_cuts.extend(item.flat())
            else:
                individual_cuts.append(item)

        start_pos = context.start or (0, 0)
        ordered_cuts = _simple_greedy_selection(individual_cuts, start_pos)

        ordered = CutCode()
        ordered.extend(ordered_cuts)
        if context.start is not None:
            ordered._start_x, ordered._start_y = context.start
        else:
            ordered._start_x = 0
            ordered._start_y = 0
        return ordered

    if not has_containment:
        if channel:
            channel("CutGroups found but no containment relationships detected")
            channel(
                "This may indicate closed path detection failed or no nested shapes"
            )

    # Initialize burns_done for all cuts within groups
    for group in candidate_groups:
        for cut in group.flat():
            cut.burns_done = 0

    # Create pieces: group related inner/outer groups together spatially
    pieces = []  # List of pieces, each piece contains related inner+outer groups
    processed_groups = set()

    # Strategy: For each outer group, create a piece containing it and all its inner groups
    outer_groups = [
        g for g in candidate_groups if hasattr(g, "contains") and g.contains
    ]

    for outer_group in outer_groups:
        if id(outer_group) in processed_groups:
            continue

        # Create a piece with this outer group and all its contained inner groups
        piece_groups = [outer_group]
        processed_groups.add(id(outer_group))

        if outer_group.contains:
            for inner_group in outer_group.contains:
                if id(inner_group) not in processed_groups:
                    piece_groups.append(inner_group)
                    processed_groups.add(id(inner_group))

        pieces.append(piece_groups)
        if channel:
            inner_count = len(
                [g for g in piece_groups if hasattr(g, "inside") and g.inside]
            )
            outer_count = len(
                [g for g in piece_groups if hasattr(g, "contains") and g.contains]
            )
            channel(f"Created piece: {inner_count} inner + {outer_count} outer groups")

    # Add remaining groups as individual pieces
    remaining_groups = [g for g in candidate_groups if id(g) not in processed_groups]
    for group in remaining_groups:
        pieces.append([group])
        if channel:
            channel(f"Created standalone piece: 1 group")

    if channel:
        channel(f"Total pieces created: {len(pieces)}")

    # Process pieces with travel optimization between pieces and inner-first within pieces
    ordered_cuts = []
    curr_x, curr_y = context.start or (0, 0)

    # Travel optimize between pieces: choose closest piece each time
    remaining_pieces = pieces[:]

    while remaining_pieces:
        # Find the closest piece based on first available cut
        best_piece = None
        best_distance = float("inf")
        best_piece_index = -1

        for piece_idx, piece in enumerate(remaining_pieces):
            # Get the first available cut from this piece to calculate distance
            first_cut = None
            for group in piece:
                for cut in group.candidate(
                    complete_path=complete_path, grouped_inner=True
                ):
                    if cut.burns_done < cut.passes:
                        first_cut = cut
                        break
                if first_cut:
                    break

            if first_cut:
                start_x, start_y = first_cut.start
                distance = ((start_x - curr_x) ** 2 + (start_y - curr_y) ** 2) ** 0.5

                if distance < best_distance:
                    best_distance = distance
                    best_piece = piece
                    best_piece_index = piece_idx

        if best_piece is None:
            break

        # Remove the selected piece from remaining pieces
        remaining_pieces.pop(best_piece_index)

        if channel:
            channel(
                f"Processing piece at distance {best_distance:.1f} with {len(best_piece)} groups"
            )

        # Process this piece with inner-first constraints within the piece
        piece_cuts = process_piece_with_inner_first(
            best_piece, (curr_x, curr_y), complete_path, channel
        )
        ordered_cuts.extend(piece_cuts)

        # Update position for next piece selection
        if piece_cuts:
            curr_x, curr_y = piece_cuts[-1].end

    # Create ordered CutCode from the optimized cuts (maintaining group structure)
    ordered = CutCode()
    ordered.extend(ordered_cuts)

    # Set start position
    if context.start is not None:
        ordered._start_x, ordered._start_y = context.start
    else:
        ordered._start_x = 0
        ordered._start_y = 0

    if channel:
        channel(
            f"Group-aware optimization: {len(pieces)} pieces, {len(ordered_cuts)} cuts optimized"
        )

    return ordered


def _group_preserving_selection(context, complete_path, channel):
    """
    Group-preserving travel optimization for opt_inners_grouped=False.

    Processes groups individually while respecting inner-first constraints.
    This mode processes groups one at a time in dependency order, optimizing
    travel within each group and choosing the closest available group to
    process next.

    Groups are only processed after all their inner dependencies have been
    completed, ensuring the inner-first constraint is maintained.

    Args:
        context: CutCode containing CutGroups with containment relationships
        complete_path: Path completion requirement (not used in this implementation)
        channel: Optional logging channel

    Returns:
        CutCode with optimized individual cuts maintaining inner-first hierarchy
    """
    if channel:
        channel(
            f"Group-preserving optimization: {len(context)} groups with inner-first constraints"
        )

    # Work directly with CutGroups from context
    candidate_groups = list(context)

    # Initialize burns_done for all cuts within groups
    for group in candidate_groups:
        for cut in group.flat():
            cut.burns_done = 0

    # Process groups individually while respecting inner-first constraints
    ordered_cuts = []
    processed_groups = set()
    curr_x, curr_y = context.start or (0, 0)

    # Keep processing until all groups are ordered
    while len(processed_groups) < len(candidate_groups):
        # Find groups that can be processed now (no unburned inner dependencies)
        ready_groups = []

        for group in candidate_groups:
            if id(group) in processed_groups:
                continue

            # Check if this group can be processed (all its inner groups are done)
            can_process = True
            if hasattr(group, "contains") and group.contains:
                for inner_group in group.contains:
                    if id(inner_group) not in processed_groups:
                        can_process = False
                        break

            if can_process:
                ready_groups.append(group)

        if not ready_groups:
            # Safety break - add remaining groups to avoid infinite loop
            for group in candidate_groups:
                if id(group) not in processed_groups:
                    ready_groups.append(group)
            if channel:
                channel(
                    f"Warning: Breaking inner-first loop, added {len(ready_groups)} remaining groups"
                )

        # Choose the closest ready group to minimize travel distance
        if len(ready_groups) == 1:
            # Only one choice
            group = ready_groups[0]
            best_start_distance = 0
        else:
            # Multiple ready groups - choose the one with best connection to current position
            best_group = None
            best_start_distance = float("inf")

            for candidate_group in ready_groups:
                if isinstance(candidate_group, CutGroup):
                    group_cuts = list(
                        candidate_group.candidate(
                            complete_path=complete_path, grouped_inner=False
                        )
                    )
                else:
                    group_cuts = (
                        [candidate_group]
                        if candidate_group.burns_done < candidate_group.passes
                        else []
                    )

                if not group_cuts:
                    continue

                # Find the best starting point in this group
                min_distance = float("inf")
                for cut in group_cuts:
                    # Check start point
                    start_dist = (
                        (cut.start[0] - curr_x) ** 2 + (cut.start[1] - curr_y) ** 2
                    ) ** 0.5
                    min_distance = min(min_distance, start_dist)

                    # Check end point if reversible
                    if hasattr(cut, "reversible") and cut.reversible():
                        end_dist = (
                            (cut.end[0] - curr_x) ** 2 + (cut.end[1] - curr_y) ** 2
                        ) ** 0.5
                        min_distance = min(min_distance, end_dist)

                if min_distance < best_start_distance:
                    best_start_distance = min_distance
                    best_group = candidate_group

            group = best_group or ready_groups[0]

        # Optimize travel within the selected group
        # Only include cuts that still need burns (don't reset burns_done)
        if isinstance(group, CutGroup):
            group_cuts = list(
                group.candidate(complete_path=complete_path, grouped_inner=False)
            )
        else:
            group_cuts = [group] if group.burns_done < group.passes else []

        # Apply travel optimization to this group's cuts
        group_ordered = _simple_greedy_selection(group_cuts, (curr_x, curr_y))
        ordered_cuts.extend(group_ordered)

        processed_groups.add(id(group))

        # Update current position for next group
        if group_ordered:
            last_cut = group_ordered[-1]
            curr_x, curr_y = last_cut.end

    # Create ordered CutCode from the optimized individual cuts
    ordered = CutCode()
    ordered.extend(ordered_cuts)

    # Set start position
    if context.start is not None:
        ordered._start_x, ordered._start_y = context.start
    else:
        ordered._start_x = 0
        ordered._start_y = 0

    if channel:
        channel(
            f"Group-preserving optimization: {len(candidate_groups)} groups, {len(ordered_cuts)} cuts optimized"
        )

    return ordered


def _simple_greedy_selection(
    all_candidates, start_position, early_termination_threshold=25
):
    """
    Simple greedy nearest-neighbor algorithm for travel optimization.

    Iteratively selects the closest unfinished cut to the current position,
    choosing the optimal direction (forward or reverse) for each cut.

    Args:
        all_candidates: List of cuts to optimize
        start_position: Starting (x, y) position tuple
        early_termination_threshold: Distance threshold for early termination (default: 25)

    Returns:
        List of cuts in optimized order
    """
    if not all_candidates:
        return []

    # Burns_done already initialized in the calling function
    ordered = []
    curr_x, curr_y = start_position

    while True:
        closest = None
        backwards = False
        best_distance_sq = float("inf")

        # Find the nearest unfinished cut
        # early_termination_threshold now configurable parameter

        for cut in all_candidates:
            if cut.burns_done >= cut.passes:
                continue

            # Check forward direction
            start_x, start_y = cut.start
            dx = start_x - curr_x
            dy = start_y - curr_y
            distance_sq = dx * dx + dy * dy

            # Deterministic tie-breaking: prefer cuts with smaller Y, then smaller X coordinates
            is_better = distance_sq < best_distance_sq or (
                distance_sq == best_distance_sq
                and closest is not None
                and (
                    start_y < closest.start[1]
                    or (start_y == closest.start[1] and start_x < closest.start[0])
                )
            )

            if is_better:
                closest = cut
                backwards = False
                best_distance_sq = distance_sq

                # Early termination for very close cuts
                if distance_sq <= early_termination_threshold:
                    break

            # Check reverse direction if cut is reversible
            if cut.reversible():
                end_x, end_y = cut.end
                dx = end_x - curr_x
                dy = end_y - curr_y
                distance_sq = dx * dx + dy * dy

                # Deterministic tie-breaking for reverse direction
                is_better = distance_sq < best_distance_sq or (
                    distance_sq == best_distance_sq
                    and closest is not None
                    and (
                        end_y
                        < (
                            closest.end[1]
                            if backwards and closest.reversible()
                            else closest.start[1]
                        )
                        or (
                            end_y
                            == (
                                closest.end[1]
                                if backwards and closest.reversible()
                                else closest.start[1]
                            )
                            and end_x
                            < (
                                closest.end[0]
                                if backwards and closest.reversible()
                                else closest.start[0]
                            )
                        )
                    )
                )

                if is_better:
                    closest = cut
                    backwards = True
                    best_distance_sq = distance_sq

                    # Early termination for very close cuts
                    if distance_sq <= early_termination_threshold:
                        break

        if closest is None:
            break

        closest.burns_done += 1
        c = copy(closest)
        if backwards:
            c.reverse()
        end = c.end
        curr_x, curr_y = end
        ordered.append(c)

    return ordered


def _improved_greedy_selection(all_candidates, start_position):
    """
    Improved greedy nearest-neighbor algorithm for medium-sized datasets.

    Uses Active Set Optimization to maintain only unfinished cuts in the search space,
    reducing the algorithm complexity as cuts are completed.

    Args:
        all_candidates: List of cuts to optimize
        start_position: Starting (x, y) position tuple

    Returns:
        List of cuts in optimized order
    """
    if not all_candidates:
        return []

    # Burns_done already initialized in the calling function
    # Active Set Optimization: maintain list of only unfinished cuts
    active_cuts = list(all_candidates)

    ordered = []
    curr_x, curr_y = start_position

    while active_cuts:
        closest = None
        backwards = False
        best_distance_sq = float("inf")
        closest_index = -1

        # Find the nearest unfinished cut with early termination and deterministic tie-breaking
        # Use same threshold as simple greedy for consistent performance
        early_termination_threshold = 25  # 5^2, very close cut

        for i, cut in enumerate(active_cuts):
            # Check forward direction
            start_x, start_y = cut.start
            dx = start_x - curr_x
            dy = start_y - curr_y
            distance_sq = dx * dx + dy * dy

            # Deterministic tie-breaking: same logic as simple greedy
            is_better = distance_sq < best_distance_sq or (
                distance_sq == best_distance_sq
                and closest is not None
                and (
                    start_y < closest.start[1]
                    or (start_y == closest.start[1] and start_x < closest.start[0])
                )
            )

            if is_better:
                closest = cut
                backwards = False
                best_distance_sq = distance_sq
                closest_index = i

                # Early termination for very close cuts
                if distance_sq <= early_termination_threshold:
                    break

            # Check reverse direction if cut is reversible
            if cut.reversible():
                end_x, end_y = cut.end
                dx = end_x - curr_x
                dy = end_y - curr_y
                distance_sq = dx * dx + dy * dy

                # Deterministic tie-breaking for reverse direction: same logic as simple greedy
                is_better = distance_sq < best_distance_sq or (
                    distance_sq == best_distance_sq
                    and closest is not None
                    and (
                        end_y
                        < (
                            closest.end[1]
                            if backwards and closest.reversible()
                            else closest.start[1]
                        )
                        or (
                            end_y
                            == (
                                closest.end[1]
                                if backwards and closest.reversible()
                                else closest.start[1]
                            )
                            and end_x
                            < (
                                closest.end[0]
                                if backwards and closest.reversible()
                                else closest.start[0]
                            )
                        )
                    )
                )

                if is_better:
                    closest = cut
                    backwards = True
                    best_distance_sq = distance_sq
                    closest_index = i

                    # Early termination for very close cuts
                    if distance_sq <= early_termination_threshold:
                        break

        if closest is None:
            break

        closest.burns_done += 1

        # Active Set Optimization: Remove cut from active list if fully burned
        if closest.burns_done >= closest.passes:
            if closest_index >= 0 and closest_index < len(active_cuts):
                active_cuts.pop(closest_index)
            else:
                # Fallback: search and remove (should be rare)
                try:
                    active_cuts.remove(closest)
                except ValueError:
                    pass  # Cut already removed

        c = copy(closest)
        if backwards:
            c.reverse()
        end = c.end
        curr_x, curr_y = end
        ordered.append(c)

    return ordered


def _spatial_optimized_selection(all_candidates, start_position):
    """
    Spatial-indexed greedy algorithm for large datasets.

    Uses scipy.spatial.cKDTree for O(log n) nearest neighbor search
    instead of O(n) linear search. Provides significant speedup for medium-large datasets.
    Falls back to improved greedy if scipy is not available.

    Args:
        all_candidates: List of cuts to optimize
        start_position: Starting (x, y) position tuple

    Returns:
        List of cuts in optimized order
    """
    try:
        from scipy.spatial import cKDTree  # Optional dependency
    except ImportError:
        # Fall back to improved greedy if scipy not available
        # import logging
        # logging.getLogger(__name__).warning("scipy.spatial not available, falling back to improved greedy algorithm")
        return _improved_greedy_selection(all_candidates, start_position)

    if not all_candidates:
        return []

    # Initialize all cuts
    # Burns_done already initialized in the calling function

    # Build spatial index for fast nearest neighbor queries
    def rebuild_spatial_index(active_cuts):
        if not active_cuts:
            return None, [], []

        positions = []
        cut_mapping = []  # Maps position index to (cut, is_reversed)

        for cut in active_cuts:
            positions.append(cut.start)
            cut_mapping.append((cut, False))
            if cut.reversible():
                positions.append(cut.end)
                cut_mapping.append((cut, True))

        if not positions:
            return None, [], []

        tree = cKDTree(positions)
        return tree, positions, cut_mapping

    active_cuts = list(all_candidates)
    ordered = []
    curr_x, curr_y = start_position

    # Rebuild index every N iterations to balance performance vs accuracy
    rebuild_frequency = max(10, len(active_cuts) // 20)
    iteration_count = 0

    tree, positions, cut_mapping = rebuild_spatial_index(active_cuts)

    while active_cuts:
        closest = None
        backwards = False
        best_distance_sq = float("inf")
        closest_index = -1

        # Try path continuation first (maintains path coherence)
        if ordered:
            last_cut = ordered[-1]
            if (
                hasattr(last_cut, "next")
                and last_cut.next
                and last_cut.next in active_cuts
            ):
                next_cut = last_cut.next
                start_x, start_y = next_cut.start
                distance_sq = (start_x - curr_x) ** 2 + (start_y - curr_y) ** 2
                if distance_sq < 2500:  # Good continuation threshold
                    closest = next_cut
                    backwards = False
                    best_distance_sq = distance_sq
                    try:
                        closest_index = active_cuts.index(closest)
                    except ValueError:
                        closest_index = -1

        # If no good continuation, use spatial index for fast search
        if best_distance_sq > 25 and tree is not None:  # Fixed: 5² = 25, not 50² = 2500
            try:
                # Query k nearest neighbors (k=5 to handle edge cases)
                distances, indices = tree.query(
                    [curr_x, curr_y], k=min(5, len(positions))
                )

                if not hasattr(distances, "__len__"):
                    distances = [distances]
                    indices = [indices]

                for dist, idx in zip(distances, indices):
                    if idx >= len(cut_mapping):
                        continue

                    cut, is_reversed = cut_mapping[idx]

                    # Verify cut is still active
                    if cut not in active_cuts:
                        continue

                    distance_sq = (
                        dist * dist
                    )  # scipy returns actual distance, we need squared

                    # Get current position for tie-breaking
                    current_pos = cut.end if is_reversed else cut.start
                    current_y, current_x = current_pos[1], current_pos[0]

                    if distance_sq < best_distance_sq or (
                        distance_sq == best_distance_sq
                        and (
                            current_y
                            < (
                                closest.end[1]
                                if closest and backwards
                                else closest.start[1]
                                if closest
                                else float("inf")
                            )
                            or (
                                current_y
                                == (
                                    closest.end[1]
                                    if closest and backwards
                                    else closest.start[1]
                                    if closest
                                    else float("inf")
                                )
                                and current_x
                                < (
                                    closest.end[0]
                                    if closest and backwards
                                    else closest.start[0]
                                    if closest
                                    else float("inf")
                                )
                            )
                        )
                    ):
                        closest = cut
                        backwards = is_reversed
                        best_distance_sq = distance_sq
                        try:
                            closest_index = active_cuts.index(closest)
                        except ValueError:
                            closest_index = -1
                        break

            except Exception:
                # Fall back to linear search if spatial query fails
                pass

        # Fall back to linear search if spatial index didn't find anything good
        if closest is None:
            early_termination_threshold = (
                400  # 20^2, reasonable threshold for spatial range
            )

            for i, cut in enumerate(active_cuts):
                # Check forward direction with optimized distance calculation
                start_x, start_y = cut.start
                dx = start_x - curr_x
                dy = start_y - curr_y
                distance_sq = dx * dx + dy * dy

                if distance_sq < best_distance_sq:
                    closest = cut
                    backwards = False
                    best_distance_sq = distance_sq
                    closest_index = i

                    # Early termination for reasonably close cuts
                    if distance_sq <= early_termination_threshold:
                        break

                # Check reverse direction if cut is reversible
                if cut.reversible():
                    end_x, end_y = cut.end
                    dx = end_x - curr_x
                    dy = end_y - curr_y
                    distance_sq = dx * dx + dy * dy

                    if distance_sq < best_distance_sq:
                        closest = cut
                        backwards = True
                        best_distance_sq = distance_sq
                        closest_index = i

                        # Early termination for reasonably close cuts
                        if distance_sq <= early_termination_threshold:
                            break

        if closest is None:
            break

        # Apply direction change logic (same as improved algorithm)
        if backwards:
            if (
                hasattr(closest, "next")
                and closest.next
                and closest.next.burns_done <= closest.burns_done
                and hasattr(closest.next, "start")
                and hasattr(closest, "end")
                and closest.next.start == closest.end
            ):
                closest = closest.next
                backwards = False
                try:
                    closest_index = active_cuts.index(closest)
                except ValueError:
                    closest_index = -1
        elif closest.reversible():
            if (
                hasattr(closest, "previous")
                and closest.previous
                and closest.previous is not closest
                and closest.previous.burns_done < closest.burns_done
                and hasattr(closest.previous, "end")
                and hasattr(closest, "start")
                and closest.previous.end == closest.start
            ):
                closest = closest.previous
                backwards = True
                try:
                    closest_index = active_cuts.index(closest)
                except ValueError:
                    closest_index = -1

        closest.burns_done += 1

        # Remove from active set if fully burned
        if closest.burns_done >= closest.passes:
            if closest_index >= 0 and closest_index < len(active_cuts):
                active_cuts.pop(closest_index)
            else:
                try:
                    active_cuts.remove(closest)
                except ValueError:
                    pass

            # Rebuild spatial index periodically for performance
            iteration_count += 1
            if iteration_count % rebuild_frequency == 0 and active_cuts:
                tree, positions, cut_mapping = rebuild_spatial_index(active_cuts)

        c = copy(closest)
        if backwards:
            c.reverse()
        end = c.end
        curr_x, curr_y = end
        ordered.append(c)

    return ordered
