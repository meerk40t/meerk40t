from copy import copy
from typing import Any, Callable, Dict, Generator, Optional, Tuple, Union

from .cutcode import CutCode, CutGroup, CutObject, RasterCut
from .cutplan import CutPlan
from ..svgelements import Group, Length, Polygon, SVGElement, SVGImage, SVGText
from ..device.lasercommandconstants import (
    COMMAND_BEEP,
    COMMAND_FUNCTION,
    COMMAND_HOME,
    COMMAND_MODE_RAPID,
    COMMAND_MOVE,
    COMMAND_SET_ABSOLUTE,
    COMMAND_SET_POSITION,
    COMMAND_UNLOCK,
    COMMAND_WAIT,
    COMMAND_WAIT_FINISH,
)
from ..kernel import Modifier

MILS_IN_MM = 39.3701

def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel_root = kernel.root
        kernel.register("modifier/Planner", Planner)

        kernel.register("plan/physicalhome", physicalhome)
        kernel.register("plan/home", home)
        kernel.register("plan/origin", origin)
        kernel.register("plan/unlock", unlock)
        kernel.register("plan/wait", wait)
        kernel.register("plan/beep", beep)
        kernel.register("function/interrupt", interrupt_text)
        kernel.register("plan/interrupt", interrupt)

        def shutdown():
            yield COMMAND_WAIT_FINISH

            def shutdown_program():
                kernel_root("quit\n")

            yield COMMAND_FUNCTION, shutdown_program

        kernel.register("plan/shutdown", shutdown)

    elif lifecycle == "boot":
        kernel_root = kernel.root
        kernel_root.activate("modifier/Planner")

        context = kernel.root
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
                "attr": "opt_rapid_between",
                "object": context,
                "default": True,
                "type": bool,
                "label": _("Rapid Moves Between Objects"),
                "tip": _(
                    "Travel between objects (laser off) at the default/rapid speed rather than at the current laser-on speed"
                ),
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
                    "How close (mils) do endpoints need to be to count as closed?"
                ),
            },
            {
                "attr": "opt_jog_minimum",
                "object": context,
                "default": 256,
                "type": int,
                "label": _("Minimum Jog Distance"),
                "tip": _(
                    "Distance (mils) at which a gap should be rapid-jog rather than moved at current speed."
                ),
            },
        ]
        kernel.register_choices("optimize", choices)


class Planner(Modifier):
    """
    Planner is a modifier that adds 'plan' commands to the kernel. These are text based versions of the job preview and
    should be permitted to control the job creation process.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._plan = dict()
        self._default_plan = "0"

    def get_or_make_plan(self, plan_name):
        """
        Plans are a tuple of 3 lists and the name. Plan, Original, Commands, and Plan-Name
        """
        try:
            return self._plan[plan_name]
        except KeyError:
            self._plan[plan_name] = CutPlan(plan_name, self.context)
            return self._plan[plan_name]

    def default_plan(self):
        return self.get_or_make_plan(self._default_plan)

    def attach(self, *a, **kwargs):
        context = self.context
        context.planner = self
        context.default_plan = self.default_plan

        _ = self.context._
        elements = context.elements
        rotary_context = self.context.get_context("rotary/1")
        bed_dim = context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)

        rotary_context.setting(bool, "rotary", False)
        rotary_context.setting(float, "scale_x", 1.0)
        rotary_context.setting(float, "scale_y", 1.0)

        # Following settings are experimental and can only be set from the console
        self.context.setting(bool, "opt_2opt", False)
        self.context.setting(bool, "opt_nearest_neighbor", True)
        self.context.setting(int, "opt_jog_mode", 0)

        # Following three options seem to be obsolete as there is no meaningful code that uses it
        self.context.setting(bool, "opt_reduce_directions", False)
        self.context.setting(bool, "opt_remove_overlap", False)
        self.context.setting(bool, "opt_start_from_position", False)


        @self.context.console_argument(
            "alias", type=str, help=_("plan command name to alias")
        )
        @self.context.console_command(
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
            if plan_command in self.context.registered:
                raise SyntaxError(_("You may not overwrite an already used alias."))

            def user_defined_alias():
                for s in remainder.split(";"):
                    self.context(s + "\n")

            user_defined_alias.__name__ = remainder
            self.context.registered[plan_command] = user_defined_alias

        @self.context.console_command(
            "plan",
            help=_("plan<?> <command>"),
            regex=True,
            input_type=(None, "ops"),
            output_type="plan",
        )
        def plan_base(command, channel, _, data=None, remainder=None, **kwgs):
            if len(command) > 4:
                self._default_plan = command[4:]
                self.context.signal("plan", self._default_plan, None)

            cutplan = self.get_or_make_plan(self._default_plan)
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
                self.context.signal("plan", self._default_plan, 1)
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

        @self.context.console_command(
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

        @self.context.console_command(
            "classify",
            help=_("plan<?> classify"),
            input_type="plan",
            output_type="plan",
        )
        def plan_classify(command, channel, _, data_type=None, data=None, **kwgs):
            elements.classify(
                list(elements.elems(emphasized=True)), data.plan, data.plan.append
            )
            return data_type, data

        @self.context.console_command(
            "copy-selected",
            help=_("plan<?> copy-selected"),
            input_type="plan",
            output_type="plan",
        )
        def plan_copy_selected(command, channel, _, data_type=None, data=None, **kwgs):
            for c in elements.ops(emphasized=True):
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
            self.context.signal("plan", data.name, 1)
            return data_type, data

        @self.context.console_command(
            "copy",
            help=_("plan<?> copy"),
            input_type="plan",
            output_type="plan",
        )
        def plan_copy(command, channel, _, data_type=None, data=None, **kwgs):
            operations = elements.get(type="branch ops")
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
            self.context.signal("plan", data.name, 1)
            return data_type, data

        @self.context.console_option(
            "index", "i", type=int, help=_("index of location to insert command")
        )
        @self.context.console_option(
            "op", "o", type=str, help=_("unlock, origin, home, etc.")
        )
        @self.context.console_command(
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
                for command_name in self.context.match("plan/.*", suffix=True):
                    channel(command_name)
                return
            try:
                for command_name in self.context.match("plan/%s" % op):
                    cmd = self.context.registered[command_name]
                    if index is None:
                        data.plan.append(cmd)
                    else:
                        try:
                            data.plan.insert(index, cmd)
                        except ValueError:
                            channel(_("Invalid index for command insert."))
                    break
                self.context.signal("plan", data.name, None)
            except (KeyError, IndexError):
                channel(_("No plan command found."))
            return data_type, data

        @self.context.console_argument(
            "op", type=str, help=_("unlock, origin, home, etc")
        )
        @self.context.console_command(
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
                for command_name in self.context.match("plan/%s" % op):
                    plan_command = self.context.registered[command_name]
                    data.plan.append(plan_command)
                    self.context.signal("plan", data.name, None)
                    return data_type, data
            except (KeyError, IndexError):
                pass
            channel(_("No plan command found."))
            return data_type, data

        @self.context.console_argument(
            "op", type=str, help=_("unlock, origin, home, etc")
        )
        @self.context.console_command(
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
            try:
                for command_name in self.context.match("plan/%s" % op):
                    plan_command = self.context.registered[command_name]
                    data.plan.insert(0, plan_command)
                    break
                self.context.signal("plan", data.name, None)
            except (KeyError, IndexError):
                channel(_("No plan command found."))
            return data_type, data

        @self.context.console_command(
            "preprocess",
            help=_("plan<?> preprocess"),
            input_type="plan",
            output_type="plan",
        )
        def plan_preprocess(command, channel, _, data_type=None, data=None, **kwgs):
            data.preprocess()
            self.context.signal("plan", data.name, 2)
            return data_type, data

        @self.context.console_command(
            "validate",
            help=_("plan<?> validate"),
            input_type="plan",
            output_type="plan",
        )
        def plan_validate(command, channel, _, data_type=None, data=None, **kwgs):
            data.execute()
            self.context.signal("plan", data.name, 3)
            return data_type, data

        @self.context.console_command(
            "blob",
            help=_("plan<?> blob"),
            input_type="plan",
            output_type="plan",
        )
        def plan_blob(data_type=None, data=None, **kwgs):
            data.blob()
            self.context.signal("plan", data.name, 4)
            return data_type, data

        @self.context.console_command(
            "preopt",
            help=_("plan<?> preopt"),
            input_type="plan",
            output_type="plan",
        )
        def plan_preopt(data_type=None, data=None, **kwgs):
            data.preopt()
            self.context.signal("plan", data.name, 5)
            return data_type, data

        @self.context.console_command(
            "optimize",
            help=_("plan<?> optimize"),
            input_type="plan",
            output_type="plan",
        )
        def plan_optimize(data_type=None, data=None, **kwgs):
            data.execute()
            self.context.signal("plan", data.name, 6)
            return data_type, data

        @self.context.console_command(
            "clear",
            help=_("plan<?> clear"),
            input_type="plan",
            output_type="plan",
        )
        def plan_clear(data_type=None, data=None, **kwgs):
            data.clear()
            self.context.signal("plan", data.name, 0)
            return data_type, data

        @self.context.console_argument("cols", type=int, help=_("columns for the grid"))
        @self.context.console_argument("rows", type=int, help=_("rows for the grid"))
        @self.context.console_argument(
            "x_distance", type=Length, help=_("x_distance each column step")
        )
        @self.context.console_argument(
            "y_distance", type=Length, help=_("y_distance each row step")
        )
        @self.context.console_command(
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
                (self.context.prephysicalhome, physicalhome),
                (self.context.prehome, home),
            )
            # Following must be in reverse order as added in preprocess()
            post_plan_items = (
                (self.context.autointerrupt, interrupt),
                (self.context.autobeep, beep),
                (self.context.postunlock, unlock),
                (self.context.autoorigin, origin),
                (self.context.autophysicalhome, physicalhome),
                (self.context.autohome, home),
            )
            post_plan = []

            c_plan = list(data.plan)
            data.plan.clear()
            data.commands.clear()
            for cmd, func in pre_plan_items:
                if (cmd and c_plan[0] is func):
                    data.plan.append(c_plan.pop(0))
                elif type(c_plan[0]) == str:  # Rotary disabled
                    data.plan.append(c_plan.pop(0))

            for cmd, func in post_plan_items:
                if (cmd and c_plan[-1] is func):
                    post_plan.insert(0, c_plan.pop())
                elif type(c_plan[-1]) == str:  # Rotary disabled
                    post_plan.insert(0, c_plan.pop())

            try:
                if x_distance is None:
                    x_distance = Length("%f%%" % (100.0 / (cols + 1)))
                if y_distance is None:
                    y_distance = Length("%f%%" % (100.0 / (rows + 1)))
            except Exception:
                pass
            x_distance = x_distance.value(
                ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM
            )
            y_distance = y_distance.value(
                ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM
            )
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
            self.context.signal("plan", data.name, None)
            return data_type, data

        @self.context.console_command(
            "return",
            help=_("plan<?> return"),
            input_type="plan",
            output_type="plan",
        )
        def plan_return(command, channel, _, data_type=None, data=None, **kwgs):
            operations = elements.get(type="branch ops")
            operations.remove_all_children()

            for c in data.plan:
                if isinstance(c, CutCode):
                    operations.add(c, type="cutcode")
                if isinstance(c, LaserOperation):
                    copy_c = copy(c)
                    operations.add(copy_c, type="op")
            channel(_("Returned Operations."))
            self.context.signal("plan", data.name, None)
            return data_type, data

        @self.context.console_argument(
            "start", help="start index for cutcode", type=int, default=0
        )
        @self.context.console_argument(
            "end", help="end index for cutcode (-1 is last value)", type=int, default=-1
        )
        @self.context.console_command(
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

            self.context.signal("plan", data.name, None)
            return data_type, data

    def plan(self, **kwargs):
        for item in self._plan:
            yield item


def origin():
    yield COMMAND_MODE_RAPID
    yield COMMAND_SET_ABSOLUTE
    yield COMMAND_MOVE, 0, 0


def unlock():
    yield COMMAND_MODE_RAPID
    yield COMMAND_UNLOCK


def home():
    yield COMMAND_HOME


def physicalhome():
    yield COMMAND_WAIT_FINISH
    yield COMMAND_HOME, 0, 0


def offset(x, y):
    def offset_value():
        yield COMMAND_WAIT_FINISH
        yield COMMAND_SET_POSITION, -int(x), -int(y)

    return offset_value


def wait():
    wait_amount = 5.0
    yield COMMAND_WAIT_FINISH
    yield COMMAND_WAIT, wait_amount


def beep():
    yield COMMAND_WAIT_FINISH
    yield COMMAND_BEEP


def interrupt_text():
    input("Interrupted: press enter to continue...\n")
    print("... continuing")


def interrupt():
    yield COMMAND_WAIT_FINISH
    yield COMMAND_FUNCTION, interrupt_text


def reify_matrix(self):
    """Apply the matrix to the path and reset matrix."""
    self.element = abs(self.element)
    self.scene_bounds = None

def correct_empty(context: CutGroup):
    """
    Iterate backwards deleting any entries that are empty.
    """
    for index in range(len(context) - 1, -1, -1):
        c = context[index]
        if isinstance(c, CutGroup):
            correct_empty(c)
        if c.inside:
            for o in c.inside:
                if o.contains and c in o.contains:
                    o.contains.remove(c)
        del context[index]
