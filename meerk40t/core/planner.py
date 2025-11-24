import threading
from copy import copy
from time import time

from meerk40t.kernel import Service

from ..core.cutcode.cutcode import CutCode
from .cutplan import CutPlan, CutPlanningFailedError
from .node.op_cut import CutOpNode
from .node.op_dots import DotsOpNode
from .node.op_engrave import EngraveOpNode
from .node.op_image import ImageOpNode
from .node.op_raster import RasterOpNode
from .node.util_console import ConsoleOperation
from .node.util_goto import GotoOperation
from .node.util_home import HomeOperation
from .node.util_output import OutputOperation
from .node.util_wait import WaitOperation
from .units import Length

"""
The planner module provides cut planning services. This provides a method of going from operations + elements into
cutcode which is then put inside a laserjob and sent to a spooler. Most of these operations are called on the
individual CutPlan objects.
"""
STAGE_PLAN_INIT = 0
STAGE_PLAN_CLEAR = 2
STAGE_PLAN_COPY = 1
STAGE_PLAN_VALIDATED = 3
STAGE_PLAN_GEOMETRY = 4
STAGE_PLAN_PREPROCESSED = 5
STAGE_PLAN_PREOPTIMIZED = 6
STAGE_PLAN_OPTIMIZED = 7
STAGE_PLAN_BLOB = 8
STAGE_PLAN_FINISHED = 99
STAGE_PLAN_INFO = 150


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
        ]
        kernel.register_choices("planner", choices)
        INNER_WARNING = _(
            "Notabene: When using both Reduce Travel Time and Burn Inner First, "
            "travel optimization occurs within each hierarchy level (inners before outers)."
        )
        choices = [
            {
                "attr": "opt_raster_optimisation",
                "object": context,
                "default": True,
                "type": bool,
                "label": _("Cluster raster objects"),
                "tip": _(
                    "Separate non-overlapping raster objects.\n"
                    "Active: this will raster close (i.e. overlapping) objects as one,\n"
                    "but will separately process objects lying apart from each other.\n"
                    "Inactive: all objects will be lasered as one single unit."
                ),
                "page": "Optimisations",
                # Hint for translation _("Reducing Movements")
                "section": "_20_Reducing Movements",
                # Hint for translation _("Splitting rasters")
                "subsection": "Splitting rasters",
            },
            {
                "attr": "opt_raster_opt_margin",
                "object": context,
                "default": "1mm",
                "type": Length,
                "label": _("Margin:"),
                "tip": _(
                    "Allowed gap between rasterable objects, to still be counted as one."
                ),
                "page": "Optimisations",
                # Hint for translation _("Reducing Movements")
                "section": "_20_Reducing Movements",
                # Hint for translation _("Splitting rasters")
                "subsection": "Splitting rasters",
                "conditional": (context, "opt_raster_optimisation"),
            },
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
                )
                + "\n"
                + INNER_WARNING,
                "page": "Optimisations",
                # Hint for translation _("Reducing Movements")
                "section": "_20_Reducing Movements",
            },
            {
                "attr": "opt_complete_subpaths",
                "object": context,
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
                ),
                "page": "Optimisations",
                # Hint for translation _("Reducing Movements")
                "section": "_20_Reducing Movements",
                "conditional": (context, "opt_reduce_travel"),
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
                "page": "Optimisations",
                # Hint for translation _("Reducing Movements")
                "section": "_20_Reducing Movements",
                "conditional": (context, "opt_reduce_travel"),
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
                "page": "Optimisations",
                # Hint for translation _("Reducing Movements")
                "section": "_20_Reducing Movements",
                "conditional": (context, "opt_reduce_travel"),
            },
            {
                "attr": "opt_stitching",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Combine path segments"),
                "tip": _(
                    "Stitch segments together that are very close (ideally having joint start/end points)."
                )
                + "\n"
                + _("Only inside a single cut/engrave operation."),
                "page": "Optimisations",
                # Hint for translation _("Stitching")
                "section": "_05_Stitching",
            },
            {
                "attr": "opt_stitch_tolerance",
                "object": context,
                "default": "0",
                "type": Length,
                "label": _("Tolerance"),
                "tip": _(
                    "Tolerance to decide whether two path segments should be joined."
                ),
                "page": "Optimisations",
                # Hint for translation _("Stitching")
                "section": "_05_Stitching",
                "conditional": (context, "opt_stitching"),
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
                )
                + "\n"
                + INNER_WARNING,
                "page": "Optimisations",
                # Hint for translation _("Burn sequence")
                "section": "_10_Burn sequence",
            },
            {
                "attr": "opt_inner_tolerance",
                "object": context,
                "default": "0",
                "type": Length,
                "label": _("Tolerance"),
                "tip": _("Tolerance to decide if a shape is truly inside another one."),
                "page": "Optimisations",
                # Hint for translation _("Burn sequence")
                "section": "_10_Burn sequence",
                "conditional": (context, "opt_inner_first"),
            },
            {
                "attr": "opt_inners_grouped",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Group Inner Burns"),
                "tip": _(
                    "Try to complete a set of inner burns and the associated outer cut before moving onto other elements.\n"
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
                "page": "Optimisations",
                # Hint for translation _("Burn sequence")
                "section": "_10_Burn sequence",
                "conditional": (context, "opt_inner_first"),
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
                "page": "Optimisations",
                # Hint for translation _("Reducing Movements")
                "section": "_20_Reducing Movements",
                "hidden": True,
            },
            {
                "attr": "opt_effect_combine",
                "object": context,
                "default": True,
                "type": bool,
                "label": _("Keep effect lines together"),
                "tip": (
                    _("Active: effects like hatches are dealt with as a bigger shape")
                    + "\n"
                    + _(
                        "Inactive: every single line segment will be dealt with individually."
                    )
                ),
                "page": "Optimisations",
                # Hint for translation _("Effects")
                "section": "_25_Effects",
            },
            {
                "attr": "opt_effect_optimize",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Optimize internally"),
                "tip": (
                    _("Active: hatch lines will be optimized internally")
                    + "\n"
                    + _("Inactive: hatch lines will be burnt sequentially.")
                ),
                "page": "Optimisations",
                # Hint for translation _("Effects")
                "section": "_25_Effects",
                "conditional": (context, "opt_effect_combine"),
            },
            {
                "attr": "opt_reduce_details",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Reduce polyline details"),
                "tip": _(
                    "Active: reduce the details of polyline elements,\n"
                    + "so that less information needs to be sent to the laser."
                )
                + "\n"
                + _(
                    "This can reduce the processing and laser time but can as well\n"
                    + "compromise the quality at higher levels, so use with care and preview in simulation."
                ),
                "page": "Optimisations",
                # Hint for translation _("Details")
                "section": "_30_Details",
                "subsection": "_10_",
            },
            {
                "attr": "opt_reduce_tolerance",
                "object": context,
                "default": 10,
                "type": int,
                "label": _("Level"),
                "style": "option",
                "choices": (1, 10, 50, 100),
                "display": (_("Minimal"), _("Fine"), _("Medium"), _("Coarse")),
                "tip": _(
                    "This can reduce the processing and laser time but can as well\n"
                    + "compromise the quality at higher levels, so use with care and preview in simulation."
                ),
                "page": "Optimisations",
                # Hint for translation _("Details")
                "section": "_30_Details",
                "subsection": "_10_",
                "conditional": (context, "opt_reduce_details"),
            },
        ]
        for c in choices:
            c["help"] = "optimisation"
        kernel.register_choices("optimize", choices)
        context.setting(bool, "opt_2opt", False)
        context.setting(bool, "opt_nearest_neighbor", True)
        context.setting(bool, "opt_start_from_position", False)

        # context.setting(int, "opt_closed_distance", 15)
        # context.setting(bool, "opt_merge_passes", False)
        # context.setting(bool, "opt_merge_ops", False)
        # context.setting(bool, "opt_inner_first", True)

    elif lifecycle == "poststart":
        planner = kernel.planner
        auto = hasattr(kernel.args, "auto") and kernel.args.auto
        console = hasattr(kernel.args, "console") and kernel.args.console
        quit = hasattr(kernel.args, "quit") and kernel.args.quit
        if auto:
            planner("plan copy preprocess validate blob preopt optimize\n")
            if quit or not console:
                planner("plan console quit\n")
            planner("plan spool\n")


class Planner(Service):
    """
    Planner is a service that manages cut planning and job creation for the kernel.
    It provides thread-safe access to cut plans, tracks plan states and stages, and exposes
    a set of console commands for manipulating plans, operations, and job execution.
    Plans are tracked with multiple stages (init, copy, preprocess, optimize, etc.),
    and the planner ensures that plan creation and modification are safe for concurrent use.
    """

    STAGE_DESCRIPTIONS = {
        STAGE_PLAN_INIT: "Init",
        STAGE_PLAN_CLEAR: "Clear",
        STAGE_PLAN_COPY: "Copy",
        STAGE_PLAN_PREPROCESSED: "Pre-Proc",
        STAGE_PLAN_PREOPTIMIZED: "Pre-Opt",
        STAGE_PLAN_OPTIMIZED: "Opt",
        STAGE_PLAN_INFO: "Info",
        STAGE_PLAN_VALIDATED: "Valid",
        STAGE_PLAN_GEOMETRY: "Geom",
        STAGE_PLAN_BLOB: "Blob",
        STAGE_PLAN_FINISHED: "Done",
    }

    def __init__(self, kernel, *args, **kwargs):
        """
        Initialize the Planner service.
        Sets up plan and state tracking, default plan, and thread lock for safe concurrent access.
        """
        Service.__init__(self, kernel, "planner")
        self._plan = {}  # contains all cutplans, keyed by plan name
        self._states = {}  # contains all plan state dictionaries, keyed by plan name
        self._default_plan = "0"
        # self.do_optimization = True
        self._plan_lock = threading.Lock()

    @property
    def do_optimization(self):
        """
        Get the optimization flag.
        """
        value = self.kernel.root.setting(bool, "do_optimization", True)
        return value

    @do_optimization.setter
    def do_optimization(self, value):
        """
        Set the optimization flag.
        """
        self.kernel.root.setting(bool, "do_optimization", value)
        self.kernel.root.do_optimization = value
    
    def length(self, v):
        """
        Convert a value to a float using the Length class (device-indepen
        dent units).
        """
        return float(Length(v))

    def length_x(self, v):
        """
        Convert a value to a float relative to the device's view width.
        """
        return float(Length(v, relative_length=self.device.view.width))

    def length_y(self, v):
        """
        Convert a value to a float relative to the device's view height.
        """
        return float(Length(v, relative_length=self.device.view.height))

    def __get_or_make_plan(self, plan_name):
        """
        Internal helper to get an existing plan by name, or create a new one if it does not exist.
        Initializes the plan's state tracking as well. Thread safety must be handled by the caller.
        """
        try:
            return self._plan[plan_name]
        except KeyError:
            self._plan[plan_name] = CutPlan(plan_name, self)
            self._states[plan_name] = {STAGE_PLAN_INIT: time()}
        return self._plan[plan_name]

    def get_or_make_plan(self, plan_name):
        """
        Thread-safe method to get or create a plan by name.
        Returns the CutPlan instance for the given plan name.
        """
        with self._plan_lock:
            plan = self.__get_or_make_plan(plan_name)
        return plan

    @property
    def default_plan(self):
        """
        Returns the default plan (usually plan '0').
        """
        return self.get_or_make_plan(self._default_plan)

    def service_attach(self, *args, **kwargs):
        _ = self.kernel.translation

        @self.console_command(
            "list-plans",
            help=_("List all available plans"),
            input_type=None,
            output_type=None,
        )
        def list_plans(command, channel, _, **kwgs):
            if not self._plan:
                channel(_("No plans available."))
                return
            channel(_("Available plans:"))
            for i, plan in enumerate(self._plan):
                stage, info = self.get_plan_stage(plan)
                channel(f"{i + 1}: {plan} (State: {info})")

        @self.console_command(
            "plan",
            help="plan<?> <command> : " + _("issue a command to modify the plan"),
            regex=True,
            input_type=(None, "ops"),
            output_type="plan",
        )
        def plan_base(command, channel, _, data=None, remainder=None, **kwgs):
            if len(command) > 4:
                self._default_plan = command[4:]

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
                        copy_c.copy_children_as_real(c)
                    except AttributeError:
                        pass
                    cutplan.plan.append(copy_c)
                return "plan", cutplan
            if remainder is None:
                channel(_("----------"))
                channel(_("Plan:") + self._default_plan)
                if isinstance(cutplan.name, str):
                    channel(f"{1}: {cutplan.name}")
                else:
                    for i, plan_name in enumerate(cutplan.name):
                        channel(f"{i + 1}: {plan_name}")
                channel(_("----------"))
                state, info = self.get_plan_stage(self._default_plan)
                channel(
                    _("Plan {plan}: {state}").format(
                        plan=self._default_plan, state=info
                    )
                )
                for i, op_name in enumerate(cutplan.plan):
                    channel(f"{i + 1}: {op_name}")
                channel(_("Commands {plan}:").format(plan=self._default_plan))
                for i, cmd_name in enumerate(cutplan.commands):
                    channel(f"{i + 1}: {cmd_name}")
                channel(_("----------"))

            return "plan", cutplan

        @self.console_command(
            ("copy", "copy-selected"),
            help=_(
                "plan<?> copy / copy-selected: copy data from all / only from selected operations"
            ),
            input_type="plan",
            output_type="plan",
        )
        def plan_copy(command, channel, _, data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            busy = self.kernel.busyinfo
            if busy.shown:
                busy.change(msg=_("Copy data"), keep=1)
                busy.show()

            operations = data  # unused.
            if command == "copy-selected":
                operations = list(self.elements.ops(emphasized=True))
                copy_selected = True
            else:
                operations = list(self.elements.ops())
                copy_selected = False

            def init_settings():
                for prefix in ("prepend", "append"):
                    str_count = f"{prefix}_op_count"
                    self.device.setting(int, str_count, 0)
                    value = getattr(self.device, str_count, 0)
                    if value > 0:
                        for idx in range(value):
                            attr1 = f"{prefix}_op_{idx:02d}"
                            attr2 = f"{prefix}_op_param_{idx:02d}"
                            self.device.setting(str, attr1, "")
                            self.device.setting(str, attr2, "")

            def add_ops(is_prepend):
                # Do we have any default actions to include first?
                if is_prepend:
                    prefix = "prepend"
                else:
                    prefix = "append"
                try:
                    if is_prepend:
                        count = self.device.prepend_op_count
                    else:
                        count = self.device.append_op_count
                except AttributeError:
                    count = 0
                idx = 0
                while idx <= count - 1:
                    addop = None
                    attr1 = f"{prefix}_op_{idx:02d}"
                    attr2 = f"{prefix}_op_param_{idx:02d}"
                    if hasattr(self.device, attr1):
                        optype = getattr(self.device, attr1, None)
                        opparam = getattr(self.device, attr2, None)
                        if optype is not None:
                            if optype == "util console":
                                addop = ConsoleOperation(command=opparam)
                            elif optype == "util home":
                                addop = HomeOperation()
                            elif optype == "util output":
                                if opparam is not None:
                                    params = opparam.split(",")
                                    mask = 0
                                    setvalue = 0
                                    if len(params) > 0:
                                        try:
                                            mask = int(params[0])
                                        except ValueError:
                                            mask = 0
                                    if len(params) > 1:
                                        try:
                                            setvalue = int(params[1])
                                        except ValueError:
                                            setvalue = 0
                                    if mask != 0 or setvalue != 0:
                                        addop = OutputOperation(
                                            output_mask=mask, output_value=setvalue
                                        )
                            elif optype == "util goto":
                                if opparam is not None:
                                    params = opparam.split(",")
                                    x = 0
                                    y = 0
                                    if len(params) > 0:
                                        try:
                                            x = float(Length(params[0]))
                                        except ValueError:
                                            x = 0
                                    if len(params) > 1:
                                        try:
                                            y = float(Length(params[1]))
                                        except ValueError:
                                            y = 0
                                    absolute = False
                                    if len(params) > 2:
                                        absolute = params[2] not in ("False", "0")
                                    addop = GotoOperation(x=x, y=y, absolute=absolute)
                            elif optype == "util wait":
                                if opparam is not None:
                                    try:
                                        opparam = float(opparam)
                                    except ValueError:
                                        opparam = None
                                if opparam is not None:
                                    addop = WaitOperation(wait=opparam)
                    if addop is not None:
                        try:
                            if not addop.output:
                                continue
                        except AttributeError:
                            pass
                        try:
                            if len(addop) == 0:
                                continue
                        except TypeError:
                            pass
                        if addop.type == "cutcode":
                            # CutNodes are denuded into normal objects.
                            addop = addop.cutcode
                        copy_c = copy(addop)
                        try:
                            copy_c.copy_children_as_real(addop)
                        except AttributeError:
                            pass
                        data.plan.append(copy_c)

                    idx += 1

            init_settings()

            # Add default start ops
            if busy.shown:
                busy.change(msg=_("Adding trailing operations"), keep=1)
                busy.show()
            add_ops(True)
            # types = (
            #     "op cut",
            #     "op raster",
            #     "op image",
            #     "op engrave",
            #     "op dots",
            #     "cutcode",
            #     "util console",
            #     "util wait",
            #     "util home",
            #     "util goto",
            #     "util input",
            #     "util output",
            #     "place point"
            #     "blob",
            # )
            c_count = 0
            update_interval = 10  # Update busy indicator every 10 commands
            for c in operations:
                c_count += 1
                if busy.shown and (c_count % update_interval) == 0:
                    busy.change(
                        msg=_("Copying data {count}").format(count=c_count), keep=2
                    )
                    busy.show()

                isactive = True
                try:
                    if not c.output:
                        isactive = False
                except AttributeError:
                    pass
                if not isactive and copy_selected and len(operations) == 1:
                    # If it's the only one we make an exception
                    isactive = True
                if not isactive:
                    continue
                if not hasattr(c, "type") or c.type is None:
                    # Node must be a type of node.
                    continue
                if c.type.startswith("op ") and len(c.children) == 0:
                    # We don't need empty operations.
                    continue
                if c.type == "cutcode":
                    # CutNodes are denuded into normal objects.
                    c = c.cutcode

                # Make copy of node.
                copy_c = copy(c)
                try:
                    # Make copy of real (non-referenced) children if that is permitted.
                    copy_c.copy_children_as_real(c)
                except AttributeError:
                    pass
                data.plan.append(copy_c)

            # Add default trailing ops
            if busy.shown:
                busy.change(msg=_("Adding trailing operations"), keep=1)
                busy.show()
            add_ops(False)
            channel(_("Copied Operations."))
            self.update_stage(data.name, STAGE_PLAN_COPY)
            return data_type, data

        @self.console_option(
            "index", "i", type=int, help=_("index of location to insert command")
        )
        @self.console_argument("console", type=str, help=_("console command to append"))
        @self.console_command(
            "console",
            help="plan<?> command : " + _("inject a console command into the plan"),
            input_type="plan",
            output_type="plan",
            all_arguments_required=True,
        )
        def plan_command(
            command,
            channel,
            _,
            data_type=None,
            data=None,
            console=None,
            index=None,
            **kwgs,
        ):
            if not console:
                channel(
                    _(
                        "plan console... requires a console command to inject into the current plan"
                    )
                )
            else:
                cmd = ConsoleOperation(command=console)
                if index is None:
                    data.plan.append(cmd)
                else:
                    try:
                        data.plan.insert(index, cmd)
                    except ValueError:
                        channel(_("Invalid index for command insert."))
                self.update_stage(data.name, STAGE_PLAN_INFO)
            return data_type, data

        @self.console_command(
            "preprocess",
            help="plan<?> preprocess : " + _("prepare the plan for execution"),
            input_type="plan",
            output_type="plan",
        )
        def plan_preprocess(command, channel, _, data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            busy = self.kernel.busyinfo
            if busy.shown:
                busy.change(msg=_("Preprocessing"), keep=1)
                busy.show()

            data.preprocess()
            self.update_stage(data.name, STAGE_PLAN_PREPROCESSED)
            return data_type, data

        @self.console_command(
            "validate",
            help="plan<?> validate : " + _("validate the plan for execution"),
            input_type="plan",
            output_type="plan",
        )
        def plan_validate(command, channel, _, data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            busy = self.kernel.busyinfo
            if busy.shown:
                busy.change(msg=_("Validating"), keep=1)
                busy.show()

            try:
                data.execute()
            except CutPlanningFailedError as e:
                self.signal("cutplanning;failed", str(e))
                data.clear()
                return
            self.update_stage(data.name, STAGE_PLAN_VALIDATED)
            return data_type, data

        @self.console_command(
            "geometry",
            help="plan<?> geometry : " + _("extract the geometry from the plan"),
            input_type="plan",
            output_type="plan",
        )
        def plan_geometry(data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            busy = self.kernel.busyinfo
            if busy.shown:
                busy.change(msg=_("Converting data"), keep=1)
                busy.show()

            data.geometry()
            self.update_stage(data.name, STAGE_PLAN_GEOMETRY)
            return data_type, data

        @self.console_command(
            "blob",
            help="plan<?> blob : " + _("create the device specific format to send to the laser"),
            input_type="plan",
            output_type="plan",
        )
        def plan_blob(data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            busy = self.kernel.busyinfo
            if busy.shown:
                busy.change(msg=_("Converting data"), keep=1)
                busy.show()

            data.blob()
            self.update_stage(data.name, STAGE_PLAN_BLOB)
            return data_type, data

        @self.console_command(
            "preopt",
            help="plan<?> preopt : " + _("prepare the plan for optimisation"),
            input_type="plan",
            output_type="plan",
        )
        def plan_preopt(data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            busy = self.kernel.busyinfo
            if busy.shown:
                busy.change(msg=_("Preparing optimisation"), keep=1)
                busy.show()

            data.preopt()
            self.update_stage(data.name, STAGE_PLAN_PREOPTIMIZED)
            return data_type, data

        @self.console_command(
            "optimize",
            help="plan<?> optimize : " + _("optimize the plan for execution, eg travel reduction"),
            input_type="plan",
            output_type="plan",
        )
        def plan_optimize(data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            busy = self.kernel.busyinfo
            if busy.shown:
                busy.change(msg=_("Optimising"), keep=1)
                busy.show()

            data.execute()
            self.update_stage(data.name, STAGE_PLAN_OPTIMIZED)
            return data_type, data

        @self.console_command(
            "clear",
            help="plan<?> clear : " + _("clear the plan"),
            input_type="plan",
            output_type="plan",
        )
        def plan_clear(data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            busy = self.kernel.busyinfo
            if busy.shown:
                busy.change(msg=_("Clearing data"), keep=1)
                busy.show()

            data.clear()
            self.update_stage(data.name, STAGE_PLAN_CLEAR)
            return data_type, data

        @self.console_command(
            "finish",
            help="plan<?> finish : " + _("deem the plan to be finished"),
            input_type="plan",
            output_type="plan",
        )
        def plan_finish(data_type=None, data=None, **kwgs):
            # Update Info-panel if displayed
            self.update_stage(data.name, STAGE_PLAN_FINISHED)
            return data_type, data

        @self.console_command(
            "return",
            help="plan<?> return : " + _("extract the operations from the plan back to the tree"),
            input_type="plan",
            output_type="plan",
        )
        def plan_return(command, channel, _, data_type=None, data=None, **kwgs):
            operations = self.elements.get(type="branch ops")
            with self.elements.node_lock:
                operations.remove_all_children()
                for c in data.plan:
                    if isinstance(c, CutCode):
                        operations.add(type="cutcode", cutcode=c)
                    if isinstance(
                        c,
                        (
                            RasterOpNode,
                            ImageOpNode,
                            CutOpNode,
                            EngraveOpNode,
                            DotsOpNode,
                        ),
                    ):
                        copy_c = copy(c)
                        operations.add_node(copy_c)
            channel(_("Returned Operations."))
            self.update_stage(data.name, STAGE_PLAN_INFO)
            return data_type, data

        @self.console_argument(
            "start", help="start index for cutcode", type=int, default=0
        )
        @self.console_argument(
            "end", help="end index for cutcode (-1 is last value)", type=int, default=-1
        )
        @self.console_command(
            "sublist",
            help="plan<?> sublist : " + _("extract a sublist from the plan"),
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

            self.update_stage(data.name, STAGE_PLAN_INFO)
            return data_type, data

    def plan(self, **kwargs):
        yield from self._plan

    def finish_plan(self, plan_name):
        self.update_stage(plan_name, STAGE_PLAN_FINISHED)

    def has_content(self, plan_name):
        """
        Checks if the specified plan has any content (i.e., non-empty plan list).
        Returns True if the plan exists and contains at least one operation.
        """
        if plan_name not in self._plan:
            return False
        return len(self._plan[plan_name].plan) > 0

    def get_last_plan(self):
        """
        Finds and returns the most recently finished plan name that has content.
        Returns the plan name, or None if no such plan exists.
        """
        last = None
        last_time = 0
        with self._plan_lock:
            for candidate in self._plan:
                plan = self._plan[candidate]
                if (
                    STAGE_PLAN_FINISHED not in self._states[candidate]
                    or len(plan.plan) == 0
                ):
                    continue
                # Make sure we take the most recent
                t = self._states[candidate].get(STAGE_PLAN_FINISHED, 0)
                if t > last_time:
                    last_time = t
                    last = candidate
        return last

    def get_free_plan(self):
        """
        Finds and returns a unique plan name not currently in use or a finished plan that can be reused.
        This method generates a new plan name by incrementing a counter until an unused or finished name is found.
        Returns the new unique plan name as a string.
        """
        candidate = "z"
        index = 1
        with self._plan_lock:
            while True:
                if candidate not in self._plan:
                    plan = self.__get_or_make_plan(candidate)
                    break
                # We take this if we finished the plan
                if STAGE_PLAN_FINISHED in self._states[candidate]:
                    break
                candidate = f"z{index}"
                index += 1
        return candidate

    def update_stage(self, plan_name, stage):
        """
        Updates the stage of a plan, recording the current time for the given stage.
        If clearing, resets all other stages. Otherwise, adds the new stage to the plan's state dictionary.
        Emits a 'plan' signal with the plan name and stage.
        """
        if plan_name not in self._states:
            self.console(f"Couldn't update plan {plan_name}: not found")
            return
        with self._plan_lock:
            if stage == STAGE_PLAN_CLEAR:
                self._states[plan_name].clear()
            self._states[plan_name][stage] = time()
        self.signal("plan", plan_name, stage)

    def get_plan_stage(self, plan_name):
        """
        Returns the current state dictionary and a comma-separated string of all reached stage descriptions for a plan (ordered desc)
        """
        states = self._states.get(plan_name, {})
        if not states:
            return None, ""
        ordered = sorted(states.items(), key=lambda kv: kv[1], reverse=True)
        info = ", ".join(self.STAGE_DESCRIPTIONS[s] for s, _ in ordered)
        return states, info

    def is_finished(self, plan_name):
        """
        Checks if the specified plan has reached the finished stage.
        Returns True if the plan exists and has the STAGE_PLAN_FINISHED recorded.
        """
        if plan_name not in self._states:
            return False
        with self._plan_lock:
            finished = STAGE_PLAN_FINISHED in self._states[plan_name]
        return finished
