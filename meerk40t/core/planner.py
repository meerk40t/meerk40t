from copy import copy

from meerk40t.kernel import Service

from ..core.cutcode import CutCode
from .cutplan import CutPlan, CutPlanningFailedError
from .node.op_cut import CutOpNode
from .node.op_dots import DotsOpNode
from .node.op_engrave import EngraveOpNode
from .node.op_hatch import HatchOpNode
from .node.op_image import ImageOpNode
from .node.op_raster import RasterOpNode
from .node.util_console import ConsoleOperation
from .node.util_goto import GotoOperation
from .node.util_home import HomeOperation
from .node.util_origin import SetOriginOperation
from .node.util_output import OutputOperation
from .node.util_wait import WaitOperation
from .units import Length


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
                "page": "Optimizations",
                "section": "",
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
                "page": "Optimizations",
                "section": "Burn sequence",
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
                "page": "Optimizations",
                "section": "Merging",
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
                "page": "Optimizations",
                "section": "Merging",
                "conditional": (context, "opt_reduce_travel"),
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
                "page": "Optimizations",
                "section": "Burn sequence",
                "subsection": "Inner burn",
            },
            {
                "attr": "opt_inner_tolerance",
                "object": context,
                "default": "0",
                "type": Length,
                "label": _("Tolerance"),
                "tip": _("Tolerance to decide if a shape is truly inside another one."),
                "page": "Optimizations",
                "section": "Burn sequence",
                "subsection": "Inner burn",
                "conditional": (context, "opt_inner_first"),
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
                "page": "Optimizations",
                "section": "Burn sequence",
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
                "page": "Optimizations",
                "section": "",
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
        planner = kernel.planner
        auto = hasattr(kernel.args, "auto") and kernel.args.auto
        if auto:
            planner("plan copy preprocess validate blob preopt optimize\n")
            if hasattr(kernel.args, "quit") and kernel.args.quit:
                planner("plan console quit\n")
            planner("plan spool\n")


class Planner(Service):
    """
    Planner is a service that adds 'plan' commands to the kernel. These are text based versions of the job preview and
    should be permitted to control the job creation process.
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "planner")
        self._plan = dict()
        self._default_plan = "0"

    def length(self, v):
        return float(Length(v))

    def length_x(self, v):
        return float(Length(v, relative_length=self.device.width))

    def length_y(self, v):
        return float(Length(v, relative_length=self.device.height))

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
        _ = self.kernel.translation

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
                        copy_c.copy_children_as_real(c)
                    except AttributeError:
                        pass
                    cutplan.plan.append(copy_c)
                self.signal("plan", self._default_plan, 1)
                return "plan", cutplan
            if remainder is None:
                channel(_("----------"))
                channel(_("Plan:"))
                for i, plan_name in enumerate(cutplan.name):
                    channel(f"{i}: {plan_name}")
                channel(_("----------"))
                channel(_("Plan {plan}:").format(plan=self._default_plan))
                for i, op_name in enumerate(cutplan.plan):
                    channel(f"{i}: {op_name}")
                channel(_("Commands {plan}:").format(plan=self._default_plan))
                for i, cmd_name in enumerate(cutplan.commands):
                    channel(f"{i}: {cmd_name}")
                channel(_("----------"))

            return "plan", cutplan

        @self.console_command(
            "copy-selected",
            help=_("plan<?> copy-selected"),
            input_type="plan",
            output_type="plan",
        )
        def plan_copy_selected(command, channel, _, data_type=None, data=None, **kwgs):
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
                                        addop = OutputOperation(mask, setvalue)
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
                                    addop = GotoOperation(x=x, y=y)
                            elif optype == "util origin":
                                if opparam is not None and opparam != "":
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
                                    addop = SetOriginOperation(x=x, y=y)
                                else:
                                    addop = SetOriginOperation(x=None, y=None)
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
            add_ops(True)

            for c in self.elements.ops(emphasized=True):
                if c.type == "cutcode":
                    # CutNodes are denuded into normal objects.
                    c = c.cutcode
                elif c.type == "blob":
                    # BlobNodes are denuded into normal objects.
                    c = c.blob
                copy_c = copy(c)
                try:
                    copy_c.copy_children_as_real(c)
                except AttributeError:
                    pass
                try:
                    if not copy_c.output:
                        copy_c.output = True
                except AttributeError:
                    pass
                data.plan.append(copy_c)

            # Add default start ops
            add_ops(False)

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
                                        addop = OutputOperation(mask, setvalue)
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
                                    addop = GotoOperation(x=x, y=y)
                            elif optype == "util origin":
                                if opparam is not None and opparam != "":
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
                                    addop = SetOriginOperation(x=x, y=y)
                                else:
                                    addop = SetOriginOperation(x=None, y=None)
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
            operations = self.elements.get(type="branch ops")

            # Add default start ops
            add_ops(True)
            for c in operations.flat(
                types=(
                    "op cut",
                    "op raster",
                    "op image",
                    "op engrave",
                    "op dots",
                    "op hatch",
                    "cutcode",
                    "util console",
                    "util wait",
                    "util home",
                    "util goto",
                    "util origin",
                    "util input",
                    "util output",
                    "lasercode",
                    "blob",
                ),
                depth=1,
            ):
                try:
                    if not c.output:
                        continue
                except AttributeError:
                    pass
                try:
                    if c.type.startswith("op") and len(c.children) == 0:
                        continue
                except TypeError:
                    pass
                if c.type == "cutcode":
                    # CutNodes are denuded into normal objects.
                    c = c.cutcode
                copy_c = copy(c)
                try:
                    copy_c.copy_children_as_real(c)
                except AttributeError:
                    pass
                data.plan.append(copy_c)
            # Add default trailing ops
            add_ops(False)
            channel(_("Copied Operations."))
            self.signal("plan", data.name, 1)
            return data_type, data

        @self.console_option(
            "index", "i", type=int, help=_("index of location to insert command")
        )
        @self.console_argument("console", type=str, help=_("console command to append"))
        @self.console_command(
            "console",
            help=_("plan<?> command"),
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
                self.signal("plan", data.name, None)
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
                if isinstance(
                    c,
                    (
                        RasterOpNode,
                        ImageOpNode,
                        CutOpNode,
                        EngraveOpNode,
                        DotsOpNode,
                        HatchOpNode,
                    ),
                ):
                    copy_c = copy(c)
                    operations.add_node(copy_c)
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
