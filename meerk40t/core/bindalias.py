from ..kernel import CommandMatchRejected, Service

# The following dicts consist of a tuple of values, the first of
# which is the current default, with any prior defaults following.
# Prior defaults are used to keep a users keymap / aliases up to date with
# any changes, unless the user has already changed away from the default.
# If you want to delete a bind / alias, set the first value to a null string.

DEFAULT_KEYMAP = {
    "escape": ("pause",),
    "pause": ("pause",),
    "d": ("+right",),
    "a": ("+left",),
    "w": ("+up",),
    "s": ("+down",),
    "l": ("lock",),
    "u": ("unlock",),
    "numpad_down": ("+translate_down",),
    "numpad_up": ("+translate_up",),
    "numpad_left": ("+translate_left",),
    "numpad_right": ("+translate_right",),
    "numpad_multiply": ("+scale_up",),
    "numpad_divide": ("+scale_down",),
    "numpad_add": ("+rotate_cw",),
    "numpad_subtract": ("+rotate_ccw",),
    "control+a": ("element* select",),
    "control+c": ("clipboard copy",),
    "control+v": ("clipboard paste",),
    "control+x": ("clipboard cut",),
    "control+i": ("element* select^",),
    "control+f": ("", "dialog_fill", "control Fill",),
    "control+s": ("", "dialog_stroke", "control Stroke",),
    "alt+f": ("dialog_fill",),
    "alt+p": ("dialog_flip",),
    "alt+s": ("dialog_stroke",),
    "alt+h": ("dialog_path",),
    "alt+t": ("dialog_transform",),
    "control+r": ("rect 0 0 1000 1000",),
    "control+e": ("circle 500 500 500",),
    "control+d": ("element copy",),
    "control+o": ("outline",),
    "control+b": ("align bedcenter",)
    "control+shift+o": ("outline 1mm",),
    "control+alt+o": ("outline -1mm",),
    "control+shift+h": ("scale -1 1",),
    "control+shift+v": ("scale 1 -1",),
    "control+1": ("bind 1 move $x $y",),
    "control+2": ("bind 2 move $x $y",),
    "control+3": ("bind 3 move $x $y",),
    "control+4": ("bind 4 move $x $y",),
    "control+5": ("bind 5 move $x $y",),
    "alt+r": ("raster",),
    "alt+e": ("engrave",),
    "alt+c": ("cut",),
    "delete": ("tree selected delete", "element delete",),
    "control+f3": ("", "rotaryview",),
    "alt+f3": ("", "rotaryscale",),
    "f4": ("", "window open CameraInterface",),
    "f5": ("refresh",),
    "f6": ("", "window open JobSpooler",),
    "f7": ("", "window open -o Controller", "window controller", "window open Controller",),
    "f8": ("", "dialog_path", "control Path"),
    "f9": ("", "dialog_transform", "control Transform",),
    "control+f9": ("", "dialog_flip", "control Flip",),
    "f12": ("", "window open Console", "window open Terminal",),
    "control+alt+g": ("image wizard Gold",),
    "control+alt+x": ("image wizard Xin",),
    "control+alt+s": ("image wizard Stipo",),
    "home": ("home",),
    "control+z": ("reset",),
    "control+alt+shift+escape": ("reset_bind_alias",),
}
DEFAULT_ALIAS = {
    "+scale_up": ("loop scale 1.02",),
    "+scale_down": ("loop scale 0.98",),
    "+rotate_cw": ("loop rotate 2",),
    "+rotate_ccw": ("loop rotate -2",),
    "+translate_right": ("loop translate 1mm 0",),
    "+translate_left": ("loop translate -1mm 0",),
    "+translate_down": ("loop translate 0 1mm",),
    "+translate_up": ("loop translate 0 -1mm",),
    "+right": ("loop right 1mm",),
    "+left": ("loop left 1mm",),
    "+up": ("loop up 1mm",),
    "+down": ("loop down 1mm",),
    "-scale_up": ("end scale 1.02",),
    "-scale_down": ("end scale 0.98",),
    "-rotate_cw": ("end rotate 2",),
    "-rotate_ccw": ("end rotate -2",),
    "-translate_right": ("end translate 1mm 0",),
    "-translate_left": ("end translate -1mm 0",),
    "-translate_down": ("end translate 0 1mm",),
    "-translate_up": ("end translate 0 -1mm",),
    "-right": ("end right 1mm",),
    "-left": ("end left 1mm",),
    "-up": ("end up 1mm",),
    "-down": ("end down 1mm",),
    "terminal_ruida": ("", "window open Terminal;ruidaserver",),
    "terminal_watch": (
        "",
        "window open Terminal;channel save usb;channel save send;channel save recv",
    ),
    "reset_bind_alias": ("bind default;alias default",),
}



def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.add_service("bind", Bind(kernel))
        kernel.add_service("alias", Alias(kernel))


class Bind(Service):
    """
    Bind service, establishes keymap
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "keymap")
        self.keymap = {}
        self.triggered = dict()

        _ = self._

        @self.console_command("bind", help=_("bind <key> <console command>"))
        def bind(command, channel, _, args=tuple(), **kwgs):
            """
            Binds a key to a given keyboard keystroke.
            """
            if len(args) == 0:
                channel(_("----------"))
                channel(_("Binds:"))
                for i, key in enumerate(self.keymap):
                    value = self.keymap[key]
                    channel(_("%d: key %s %s") % (i, key.ljust(15), value))
                channel(_("----------"))
            else:
                key = args[0].lower()
                if key == "default":
                    self.keymap = dict()
                    self.default_keymap()
                    channel(_("Set default keymap."))
                    return
                command_line = " ".join(args[1:])
                f = command_line.find("bind")
                if f == -1:  # If bind value has a bind, do not evaluate.
                    if "$x" in command_line:
                        try:
                            x = self.device.current_x
                        except AttributeError:
                            x = 0
                        command_line = command_line.replace("$x", str(x))
                    if "$y" in command_line:
                        try:
                            y = self.device.current_y
                        except AttributeError:
                            y = 0
                        command_line = command_line.replace("$y", str(y))
                if len(command_line) != 0:
                    self.keymap[key] = command_line
                else:
                    try:
                        del self.keymap[key]
                        channel(_("Unbound %s") % key)
                    except KeyError:
                        pass
            return

        self.read_persistent_string_dict(self.keymap, suffix=True)
        if not len(self.keymap):
            self.default_keymap()

    def trigger(self, keyvalue):
        if keyvalue in self.keymap:
            if keyvalue not in self.triggered:
                self.triggered[keyvalue] = 1
                action = self.keymap[keyvalue]
                self(action + "\n")
                return True
        else:
            return False

    def untrigger(self, keyvalue):
        keymap = self.keymap
        if keyvalue in keymap:
            if keyvalue in self.triggered:
                del self.triggered[keyvalue]
            action = keymap[keyvalue]
            if action.startswith("+"):
                # Keyup commands only trigger if the down command started with +
                action = "-" + action[1:]
                self(action + "\n")
                return True
        else:
            return False

    def shutdown(self, *args, **kwargs):
        self.clear_persistent()

        for key, value in self.keymap.items():
            if key is None or len(key) == 0:
                continue
            self.write_persistent(key, value)

    def default_keymap(self):
        self.keymap.clear()
        for key, values in DEFAULT_KEYMAP.items():
            value = values[0]
            if value:
                self.keymap[key] = value


class Alias(Service):
    """
    Alias service, establishes command aliases
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "alias")
        self.aliases = {}
        _ = self._

        @self.console_argument("alias", type=str, help=_("alias command"))
        @self.console_command(
            "alias", help=_("alias <alias> <console commands[;console command]*>")
        )
        def alias(command, channel, _, alias=None, remainder=None, **kwgs):
            if alias is None:
                channel(_("----------"))
                channel(_("Aliases:"))
                for i, key in enumerate(self.aliases):
                    value = self.aliases[key]
                    channel("%d: %s %s" % (i, key.ljust(15), value))
                channel(_("----------"))
                return
            alias = alias.lower()
            if alias == "default":
                self.aliases = dict()
                self.default_alias()
                channel(_("Set default aliases."))
                return
            if remainder is None:
                if alias in self.aliases:
                    channel(_("Alias %s unset.") % alias)
                    del self.aliases[alias]
                else:
                    channel(_("No alias for %s was set.") % alias)
            else:
                self.aliases[alias] = remainder

        @self.console_command(".*", regex=True, hidden=True)
        def alias_execute(command, **kwgs):
            """
            Alias execution code. Checks values for matching alias and utilizes that.

            Aliases with ; delimit multipart commands
            """
            if command in self.aliases:
                aliased_command = self.aliases[command]
                for cmd in aliased_command.split(";"):
                    self("%s\n" % cmd)
            else:
                raise CommandMatchRejected(_("This is not an alias."))

        self.aliases.clear()
        self.read_persistent_string_dict(self.aliases, suffix=True)
        if not len(self.aliases):
            self.default_alias()

    def shutdown(self, *args, **kwargs):
        self.clear_persistent()
        for key in self.aliases:
            if key is None or len(key) == 0:
                continue
            self.write_persistent(key, self.aliases[key])

    def default_alias(self):
        self.aliases["+scale_up"] = "loop scale 1.02"
        self.aliases["+scale_down"] = "loop scale 0.98"
        self.aliases["+rotate_cw"] = "loop rotate 2"
        self.aliases["+rotate_ccw"] = "loop rotate -2"
        self.aliases["+translate_right"] = "loop translate 1mm 0"
        self.aliases["+translate_left"] = "loop translate -1mm 0"
        self.aliases["+translate_down"] = "loop translate 0 1mm"
        self.aliases["+translate_up"] = "loop translate 0 -1mm"
        self.aliases["+right"] = "loop right 1mm"
        self.aliases["+left"] = "loop left 1mm"
        self.aliases["+up"] = "loop up 1mm"
        self.aliases["+down"] = "loop down 1mm"
        self.aliases["-scale_up"] = "end scale 1.02"
        self.aliases["-scale_down"] = "end scale 0.98"
        self.aliases["-rotate_cw"] = "end rotate 2"
        self.aliases["-rotate_ccw"] = "end rotate -2"
        self.aliases["-translate_right"] = "end translate 1mm 0"
        self.aliases["-translate_left"] = "end translate -1mm 0"
        self.aliases["-translate_down"] = "end translate 0 1mm"
        self.aliases["-translate_up"] = "end translate 0 -1mm"
        self.aliases["-right"] = "end right 1mm"
        self.aliases["-left"] = "end left 1mm"
        self.aliases["-up"] = "end up 1mm"
        self.aliases["-down"] = "end down 1mm"
        self.aliases["reset_bind_alias"] = "bind default;alias default"
        self.context.alias.clear()
        for key, values in DEFAULT_ALIAS.items():
            value = values[0]
            if value:
                self.context.alias[key] = value
