from copy import copy
from math import ceil

from ..core.cutcode import CutCode, CutObject, CutGroup
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
from ..svgelements import Group, Length, Polygon, SVGElement, SVGImage, SVGText
from ..tools.pathtools import VectorMontonizer
from .elements import LaserOperation

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


class CutPlan:
    """
    Cut Plan is a centralized class to modify plans with specific methods.
    """

    def __init__(self, name, context):
        self.name = name
        self.context = context
        self.plan = list()
        self.original = list()
        self.commands = list()

    def execute(self):
        # Using copy of commands, so commands can add ops.
        cmds = self.commands[:]
        self.commands.clear()
        for cmd in cmds:
            cmd()

    def blob(self):
        context = self.context
        blob_plan = list()
        for i in range(len(self.plan)):
            c = self.plan[i]
            try:
                if c.operation == "Dots":
                    blob_plan.append(c)
                    continue
                for p in range(c.settings.implicit_passes):
                    cutcode = CutCode(
                        c.as_cutobjects(closed_distance=context.opt_closed_distance)
                    )
                    cutcode.constrained = c.operation == "Cut" and context.opt_inner_first
                    cutcode.pass_index = p
                    cutcode.original_op = c.operation
                    if len(cutcode):
                        blob_plan.append(cutcode)
            except AttributeError:
                blob_plan.append(c)
        self.plan.clear()

        for i in range(len(blob_plan)):
            c = blob_plan[i]
            try:
                c.settings.jog_distance = context.opt_jog_minimum
                c.settings.jog_enable = context.opt_rapid_between
            except AttributeError:
                pass
            merge = (
                len(self.plan)
                and isinstance(self.plan[-1], CutCode)
                and isinstance(blob_plan[i], CutObject)
            )
            if (
                merge
                and not context.opt_merge_passes
                and self.plan[-1].pass_index != c.pass_index
            ):
                merge = False
            if (
                merge
                and not context.opt_merge_ops
                and self.plan[-1].original_op != c.original_op
            ):
                merge = False
            if (
                merge
                and not context.opt_inner_first
                and self.plan[-1].original_op == "Cut"
            ):
                merge = False

            if merge:
                if blob_plan[i].constrained:
                    self.plan[-1].constrained = True
                self.plan[-1].extend(blob_plan[i])
            else:
                if isinstance(c, CutObject) and not isinstance(c, CutCode):
                    cc = CutCode([c])
                    cc.original_op = c.original_op
                    cc.pass_index = c.pass_index
                    self.plan.append(cc)
                else:
                    self.plan.append(c)

    def optimize_cuts(self):
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                if c.constrained:
                    self.plan[i] = inner_first_cutcode(c)
                self.plan[i] = inner_selection_cutcode(c)

    def optimize_travel(self):
        last = None
        for i, c in enumerate(self.plan):
            if isinstance(c, CutCode):
                if c.constrained:
                    self.plan[i] = inner_first_cutcode(c)
                    c = self.plan[i]
                if last is not None:
                    self.plan[i].start = last
                self.plan[i] = short_travel_cutcode(c)
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
        reverse = self.context.classify_reverse
        if reverse:
            subitems = list(reversed(subitems))
        make_raster = self.context.registered.get("render-op/make_raster")
        objs = [s.object for s in subitems]
        bounds = Group.union_bbox(objs)
        if bounds is None:
            return None
        xmin, ymin, xmax, ymax = bounds
        image = make_raster(subitems, bounds, step=op.settings.raster_step)
        image_element = SVGImage(image=image)
        image_element.transform.post_translate(xmin, ymin)
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
                        """
                        TODO: Solve this is a less kludgy manner. The call to make the image can fail the first
                            time around because the renderer is what sets the size of the text. If the size hasn't
                            already been set, the initial bounds are wrong.
                        """
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

    def scale_for_rotary(self):
        r = self.context.get_context("rotary/1")
        spooler, input_driver, output = self.context.registered[
            "device/%s" % self.context.root.active
        ]
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
                    if len(op.children) == 1 and isinstance(op.children[0], SVGImage):
                        continue  # make raster not needed since its a single real raster.
                    make_raster = self.context.registered.get("render-op/make_raster")

                    if make_raster is None:
                        self.commands.append(self.strip_rasters)
                    else:
                        self.commands.append(self.make_image)
                    return True
            except AttributeError:
                pass
        return False

    def conditional_jobadd_optimize_travel(self):
        self.commands.append(self.optimize_travel)

    def conditional_jobadd_optimize_cuts(self):
        for op in self.plan:
            try:
                if op.operation == "CutCode":
                    self.commands.append(self.optimize_cuts)
                    return
            except AttributeError:
                pass

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
        self.context.setting(bool, "prehome", False)
        self.context.setting(bool, "prephysicalhome", False)
        self.context.setting(bool, "postunlock", False)
        self.context.setting(bool, "autohome", False)
        self.context.setting(bool, "autophysicalhome", False)
        self.context.setting(bool, "autoorigin", False)
        self.context.setting(bool, "autobeep", True)
        self.context.setting(bool, "autointerrupt", False)
        self.context.setting(int, "opt_closed_distance", 15)
        self.context.setting(bool, "opt_merge_passes", False)
        self.context.setting(bool, "opt_merge_ops", False)
        self.context.setting(bool, "opt_reduce_travel", True)
        self.context.setting(bool, "opt_inner_first", True)
        self.context.setting(bool, "opt_reduce_directions", False)
        self.context.setting(bool, "opt_remove_overlap", False)
        self.context.setting(bool, "opt_reduce_directions", False)
        self.context.setting(bool, "opt_start_from_position", False)
        self.context.setting(bool, "opt_rapid_between", False)
        self.context.setting(int, "opt_jog_minimum", 256)
        self.context.setting(int, "opt_jog_mode", 0)

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

            if data is not None:
                # If ops data is in data, then we copy that and move on to next step.
                cutplan = self.get_or_make_plan(self._default_plan)
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

            data = self.get_or_make_plan(self._default_plan)
            if remainder is None:
                plan, original, commands, name = data
                channel(_("----------"))
                channel(_("Plan:"))
                for i, plan_name in enumerate(self._plan):
                    channel("%d: %s" % (i, plan_name))
                channel(_("----------"))
                channel(_("Plan %s:" % self._default_plan))
                for i, op_name in enumerate(plan):
                    channel("%d: %s" % (i, op_name))
                channel(_("Commands %s:" % self._default_plan))
                for i, cmd_name in enumerate(commands):
                    channel("%d: %s" % (i, cmd_name))
                channel(_("----------"))

            return "plan", data

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
            channel(_("Plan %s:" % self._default_plan))
            for i, op_name in enumerate(data.plan):
                channel("%d: %s" % (i, op_name))
            channel(_("Commands %s:" % self._default_plan))
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
            self.context.signal("plan", self._default_plan, 1)
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
                types=("op", "cutcode", "cmdop", "lasercode", "blob"), depth=1
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
            self.context.signal("plan", self._default_plan, 1)
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
                self.context.signal("plan", self._default_plan, None)
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
                    self.context.signal("plan", self._default_plan, None)
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
                self.context.signal("plan", self._default_plan, None)
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
            rotary_context = self.context.get_context("rotary/1")
            if self.context.prephysicalhome:
                if not rotary_context.rotary:
                    data.plan.insert(0, self.context.registered["plan/physicalhome"])
                else:
                    data.plan.insert(0, _("Physical Home Before: Disabled (Rotary On)"))
            if self.context.prehome:
                if not rotary_context.rotary:
                    data.plan.insert(0, self.context.registered["plan/home"])
                else:
                    data.plan.insert(0, _("Home Before: Disabled (Rotary On)"))
            # ==========
            # BEFORE/AFTER
            # ==========
            if self.context.autohome:
                if not rotary_context.rotary:
                    data.plan.append(self.context.registered["plan/home"])
                else:
                    data.plan.append(_("Home After: Disabled (Rotary On)"))
            if self.context.autophysicalhome:
                if not rotary_context.rotary:
                    data.plan.append(self.context.registered["plan/physicalhome"])
                else:
                    data.plan.append(_("Physical Home After: Disabled (Rotary On)"))
            if self.context.autoorigin:
                data.plan.append(self.context.registered["plan/origin"])
            if self.context.postunlock:
                data.plan.append(self.context.registered["plan/unlock"])
            if self.context.autobeep:
                data.plan.append(self.context.registered["plan/beep"])
            if self.context.autointerrupt:
                data.plan.append(self.context.registered["plan/interrupt"])

            # ==========
            # Conditional Ops
            # ==========
            data.conditional_jobadd_strip_text()
            if rotary_context.rotary:
                data.conditional_jobadd_scale_rotary()
            data.conditional_jobadd_actualize_image()
            data.conditional_jobadd_make_raster()
            self.context.signal("plan", self._default_plan, 2)
            return data_type, data

        @self.context.console_command(
            "validate",
            help=_("plan<?> validate"),
            input_type="plan",
            output_type="plan",
        )
        def plan_validate(command, channel, _, data_type=None, data=None, **kwgs):
            data.execute()
            self.context.signal("plan", self._default_plan, 3)
            return data_type, data

        @self.context.console_command(
            "blob",
            help=_("plan<?> blob"),
            input_type="plan",
            output_type="plan",
        )
        def plan_blob(data_type=None, data=None, **kwgs):
            data.blob()
            self.context.signal("plan", self._default_plan, 4)
            return data_type, data

        @self.context.console_command(
            "preopt",
            help=_("plan<?> preopt"),
            input_type="plan",
            output_type="plan",
        )
        def plan_preopt(data_type=None, data=None, **kwgs):
            if self.context.opt_reduce_travel:
                data.conditional_jobadd_optimize_travel()
            elif self.context.opt_inner_first:
                data.conditional_jobadd_optimize_cuts()
            if self.context.opt_reduce_directions:
                pass
            if self.context.opt_remove_overlap:
                pass
            self.context.signal("plan", self._default_plan, 5)
            return data_type, data

        @self.context.console_command(
            "optimize",
            help=_("plan<?> optimize"),
            input_type="plan",
            output_type="plan",
        )
        def plan_optimize(data_type=None, data=None, **kwgs):
            data.execute()
            self.context.signal("plan", self._default_plan, 6)
            return data_type, data

        @self.context.console_command(
            "clear",
            help=_("plan<?> clear"),
            input_type="plan",
            output_type="plan",
        )
        def plan_clear(data_type=None, data=None, **kwgs):
            data.clear()
            self.context.signal("plan", self._default_plan, 0)
            return data_type, data

        @self.context.console_option(
            "op", "o", type=str, help=_("unlock, origin, home")
        )
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
            data.plan.clear()
            data.commands.clear()
            x_distance = x_distance.value(ppi=1000.0, relative_length=bed_dim.bed_width * MILS_IN_MM)
            y_distance = x_distance.value(ppi=1000.0, relative_length=bed_dim.bed_height * MILS_IN_MM)
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

                    data.plan.extend(list(data.original))
                    x_last = x_pos
                    y_last = y_pos
                    x_pos += x_distance
                y_pos += y_distance
            if x_pos != 0 or y_pos != 0:
                data.plan.append(offset(-x_pos, -y_pos))
            self.context.signal("plan", self._default_plan, None)
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
            self.context.signal("plan", self._default_plan, None)
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
    from PIL import Image

    pil_image = image_element.image
    image_element.cache = None
    matrix = image_element.transform
    bbox = Group.union_bbox([image_element])
    element_width = int(ceil(bbox[2] - bbox[0]))
    element_height = int(ceil(bbox[3] - bbox[1]))
    if step_level is None:
        # If we are not told the step amount either draw it from the object or set it to default.
        if "raster_step" in image_element.values:
            step_level = float(image_element.values["raster_step"])
        else:
            step_level = 1.0
    step_scale = 1 / float(step_level)
    tx = bbox[0]
    ty = bbox[1]
    matrix.post_translate(-tx, -ty)
    matrix.post_scale(
        step_scale, step_scale
    )  # step level requires the actual image be scaled down.
    try:
        matrix.inverse()
    except ZeroDivisionError:
        # Rare crash if matrix is malformed and cannot invert.
        matrix.reset()
        matrix.post_translate(-tx, -ty)
        matrix.post_scale(step_scale, step_scale)
    if (
        matrix.value_skew_y() != 0.0 or matrix.value_skew_y() != 0.0
    ) and pil_image.mode != "RGBA":
        # If we are rotating an image without alpha, we need to convert it, or the rotation invents black pixels.
        pil_image = pil_image.convert("RGBA")

    pil_image = pil_image.transform(
        (element_width, element_height),
        Image.AFFINE,
        (matrix.a, matrix.c, matrix.e, matrix.b, matrix.d, matrix.f),
        resample=Image.BICUBIC,
    )
    image_element.image_width, image_element.image_height = (
        element_width,
        element_height,
    )
    matrix.reset()

    box = pil_image.getbbox()
    if box is None:
        matrix.post_scale(step_level, step_level)
        matrix.post_translate(tx, ty)
        image_element.image = pil_image
        return
    width = box[2] - box[0]
    height = box[3] - box[1]
    if width != element_width and height != element_height:
        image_element.image_width, image_element.image_height = (width, height)
        pil_image = pil_image.crop(box)
        matrix.post_translate(box[0], box[1])
    # step level requires the new actualized matrix be scaled up.
    matrix.post_scale(step_level, step_level)
    matrix.post_translate(tx, ty)
    image_element.image = pil_image


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
    input("waiting for user...")


def interrupt():
    yield COMMAND_WAIT_FINISH
    yield COMMAND_FUNCTION, interrupt_text


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


def is_inside(inner_path, outer_path):
    """
    Test that path1 is inside path2.
    :param inner_path: inner path
    :param outer_path: outer path
    :return: whether path1 is wholly inside path2.
    """
    if hasattr(inner_path, "path") and inner_path.path is not None:
        inner_path = inner_path.path
    if hasattr(outer_path, "path") and outer_path.path is not None:
        outer_path = outer_path.path
    if not hasattr(inner_path, "bounding_box"):
        inner_path.bounding_box = Group.union_bbox([inner_path])
    if not hasattr(outer_path, "bounding_box"):
        outer_path.bounding_box = Group.union_bbox([outer_path])
    if outer_path.bounding_box is None:
        return False
    if inner_path.bounding_box is None:
        return False
    if outer_path.bounding_box[0] > inner_path.bounding_box[0]:
        # outer minx > inner minx (is not contained)
        return False
    if outer_path.bounding_box[1] > inner_path.bounding_box[1]:
        # outer miny > inner miny (is not contained)
        return False
    if outer_path.bounding_box[2] < inner_path.bounding_box[2]:
        # outer maxx < inner maxx (is not contained)
        return False
    if outer_path.bounding_box[3] < inner_path.bounding_box[3]:
        # outer maxy < inner maxy (is not contained)
        return False
    if outer_path.bounding_box == inner_path.bounding_box:
        if outer_path == inner_path:  # This is the same object.
            return False
    if not hasattr(outer_path, "vm"):
        outer_path = Polygon(
            [outer_path.point(i / 100.0, error=1e4) for i in range(101)]
        )
        vm = VectorMontonizer()
        vm.add_cluster(outer_path)
        outer_path.vm = vm
    for i in range(101):
        p = inner_path.point(i / 100.0, error=1e4)
        if not outer_path.vm.is_point_inside(p.x, p.y):
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


def extract_closed_groups(context: CutGroup):
    """
    yields all closed groups within the current cutcode.
    Removing those groups from this cutcode.
    """
    try:
        index = len(context) - 1
    except TypeError:
        index = -1
    while index != -1:
        c = context[index]
        if isinstance(c, CutGroup):
            if c.closed:
                del context[index]
                yield c
            index -= 1
            continue
        for s in extract_closed_groups(c):
            yield s
        index -= 1


def inner_first_cutcode(context: CutGroup):
    """
    Extract all closed groups and place them at the start of the cutcode.
    Place all cuts that are not closed groups after these extracted elements.
    Brute force each object to see if it is located within another object.

    Creates .inside and .contains lists for all cut objects with regard to whether
    they are inside or contain the other object.
    """
    ordered = CutCode()
    closed_groups = list(extract_closed_groups(context))
    if len(closed_groups):
        ordered.contains = closed_groups
        ordered.extend(closed_groups)
    ordered.extend(context.flat())
    context.clear()
    for oj in ordered:
        for ok in ordered:
            if oj is ok:
                continue
            if is_inside(ok, oj):
                if ok.inside is None:
                    ok.inside = list()
                if oj.contains is None:
                    oj.contains = list()
                ok.inside.append(oj)
                oj.contains.append(ok)
    # for j, c in enumerate(ordered):
    #     if c.contains is not None:
    #         for k, q in enumerate(c.contains):
    #             assert q in ordered
    #             assert q is not c
    #     if c.inside is not None:
    #         for m, q in enumerate(c.inside):
    #             assert q in ordered
    #             assert q is not c

    ordered.constrained = True
    return ordered


def short_travel_cutcode(context: CutCode):
    """
    Selects cutcode from candidate cutcode permitted, optimizing with greedy/brute for
    shortest distances optimizations.

    For paths starting at exactly the same point forward paths are prefered over reverse paths
    and within this shorter paths are prefered over longer ones.

    We start at either 0,0 or the value given in cc.start
    """
    curr = context.start
    if curr is None:
        curr = 0
    else:
        curr = complex(curr[0], curr[1])
    for c in context.flat():
        c.permitted = True
    ordered = CutCode()
    while True:
        closest = None
        backwards = False
        closest_length = distance = float("inf")
        for cut in context.candidate():
            s = cut.start()
            s = complex(s[0], s[1])
            d = abs(s - curr)
            l = cut.length()
            if (d < distance
                or (
                    d == distance
                    and (
                        backwards
                        or l < closest_length
                    )
                )
            ):
                distance = d
                backwards = False
                closest = cut
                closest_length = l
            if cut.reversible():
                e = cut.end()
                e = complex(e[0], e[1])
                d = abs(e - curr)
                if (d < distance
                    or (
                        d == distance
                        and backwards
                        and l < closest_length
                    )
                ):
                    distance = d
                    backwards = True
                    closest = cut
                    closest_length = l
        if closest is None:
            break
        closest.permitted = False
        c = copy(closest)
        if backwards:
            c.reverse()
        end = c.end()
        curr = complex(end[0], end[1])
        ordered.append(c)
    return ordered


def inner_selection_cutcode(context: CutCode):
    """
    Selects cutcode from candidate cutcode permitted but does nothing to optimize byond
    finding a valid solution.
    """
    for c in context.flat():
        c.permitted = True
    ordered = CutCode()
    while True:
        c = list(context.candidate())
        if len(c) == 0:
            break
        ordered.extend(c)
        for o in ordered.flat():
            o.permitted = False
    return ordered
