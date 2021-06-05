from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Inputs", Inputs)
        kernel.register("input/file", FileInput)
        kernel.register("input/tcp", TcpInput)

    elif lifecycle == "boot":
        kernel_root = kernel.root
        kernel_root.activate("modifier/Inputs")


class Input:
    def __init__(self):
        self.output = None
        self.input = None
        self.next = None
        self.prev = None


class FileInput(Input):
    def __init__(self):
        super().__init__()


class TcpInput(Input):
    def __init__(self):
        super().__init__()


class Inputs(Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self._inputs = dict()
        self._default_input = "0"

    def get_input(self, input_name, **kwargs):
        try:
            return self._inputs[input_name]
        except KeyError:
            pass
        return None

    def make_input(self, input_name, input_type, **kwargs):
        try:
            return self._inputs[input_name]
        except KeyError:
            try:
                for pname in self.context.match("input/%s" % input_type):
                    input_class = self.context.registered[pname]
                    input = input_class(self.context, input_name, **kwargs)
                    self._inputs[input_name] = input, input_name
                    return input, input_name
            except (KeyError, IndexError):
                pass
        return None

    def default_input(self):
        return self.get_input(self._default_input)

    def attach(self, *a, **kwargs):
        context = self.context
        context.inputs = self
        context.default_input = self.default_input

        kernel = self.context._kernel
        _ = kernel.translation

        @context.console_option("new", "n", type=str, help=_("new input type"))
        @context.console_command(
            "input",
            help=_("input<?> <command>"),
            regex=True,
            input_type=None,
            output_type="input",
        )
        def input(
            command,
            channel,
            _,
            data=None,
            data_type=None,
            new=None,
            remainder=None,
            **kwargs
        ):
            if len(command) > 6:
                self._default_input = command[6:]
                self.context.signal("input", self._default_input, None)
            if new is not None and self._default_input in self._inputs:
                for i in range(1000):
                    if str(i) in self._inputs:
                        continue
                    self.default_input = str(i)
                    break

            if new is not None:
                input_data = self.make_input(self._default_input, new)
            else:
                input_data = self.get_input(self._default_input)

            if input_data is None:
                raise SyntaxError("No input")

            input, input_name = input_data
            self.context.signal("input", input_name, 1)

            if data is not None:
                if data_type == "driver":
                    dinter, dname = data
                    dinter.output = input
                    input.next = dinter
                elif data_type == "input":
                    dinput, dname = data
                    dinput.output = input
            elif remainder is None:
                input, input_name = input_data
                channel(_("----------"))
                channel(_("Input:"))
                for i, pname in enumerate(self._inputs):
                    channel("%d: %s" % (i, pname))
                channel(_("----------"))
                channel(_("Input %s: %s" % (input_name, str(input))))
                channel(_("----------"))

            return "input", input_data

        @self.context.console_command(
            "list",
            help=_("input<?> list, list current inputs"),
            input_type="input",
            output_type="input",
        )
        def input(command, channel, _, data_type=None, data=None, **kwargs):
            input, input_name = data
            channel(_("----------"))
            channel(_("Input:"))
            for i, pname in enumerate(self._inputs):
                channel("%d: %s" % (i, pname))
            channel(_("----------"))
            channel(_("Input %s: %s" % (input_name, str(input))))
            channel(_("----------"))
            return data_type, data

        @context.console_command("type", help=_("list input types"), input_type="input")
        def list_type(channel, _, **kwargs):
            channel(_("----------"))
            channel(_("Input types:"))
            for i, name in enumerate(context.match("input/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))
