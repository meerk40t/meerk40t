from copy import copy
from os import times
from typing import Any, Callable, Dict, Generator, Optional, Tuple, Union
from time import time

from ..core.cutcode import CutCode, CutGroup, CutObject, RasterCut
from ..kernel import Service
from ..svgelements import Group, Polygon, SVGElement, SVGImage, SVGText
from ..tools.pathtools import VectorMontonizer
from .elements import LaserOperation


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("planner", Planner(kernel))

    elif lifecycle == "boot":
        context = kernel.get_context("planner")  # specifically get this planner context
        _ = context._
        choices = [
            {
                "attr": "auto_spooler",
                "object": context,
                "default": True,
                "type": bool,
                "label": _("Launch Spooler on Job Start"),
                "tip": _(
                    "Open the Spooler window automatically when you Execute a Job"
                ),
            },
            {
                "attr": "prehome",
                "object": context,
                "default": False,
                "type": bool,
                "submenu": _("Before"),
                "label": _("Home"),
                "tip": _("Automatically add a home command before all jobs"),
            },
            {
                "attr": "prephysicalhome",
                "object": context,
                "default": False,
                "type": bool,
                "submenu": _("Before"),
                "label": _("Physical Home"),
                "tip": _("Automatically add a physical home command before all jobs"),
            },
            {
                "attr": "autohome",
                "object": context,
                "default": False,
                "type": bool,
                "submenu": _("After"),
                "label": _("Home"),
                "tip": _("Automatically add a home command after all jobs"),
            },
            {
                "attr": "autophysicalhome",
                "object": context,
                "default": False,
                "type": bool,
                "submenu": _("After"),
                "label": _("Physical Home"),
                "tip": _("Automatically add a physical home command before all jobs"),
            },
            {
                "attr": "autoorigin",
                "object": context,
                "default": False,
                "type": bool,
                "submenu": _("After"),
                "label": _("Return to Origin"),
                "tip": _("Automatically return to origin after a job"),
            },
            {
                "attr": "postunlock",
                "object": context,
                "default": False,
                "type": bool,
                "submenu": _("After"),
                "label": _("Unlock"),
                "tip": _("Automatically unlock the rail after all jobs"),
            },
            {
                "attr": "autobeep",
                "object": context,
                "default": False,
                "type": bool,
                "submenu": _("After"),
                "label": _("Beep"),
                "tip": _("Automatically add a beep after all jobs"),
            },
            {
                "attr": "autointerrupt",
                "object": context,
                "default": False,
                "type": bool,
                "submenu": _("After"),
                "label": _("Interrupt"),
                "tip": _("Automatically add an interrupt after all jobs"),
            },
        ]
        kernel.register_choices("planner", choices)

        choices = [
            {
                "attr": "opt_reduce_travel",
                "object": context,
                "default": True,
                "type": bool,
                "label": _("Reduce Travel Time"),
                "tip": _(
                    "Using this option can significantly reduce the time spent "
                    + "moving between elements with the laser off "
                    + "by optimizing the sequence that elements are burned. "
                )
                + "\n\n"
                + _(
                    "When this option is NOT checked, elements are burned strictly "
                    + "in the order they appear in the Operation tree, "
                    + "and the Merge options will have no effect on the burn time. "
                )
                + "\n\n"
                + _(
                    "When this option IS checked, Meerk40t will burn each subpath "
                    + "and then move to the nearest remaining subpath instead, "
                    + "reducing the time taken moving between burn items."
                ),
            },
            {
                "attr": "opt_complete_subpaths",
                "object": context,
                # Default is false for backwards compatibility.
                # Initial tests suggest that in most cases this actually results in shorter burn times.
                "default": True,
                "type": bool,
                "label": _("Burn Complete Subpaths"),
                "tip": _(
                    "By default Reduce Travel Time optimises using SVG individual path segments, "
                    + "which means that non-closed subpaths can be burned in several shorter separate burns "
                    + "rather than one continuous burn from start to end. "
                )
                + "\n\n"
                + _(
                    "This option only affects non-closed paths. "
                    + "When this option is checked, non-closed subpaths are always burned in one continuous burn "
                    + "from start to end rather than having burns start in the middle. "
                    + "Whilst this may create a longer travel move to the end of the subpath,"
                    + "it also avoids later travel moves to or from the intermediate point. "
                    + "The total travel time may therefore be shorter or longer. "
                    + "It may also avoid minor differences in total burn depth "
                    + "at the point the burns join. "
                )
            },
            {
                "attr": "opt_merge_passes",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Merge Passes"),
                "tip": _(
                    "Combine multiple passes into the same optimization. "
                    + "This will typically result in each subpath being burned multiple times in succession, "
                    + "burning closed paths round-and-round "
                    + "and non-closed paths back-and-forth, "
                    + "before Meerk40t moves to the next path. "
                )
                + "\n\n"
                + _(
                    "If you have a complex design with many paths and are burning with multiple passes, "
                    + "using this option can significantly REDUCE the optimisation time. "
                )
                + "\n\n"
                + _(
                    "NOTE: Where you burn very short paths multiple times in quick succession, "
                    + "this does not allow time for the material to cool down between burns, "
                    + "and this can result in greater charring "
                    + "or even an increased risk of the material catching fire."
                ),
            },
            {
                "attr": "opt_merge_ops",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Merge Operations"),
                "tip": _(
                    "Combine multiple consecutive burn operations and optimise across them globally. "
                    + "Operations of different types will be optimised together to reduce travel time, "
                    + "so vector and raster burns will be mixed. "
                )
                + "\n\n"
                + _(
                    "If Merge Passes is not checked, Operations with >1 passes will only have the same passes merged. "
                    + "If Merge Passes is also checked, then all burns will be optimised globally."
                )
                + "\n\n"
                + _(
                    "If you have a complex design with many paths across multiple consecutive burn operations, "
                    + "using this option can significantly INCREASE the optimisation time. "
                ),
            },
            {
                "attr": "opt_inner_first",
                "object": context,
                "default": True,
                "type": bool,
                "label": _("Burn Inner First"),
                "tip": _(
                    "Ensure that inside burns are done before an outside cut in order to ensure that burns inside "
                    + "a cut-out piece are done before the cut piece shifts or drops out of the material."
                )
                + "\n\n"
                + _(
                    "If you find that using this option significantly increases the optimisation time, "
                    + "alternatives are: \n"
                    + "* Deselecting Cut Inner First if you are not cutting fully through your material \n"
                    + "* Putting the inner paths into a separate earlier operation(s) and not using Merge Operations or Cut Inner First \n"
                    + "* If you are using multiple passes, check Merge Passes"
                ),
            },
            {
                "attr": "opt_inners_grouped",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Group Inner Burns"),
                "tip": _(
                    "Try to complete a set of inner burns and the associated outer cut before moving onto other elements."
                    + "This option only does something if Burn Inner First is also selected. "
                    + "If your design has multiple separate pieces on it, "
                    + "this should mostly cause each piece to be burned in entirety "
                    + "before moving on to burn another piece. "
                    + "This can reduce the risk of e.g. a shift ruining an entire piece of material "
                    + "by trying to ensure that one piece is finished before starting on another."
                )
                + "\n\n"
                + _(
                    "This optimization works best with Merge Operations also checked though this is not a requirement. "
                )
                + "\n\n"
                + _(
                    "Because this optimisation is done once rasters have been turned into images, "
                    + "inner elements may span multiple design pieces, "
                    + "in which case they may be optimised together."
                ),
            },
            {
                "attr": "opt_closed_distance",
                "object": context,
                "default": 15,
                "type": int,
                "label": _("Closed Distance"),
                "tip": _(
                    "How close in device specific natural units do endpoints need to be to count as closed?"
                ),
            },
        ]
        kernel.register_choices("optimize", choices)

        context.setting(bool, "opt_2opt", False)
        context.setting(bool, "opt_nearest_neighbor", True)
        context.setting(bool, "opt_reduce_directions", False)
        context.setting(bool, "opt_remove_overlap", False)
        context.setting(bool, "opt_start_from_position", False)

        # context.setting(int, "opt_closed_distance", 15)
        # context.setting(bool, "opt_merge_passes", False)
        # context.setting(bool, "opt_merge_ops", False)
        # context.setting(bool, "opt_inner_first", True)

    elif lifecycle == "poststart":
        if hasattr(kernel.args, "auto") and kernel.args.auto:
            elements = kernel.elements
            planner = kernel.planner
            # Auto start does the planning and spooling of the data.
            if hasattr(kernel.args, "speed") and kernel.args.speed is not None:
                for o in elements.ops():
                    o.speed = kernel.args.speed
            planner("plan copy preprocess validate blob preopt optimize\n")
            if hasattr(kernel.args, "origin") and kernel.args.origin:
                planner("plan append origin\n")
            if hasattr(kernel.args, "quit") and kernel.args.quit:
                planner("plan append shutdown\n")
            planner("plan spool\n")
        else:
            if hasattr(kernel.args, "quit") and kernel.args.quit:
                # Flag quitting on complete.
                kernel.root._quit = True


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

    def __str__(self):
        parts = list()
        parts.append(self.name)
        if len(self.plan):
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
        context = self.context

        grouped_plan = list()
        group = [self.plan[0]]
        for c in self.plan[1:]:
            if (
                type(group[-1]) == LaserOperation or type(c) == LaserOperation
            ) and type(group[-1]) != type(c):
                grouped_plan.append(group)
                group = []
            group.append(c)
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
                    if not isinstance(op, LaserOperation):
                        blob_plan.append(op)
                        continue
                    if op.operation == "Dots":
                        if pass_idx == 1:
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

        self.plan.clear()
        for blob in blob_plan:
            try:
                blob.settings.jog_distance = context.opt_jog_minimum
                blob.settings.jog_enable = context.opt_rapid_between
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
                self.plan[i] = short_travel_cutcode_2opt(
                    self.plan[i], channel=channel
                )

    def optimize_cuts(self):
        channel = self.context.channel("optimize", timestamp=True)
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                if c.constrained:
                    self.plan[i] = inner_first_ident(
                        c, channel=channel
                    )
                    c = self.plan[i]
                self.plan[i] = inner_selection_cutcode(
                    c,
                    channel=channel,
                    grouped_inner=self.context.opt_inners_grouped,
                )

    def optimize_travel(self):
        last = None
        channel = self.context.channel("optimize", timestamp=True)
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                if c.constrained:
                    self.plan[i] = inner_first_ident(
                        c, channel=channel
                    )
                    c = self.plan[i]
                if last is not None:
                    self.plan[i].start = last
                self.plan[i] = short_travel_cutcode(
                    c,
                    channel=channel,
                    complete_path=self.context.opt_complete_subpaths,
                    grouped_inner=self.context.opt_inners_grouped,
                )
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
        for k, op in enumerate(self.plan):
            try:
                if op.operation == "Raster":
                    if len(op.children) == 1 and isinstance(op[0], SVGImage):
                        continue
                    self.plan[k] = None
                    stripped = True
            except AttributeError:
                pass
        if stripped:
            p = [q for q in self.plan if q is not None]
            self.plan.clear()
            self.plan.extend(p)

    def make_image_for_op(self, op):
        subitems = list(op.flat(types=("elem", "opnode")))
        reverse = self.context.elements.classify_reverse
        if reverse:
            subitems = list(reversed(subitems))
        make_raster = self.context.lookup("render-op/make_raster")
        objs = [s.object for s in subitems]
        bounds = Group.union_bbox(objs, with_stroke=True)
        if bounds is None:
            return None
        xmin, ymin, xmax, ymax = bounds
        step = op.settings.raster_step
        if step == 0:
            step = 1
        image = make_raster(subitems, bounds, step=step)
        image_element = SVGImage(image=image)
        image_element.transform.post_scale(step, step)
        image_element.transform.post_translate(xmin, ymin)
        image_element.values["raster_step"] = step
        return image_element

    def make_image(self):
        for op in self.plan:
            try:
                if op.operation == "Raster":
                    if len(op.children) == 1 and isinstance(op.children[0], SVGImage):
                        continue
                    image_element = self.make_image_for_op(op)
                    if image_element is None:
                        continue
                    if (
                        image_element.image_width == 1
                        and image_element.image_height == 1
                    ):
                        # TODO: Solve this is a less kludgy manner. The call to make the image can fail the first time
                        #  around because the renderer is what sets the size of the text. If the size hasn't already
                        #  been set, the initial bounds are wrong.
                        image_element = self.make_image_for_op(op)
                    op.children.clear()
                    op.add(image_element, type="opnode")
            except AttributeError:
                continue

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

    def scale_to_device_native(self):
        # rotary = self.context.rotary
        #
        # if rotary.rotary_enabled:
        #     axis = rotary.axis
        # TODO: Correct rotary.
        device = self.context.device
        scale_str = "scale(%.13f,%.13f)" % (
            device.get_native_scale_x,
            device.get_native_scale_y,
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
                    if len(op.children) == 1 and isinstance(op.children[0], SVGImage):
                        continue  # make raster not needed since its a single real raster.
                    make_raster = self.context.lookup("render-op/make_raster")

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

    def conditional_jobadd_scale(self):
        self.commands.append(self.scale_to_device_native)


class Planner(Service):
    """
    Planner is a service that adds 'plan' commands to the kernel. These are text based versions of the job preview and
    should be permitted to control the job creation process.
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "planner")
        self._plan = dict()
        self._default_plan = "0"

    def get_or_make_plan(self, plan_name):
        """
        Plans are a tuple of 3 lists and the name. Plan, Original, Commands, and Plan-Name
        """
        try:
            return self._plan[plan_name]
        except KeyError:
            self._plan[plan_name] = CutPlan(plan_name, self)
            return self._plan[plan_name]

    @property
    def default_plan(self):
        return self.get_or_make_plan(self._default_plan)

    def service_attach(self, *args, **kwargs):
        self.register("plan/physicalhome", physicalhome)
        self.register("plan/home", home)
        self.register("plan/origin", origin)
        self.register("plan/unlock", unlock)
        self.register("plan/wait", wait)
        self.register("plan/beep", beep)
        self.register("function/interrupt", interrupt_text)
        self.register("plan/interrupt", interrupt)

        def shutdown():
            yield "wait_finish"

            def shutdown_program():
                self("quit\n")

            yield "function", shutdown_program

        self.register("plan/shutdown", shutdown)

        _ = self.kernel.translation

        @self.console_argument("alias", type=str, help=_("plan command name to alias"))
        @self.console_command(
            "plan-alias",
            help=_("Define a spoolable console command"),
            input_type=None,
            output_type=None,
        )
        def plan_alias(command, channel, _, alias=None, remainder=None, **kwgs):
            """
            Plan alias allows the user to define a spoolable console command.
            eg. plan-alias export egv_export myfile.egv

            This creates a plan command called "export" that executes "egv_export myfile.egv".
            This can then be placed into the spooler during the planning stages.
            When the spooler reaches the command it will execute the console command.
            This would then run: "egv_export myfile.egv" which would save the current buffer.
            """
            if alias is None:
                raise SyntaxError
            plan_command = "plan/%s" % alias
            if self.lookup(plan_command) is not None:
                raise SyntaxError(_("You may not overwrite an already used alias."))

            def user_defined_alias():
                for s in remainder.split(";"):
                    self(s + "\n")

            user_defined_alias.__name__ = remainder
            self.register(plan_command, user_defined_alias)

        @self.console_command(
            "plan",
            help=_("plan<?> <command>"),
            regex=True,
            input_type=(None, "ops"),
            output_type="plan",
        )
        def plan_base(command, channel, _, data=None, remainder=None, **kwgs):
            if len(command) > 4:
                self._default_plan = command[4:]
                self.signal("plan", self._default_plan, None)

            cutplan = self.default_plan
            if data is not None:
                # If ops data is in data, then we copy that and move on to next step.
                for c in data:
                    if not c.output:
                        continue
                    try:
                        if len(c.children) == 0:
                            continue
                    except TypeError:
                        pass
                    copy_c = copy(c)
                    try:
                        copy_c.deep_copy_children(c)
                    except AttributeError:
                        pass
                    cutplan.plan.append(copy_c)
                self.signal("plan", self._default_plan, 1)
                return "plan", cutplan
            if remainder is None:
                channel(_("----------"))
                channel(_("Plan:"))
                for i, plan_name in enumerate(cutplan.name):
                    channel("%d: %s" % (i, plan_name))
                channel(_("----------"))
                channel(_("Plan %s:" % self._default_plan))
                for i, op_name in enumerate(cutplan.plan):
                    channel("%d: %s" % (i, op_name))
                channel(_("Commands %s:" % self._default_plan))
                for i, cmd_name in enumerate(cutplan.commands):
                    channel("%d: %s" % (i, cmd_name))
                channel(_("----------"))

            return "plan", cutplan

        @self.console_command(
            "list",
            help=_("plan<?> list"),
            input_type="plan",
            output_type="plan",
        )
        def plan_list(command, channel, _, data_type=None, data=None, **kwgs):
            channel(_("----------"))
            channel(_("Plan:"))
            for i, plan_name in enumerate(self._plan):
                channel("%d: %s" % (i, plan_name))
            channel(_("----------"))
            channel(_("Plan %s:" % data.name))
            for i, op_name in enumerate(data.plan):
                channel("%d: %s" % (i, op_name))
            channel(_("Commands %s:" % data.name))
            for i, cmd_name in enumerate(data.commands):
                channel("%d: %s" % (i, cmd_name))
            channel(_("----------"))
            return data_type, data

        @self.console_command(
            "classify",
            help=_("plan<?> classify"),
            input_type="plan",
            output_type="plan",
        )
        def plan_classify(command, channel, _, data_type=None, data=None, **kwgs):
            self.elements.classify(
                list(self.elements.elems(emphasized=True)), data.plan, data.plan.append
            )
            return data_type, data

        @self.console_command(
            "copy-selected",
            help=_("plan<?> copy-selected"),
            input_type="plan",
            output_type="plan",
        )
        def plan_copy_selected(command, channel, _, data_type=None, data=None, **kwgs):
            for c in self.elements.ops(emphasized=True):
                if c.type in ("cutcode", "blob"):
                    # CutNodes and BlobNodes are denuded into normal objects.
                    c = c.object
                copy_c = copy(c)
                try:
                    copy_c.deep_copy_children(c)
                except AttributeError:
                    pass
                try:
                    if not copy_c.output:
                        copy_c.output = True
                except AttributeError:
                    pass
                data.plan.append(copy_c)

            channel(_("Copied Operations."))
            self.signal("plan", data.name, 1)
            return data_type, data

        @self.console_command(
            "copy",
            help=_("plan<?> copy"),
            input_type="plan",
            output_type="plan",
        )
        def plan_copy(command, channel, _, data_type=None, data=None, **kwgs):
            operations = self.elements.get(type="branch ops")
            for c in operations.flat(
                types=("op", "cutcode", "cmdop", "consoleop", "lasercode", "blob"), depth=1
            ):
                try:
                    if not c.output:
                        continue
                except AttributeError:
                    pass
                try:
                    if len(c) == 0:
                        continue
                except TypeError:
                    pass
                if c.type in ("cutcode", "blob"):
                    # CutNodes and BlobNodes are denuded into normal objects.
                    c = c.object
                copy_c = copy(c)
                try:
                    copy_c.deep_copy_children(c)
                except AttributeError:
                    pass
                data.plan.append(copy_c)
            channel(_("Copied Operations."))
            self.signal("plan", data.name, 1)
            return data_type, data

        @self.console_option(
            "index", "i", type=int, help=_("index of location to insert command")
        )
        @self.console_option("op", "o", type=str, help=_("unlock, origin, home, etc."))
        @self.console_command(
            "command",
            help=_("plan<?> command"),
            input_type="plan",
            output_type="plan",
        )
        def plan_command(
            command, channel, _, data_type=None, op=None, index=None, data=None, **kwgs
        ):
            if op is None:
                channel(_("Plan Commands:"))
                for command_name in self.match("plan/.*", suffix=True):
                    channel(command_name)
                return
            try:
                for cmd, command_name, suffix in self.find("plan", op):
                    if index is None:
                        data.plan.append(cmd)
                    else:
                        try:
                            data.plan.insert(index, cmd)
                        except ValueError:
                            channel(_("Invalid index for command insert."))
                    break
                self.signal("plan", data.name, None)
            except (KeyError, IndexError):
                channel(_("No plan command found."))
            return data_type, data

        @self.console_argument("op", type=str, help=_("unlock, origin, home, etc"))
        @self.console_command(
            "append",
            help=_("plan<?> append <op>"),
            input_type="plan",
            output_type="plan",
        )
        def plan_append(
            command, channel, _, data_type=None, op=None, data=None, **kwgs
        ):
            if op is None:
                raise SyntaxError
            try:
                for plan_command, command_name, sname in self.find("plan", op):
                    data.plan.append(plan_command)
                    self.signal("plan", data.name, None)
                    return data_type, data
            except (KeyError, IndexError):
                pass
            channel(_("No plan command found."))
            return data_type, data

        @self.console_argument("op", type=str, help=_("unlock, origin, home, etc"))
        @self.console_command(
            "prepend",
            help=_("plan<?> prepend <op>"),
            input_type="plan",
            output_type="plan",
        )
        def plan_prepend(
            command, channel, _, data_type=None, op=None, data=None, **kwgs
        ):
            if op is None:
                raise SyntaxError
            for plan_command, command_name, sname in self.find("plan", op):
                data.plan.insert(0, plan_command)
                self.signal("plan", data.name, None)
                return data_type, data
            channel(_("No plan command found."))
            return data_type, data

        @self.console_command(
            "preprocess",
            help=_("plan<?> preprocess"),
            input_type="plan",
            output_type="plan",
        )
        def plan_preprocess(command, channel, _, data_type=None, data=None, **kwgs):
            data.preprocess()
            self.signal("plan", data.name, 2)
            return data_type, data

        @self.console_command(
            "validate",
            help=_("plan<?> validate"),
            input_type="plan",
            output_type="plan",
        )
        def plan_validate(command, channel, _, data_type=None, data=None, **kwgs):
            try:
                data.execute()
            except CutPlanningFailedError as e:
                self.signal("cutplanning;failed", str(e))
                data.clear()
                return
            self.signal("plan", data.name, 3)
            return data_type, data

        @self.console_command(
            "blob",
            help=_("plan<?> blob"),
            input_type="plan",
            output_type="plan",
        )
        def plan_blob(data_type=None, data=None, **kwgs):
            data.blob()
            self.signal("plan", data.name, 4)
            return data_type, data

        @self.console_command(
            "preopt",
            help=_("plan<?> preopt"),
            input_type="plan",
            output_type="plan",
        )
        def plan_preopt(data_type=None, data=None, **kwgs):
            data.preopt()
            self.signal("plan", data.name, 5)
            return data_type, data

        @self.console_command(
            "optimize",
            help=_("plan<?> optimize"),
            input_type="plan",
            output_type="plan",
        )
        def plan_optimize(data_type=None, data=None, **kwgs):
            data.execute()
            self.signal("plan", data.name, 6)
            return data_type, data

        @self.console_command(
            "clear",
            help=_("plan<?> clear"),
            input_type="plan",
            output_type="plan",
        )
        def plan_clear(data_type=None, data=None, **kwgs):
            data.clear()
            self.signal("plan", data.name, 0)
            return data_type, data

        @self.console_argument("cols", type=int, help=_("columns for the grid"))
        @self.console_argument("rows", type=int, help=_("rows for the grid"))
        @self.console_argument(
            "x_distance", type=str, help=_("x_distance each column step")
        )
        @self.console_argument(
            "y_distance", type=str, help=_("y_distance each row step")
        )
        @self.console_command(
            "step_repeat",
            help=_("plan<?> step_repeat"),
            input_type="plan",
            output_type="plan",
        )
        def plan_step_repeat(
            command,
            channel,
            _,
            cols=0,
            rows=0,
            x_distance=None,
            y_distance=None,
            data_type=None,
            data=None,
            **kwgs
        ):
            if y_distance is None:
                raise SyntaxError
            # Following must be in same order as added in preprocess()
            pre_plan_items = (
                (self.prephysicalhome, physicalhome),
                (self.prehome, home),
            )
            # Following must be in reverse order as added in preprocess()
            post_plan_items = (
                (self.autointerrupt, interrupt),
                (self.autobeep, beep),
                (self.postunlock, unlock),
                (self.autoorigin, origin),
                (self.autophysicalhome, physicalhome),
                (self.autohome, home),
            )
            post_plan = []

            c_plan = list(data.plan)
            data.plan.clear()
            data.commands.clear()
            for cmd, func in pre_plan_items:
                if cmd and c_plan[0] is func:
                    data.plan.append(c_plan.pop(0))
                elif type(c_plan[0]) == str:  # Rotary disabled
                    data.plan.append(c_plan.pop(0))

            for cmd, func in post_plan_items:
                if cmd and c_plan[-1] is func:
                    post_plan.insert(0, c_plan.pop())
                elif type(c_plan[-1]) == str:  # Rotary disabled
                    post_plan.insert(0, c_plan.pop())

            try:
                if x_distance is None:
                    x_distance = "%f%%" % (100.0 / (cols + 1))
                if y_distance is None:
                    y_distance = "%f%%" % (100.0 / (rows + 1))
            except Exception:
                pass
            x_distance = self.device.length(x_distance,1)
            y_distance = self.device.length(y_distance, 1)
            x_last = 0
            y_last = 0
            y_pos = 0
            x_pos = 0

            for j in range(rows):
                x_pos = 0
                for k in range(cols):
                    x_offset = x_pos - x_last
                    y_offset = y_pos - y_last
                    data.plan.append(origin)
                    if x_offset != 0 or y_offset != 0:
                        data.plan.append(offset(x_offset, y_offset))

                    data.plan.extend(c_plan)
                    x_last = x_pos
                    y_last = y_pos
                    x_pos += x_distance
                y_pos += y_distance
            if x_pos != 0 or y_pos != 0:
                data.plan.append(offset(-x_pos, -y_pos))
            data.plan.extend(post_plan)
            self.signal("plan", data.name, None)
            return data_type, data

        @self.console_command(
            "return",
            help=_("plan<?> return"),
            input_type="plan",
            output_type="plan",
        )
        def plan_return(command, channel, _, data_type=None, data=None, **kwgs):
            operations = self.elements.get(type="branch ops")
            operations.remove_all_children()

            for c in data.plan:
                if isinstance(c, CutCode):
                    operations.add(c, type="cutcode")
                if isinstance(c, LaserOperation):
                    copy_c = copy(c)
                    operations.add(copy_c, type="op")
            channel(_("Returned Operations."))
            self.signal("plan", data.name, None)
            return data_type, data

        @self.console_argument(
            "start", help="start index for cutcode", type=int, default=0
        )
        @self.console_argument(
            "end", help="end index for cutcode (-1 is last value)", type=int, default=-1
        )
        @self.console_command(
            "sublist",
            help=_("plan<?> sublist"),
            input_type="plan",
            output_type="plan",
        )
        def plan_sublist(
            command, channel, _, start=None, end=None, data_type=None, data=None, **kwgs
        ):
            if end == -1:
                end = float("inf")
            pos = 0
            index = 0
            size = 0
            plan = list(data.plan)
            data.plan.clear()
            c = None
            while pos < start:
                # Process prestart elements.
                try:
                    c = plan[index]
                except IndexError:
                    break
                index += 1
                if isinstance(c, CutCode):
                    c = CutCode(c.flat())
                    size = len(c)
                else:
                    size = 0
                if (pos + size) > start:
                    break
                pos += size
                size = 0
            if (pos + size) > start:
                # We overshot the start
                c = CutCode(c[start - pos :])
                pos = start
                data.plan.append(c)
            while end > pos:
                try:
                    c = plan[index]
                except IndexError:
                    break
                index += 1
                if isinstance(c, CutCode):
                    c = CutCode(c.flat())
                    size = len(c)
                else:
                    size = 0
                pos += size
                if pos > end:
                    c = CutCode(c[: end - pos])
                data.plan.append(c)

            self.signal("plan", data.name, None)
            return data_type, data

    def plan(self, **kwargs):
        for item in self._plan:
            yield item


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
    from ..image.actualize import actualize

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


def origin():
    yield "rapid_mode"
    yield "move_abs", 0, 0


def unlock():
    yield "rapid_mode"
    yield "unlock"


def home():
    yield "home"


def physicalhome():
    yield "wait_finish"
    yield "home", 0, 0


def offset(x, y):
    def offset_value():
        yield "wait_finish"
        yield "set_position", -int(x), -int(y)

    return offset_value


def wait():
    wait_amount = 5.0
    yield "wait_finish"
    yield "wait", wait_amount


def beep():
    yield "wait_finish"
    yield "beep"


def interrupt_text():
    input("Interrupted: press enter to continue...\n")
    print("... continuing")


def interrupt():
    yield "wait_finish"
    yield "function", interrupt_text


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


def short_travel_cutcode(context: CutCode, channel=None, complete_path: Optional[bool]=False, grouped_inner: Optional[bool]=False):
    """
    Selects cutcode from candidate cutcode (burns_done < passes in this CutCode),
    optimizing with greedy/brute for shortest distances optimizations.

    For paths starting at exactly the same point forward paths are preferred over reverse paths

    We start at either 0,0 or the value given in context.start

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
            ):
                # last_segment is a copy so we need to get original
                closest = last_segment.next.previous
                backwards = last_segment.normal
                distance = 0  # By definition since we are reversing and reburning

        # Stay on path in same direction if gap <= 1/20" i.e. path not quite closed
        # Travel only if path is completely burned or gap > 1/20"
        if distance > 50:
            closest = None
            for cut in context.candidate(complete_path=complete_path, grouped_inner=grouped_inner):
                s = cut.start()
                if (
                    abs(s.x - curr.real) <= distance
                    and abs(s.y - curr.imag) <= distance
                    and (
                        not complete_path
                        or cut.closed
                        or cut.first
                    )
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
                    and (
                        not complete_path
                        or cut.closed
                        or cut.last
                    )
                ):
                    d = abs(complex(e) - curr)
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
                and closest.next.start() == closest.end()
            ):
                closest = closest.next
                backwards = False
        else:
            if (
                closest.previous
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
        endpoints[i] = complex(ordered[i].start()), i, ~i, complex(ordered[i].end())
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


def inner_selection_cutcode(context: CutCode, channel=None, grouped_inner: Optional[bool]=False):
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
