from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Interpreters", Interpreters)
    elif lifecycle == "boot":
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Interpreters")


class Interpreters(Modifier):

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._interpreters = dict()
        self._default_interpreter = "0"

    def get_or_make_interpreter(self, interpreter_name):
        try:
            return self._interpreters[interpreter_name]
        except KeyError:
            self._interpreters[interpreter_name] = list(), list(), list(), interpreter_name
            return self._interpreters[interpreter_name]

    def default_interpreter(self):
        return self.get_or_make_interpreter(self._default_interpreter)

    def attach(self, *a, **kwargs):
        context = self.context
        context.interpreters = self
        context.default_interpreter = self.default_interpreter

        kernel = self.context._kernel
        _ = kernel.translation

        @self.context.console_command(
            "interpret",
            help="interpret<?> <command>",
            regex=True,
            input_type=(None, "spooler"),
            output_type="interpret",
        )
        def interpret(command, channel, _, data=None, remainder=None, **kwargs):
            if len(command) > 9:
                self._default_interpreter = command[9:]
                self.context.signal("interpreter", self._default_interpreter, None)

            if data is not None:
                # If ops data is in data, then we copy that and move on to next step.
                spooler, spooler_name = data
                interpreter, name = self.get_or_make_interpreter(self._default_interpreter)
                try:
                    interpreter.set_spooler(spooler)
                except AttributeError:
                    pass
                return "interpreter", interpreter, name

            data = self.get_or_make_interpreter(self._default_interpreter)
            if remainder is None:
                interpreter, name = data
                channel(_("----------"))
                channel(_("Interpreter:"))
                for i, inter in enumerate(self._interpreters):
                    channel("%d: %s" % (i, inter))
                channel(_("----------"))
                channel(_("Interpreter %s:" % name))
                channel(str(interpreter))
                channel(_("----------"))
            return "plan", data

        @self.context.console_command(
            "list",
            help="intepret<?> list",
            input_type="interpret",
            output_type="interpret",
        )
        def interpret_list(command, channel, _, data_type=None, data=None, **kwargs):
            interpreter, name = data
            channel(_("----------"))
            channel(_("Interpreter:"))
            for i, inter in enumerate(self._interpreters):
                channel("%d: %s" % (i, inter))
            channel(_("----------"))
            channel(_("Interpreter %s:" % name))
            channel(str(interpreter))
            channel(_("----------"))
            return data_type, data

        @self.context.console_command(
            "reset",
            help="interpret<?> reset",
            input_type="interpret",
            output_type="interpret",
        )
        def interpreter_reset(command, channel, _, data_type=None, data=None, **kwargs):
            interpreter, name = data
            interpreter.reset()
            return data_type, data
