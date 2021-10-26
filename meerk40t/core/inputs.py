from ..kernel import Modifier


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_modifier(Inputs)
        kernel.register("input/file", FileInput)
        kernel.register("input/tcp", TcpInput)


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
    def __init__(self, kernel, name=None, *args, **kwargs):
        Modifier.__init__(self, kernel, "inputs")
        self._inputs = dict()

        _ = kernel.translation

        @kernel.console_option("new", "n", type=str, help=_("new input type"))
        @kernel.console_command(
            "input",
            help=_("input<?> <command>"),
            regex=True,
            input_type=None,
            output_type="input",
        )
        def input_base(
            command,
            channel,
            _,
            data=None,
            data_type=None,
            new=None,
            remainder=None,
            **kwgs
        ):
            if len(command) > 6:
                self._default_input = command[6:]
                self.signal("input", self._default_input, None)
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

            input_obj, input_name = input_data
            self.signal("input", input_name, 1)

            if data is not None:
                if data_type == "driver":
                    dinter, dname = data
                    dinter.output = input_obj
                    input_obj.next = dinter
                elif data_type == "input":
                    dinput, dname = data
                    dinput.output = input_obj
            elif remainder is None:
                input_obj, input_name = input_data
                channel(_("----------"))
                channel(_("Input:"))
                for i, pname in enumerate(self._inputs):
                    channel("%d: %s" % (i, pname))
                channel(_("----------"))
                channel(_("Input %s: %s" % (input_name, str(input_obj))))
                channel(_("----------"))

            return "input", input_data

        @kernel.console_command(
            "list",
            help=_("input<?> list, list current inputs"),
            input_type="input",
            output_type="input",
        )
        def input_list(command, channel, _, data_type=None, data=None, **kwgs):
            input_obj, input_name = data
            channel(_("----------"))
            channel(_("Input:"))
            for i, pname in enumerate(self._inputs):
                channel("%d: %s" % (i, pname))
            channel(_("----------"))
            channel(_("Input %s: %s" % (input_name, str(input_obj))))
            channel(_("----------"))
            return data_type, data

        @kernel.console_command("type", help=_("list input types"), input_type="input")
        def list_type(channel, _, **kwgs):
            channel(_("----------"))
            channel(_("Input types:"))
            for i, name in enumerate(self.match("input/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))

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
                for pname in self.match("input/%s" % input_type):
                    input_class = self.registered[pname]
                    input_obj = input_class(self, input_name, **kwargs)
                    self._inputs[input_name] = input_obj, input_name
                    return input_obj, input_name
            except (KeyError, IndexError):
                pass
        return None

    def default_input(self):
        return self.get_input(self.active.name)