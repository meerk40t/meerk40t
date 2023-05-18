from meerk40t.kernel import CommandMatchRejected, Service

"""
This core class defines two main services: bind and alias. This is a set defined keybinds and alias commands.

If a keybind commands starts with a "+" then the command is triggered on the down-key and the "-" version of
the same command is triggered on the up-key. If the bind is for any other command, it will execute on key-press.
If you need this functionality it's best to define these commands as aliases of other commands.
"""


"""
The following dicts consist of a tuple of values, the first of
which is the current default, with any prior defaults following.
Prior defaults are used to keep a users keymap / aliases up to date with
any changes, unless the user has already changed away from the default.
If you want to delete a bind / alias, set the first value to a null string.

CHOICE OF BINDALIAS vs. MENU
These key bindings are in addition to those specified in the menus
(like Ctrl+S for File Save). The choice of which of these to use is debatable.
On one hand bindalias is a more flexible approach because the user can
change keys mappings to whatever they wish whilst menus are fixed.
On the other hand, default menu keys can be set per language because the
menu strings are translated, whereas bindalias keys are not.

RESERVED KEYS
Regardless of the platform used by individual developers, bindalias needs
to conform to BOTH of the following:

1. Mac - common shortcuts defined in https://support.apple.com/en-us/HT201236
   should be followed where appropriate and avoided if not. This is important
   for MK to be accepted into the Apple app store.
   Where keys defined in other sections on this page make sense for this application,
   these should also be used by preference.
2. Windows - alt-single letter should be avoided as these correspond to menu
   shortcuts (e.g. in english locale, alt-f should activate the file menu).
   Common Windows shortcuts can be found at
   https://support.microsoft.com/en-us/windows/keyboard-shortcuts-in-windows-dcc61a57-8ff0-cffe-9796-cb9706c75eec

In addition where they do not conflict with the above, any synergy with keys commonly used
in popular SVG / image editors (e.g. paint.net, inkscape) may be beneficial.

To change keymaps / alias insert new alias at the beginning of the tuple
Later entries in the tuple are used to identify previous defaults and update them to current,
so do not delete these until a version change (like 0.8) results in completely new settings anyway.
"""

DEFAULT_KEYMAP = {
    "right": ("translate 1mm 0",),
    "left": ("translate -1mm 0",),
    "up": ("translate 0 -1mm",),
    "down": ("translate 0 1mm",),
    "a": ("+left",),
    "d": ("+right",),
    "w": ("+up",),
    "s": ("+down",),
    "l": ("lock",),
    "u": ("unlock",),
    "f4": (
        "",
        "window open CameraInterface",
    ),
    "f5": ("refresh",),
    "f6": (
        "",
        "window open JobSpooler",
    ),
    "f7": (
        "",
        "window open -o Controller",
        "window controller",
        "window open Controller",
    ),
    "f8": ("", "dialog_path"),
    "f9": (
        "",
        "dialog_transform",
    ),
    "f12": (
        "",
        "window open Console",
    ),
    "ctrl+f6": ("page home",),
    "ctrl+f7": ("page design",),
    "ctrl+f8": (
        "page modify",
        "dialog_flip",
    ),
    "ctrl+f9": ("page config",),
    "delete": (
        "tree selected delete",
        "tree emphasized delete",
        "element delete",
    ),
    "escape": (
        "",
        "pause",
    ),
    "home": ("home",),
    "numpad_down": ("+translate_down",),
    "numpad_up": ("+translate_up",),
    "numpad_left": ("+translate_left",),
    "numpad_right": ("+translate_right",),
    "numpad_multiply": ("+scale_up",),
    "numpad_divide": ("+scale_down",),
    "numpad_add": ("+rotate_cw",),
    "numpad_subtract": ("+rotate_ccw",),
    "pause": ("pause",),
    "alt+c": (
        "",
        "cut",
    ),
    "alt+e": (
        "",
        "engrave",
    ),
    "alt+f": (
        "",
        "dialog_fill",
    ),
    "alt+h": (
        "",
        "dialog_path",
    ),
    "alt+p": (
        "",
        "dialog_flip",
    ),
    "alt+r": (
        "",
        "raster",
    ),
    "alt+s": (
        "",
        "dialog_stroke",
    ),
    "alt+t": (
        "",
        "dialog_transform",
    ),
    "alt+f3": (
        "",
        "rotaryscale",
    ),
    "ctrl+a": ("element* select",),
    "ctrl+c": ("clipboard copy",),
    "ctrl+shift+c": ("align bed group xy center center",),
    "ctrl+e": (
        "circle 0.5in 0.5in 0.5in stroke red classify",
        "circle 500 500 500",
    ),
    "ctrl+f": (
        "",
        "dialog_fill",
    ),
    "ctrl+i": ("element* select^",),
    "ctrl+d": ("element copy",),
    "ctrl+g": (
        "",
        "planz clear copy preprocess validate blob preopt optimize spool",
    ),
    "ctrl+o": (
        "",
        "outline",
    ),
    "ctrl+r": (
        "rect 0 0 1in 1in stroke red classify",
        "rect 0 0 1000 1000",
    ),
    "ctrl+s": (
        "",
        "dialog_stroke",
    ),
    "ctrl+v": (
        "",
        "clipboard paste",
    ),
    "ctrl+x": (
        "",
        "clipboard cut",
    ),
    "ctrl+z": (
        "",
        "undo",
        "reset",
    ),
    "ctrl+shift+z": (
        "",
        "redo",
    ),
    "ctrl+1": ("bind 1 move $x $y",),
    "ctrl+2": ("bind 2 move $x $y",),
    "ctrl+3": ("bind 3 move $x $y",),
    "ctrl+4": ("bind 4 move $x $y",),
    "ctrl+5": ("bind 5 move $x $y",),
    "ctrl+f3": (
        "",
        "rotaryview",
    ),
    "ctrl+alt+d": ("image wizard Gold",),
    "ctrl+alt+e": ("image wizard Simple",),
    "ctrl+alt+g": (
        "",
        "image wizard Gold",
    ),
    "ctrl+alt+n": ("image wizard Newsy",),
    "ctrl+alt+o": (
        "image wizard Stipo",
        "outline -1mm",
    ),
    "ctrl+alt+s": (
        "",
        "image wizard Stipo",
    ),
    "ctrl+alt+x": ("image wizard Xin",),
    "ctrl+alt+y": ("image wizard Gravy",),
    "ctrl+shift+h": ("scale -1 1",),
    "ctrl+shift+o": ("outline 1mm",),
    "ctrl+shift+v": ("scale 1 -1",),
    "ctrl+alt+shift+escape": (
        "",
        "reset_bind_alias",
    ),
    "ctrl+alt+shift+home": ("bind default;alias default",),
}
DEFAULT_ALIAS = {
    "+scale_up": (".timerscale_up 0 0.1 .scale 1.02",),
    "+scale_down": (".timerscale_down 0 0.1 scale 0.98",),
    "+rotate_cw": (".timerrotate_cw 0 0.1 rotate 2",),
    "+rotate_ccw": (".timerrotate_ccw 0 0.1 rotate -2",),
    "+translate_right": (".timertranslate_right 0 0.1 translate 1mm 0",),
    "+translate_left": (".timertranslate_left 0 0.1 translate -1mm 0",),
    "+translate_down": (".timertranslate_down 0 0.1 translate 0 1mm",),
    "+translate_up": (".timertranslate_up 0 0.1 translate 0 -1mm",),
    "+right": (".timerright 0 0.1 right 1mm",),
    "+left": (".timerleft 0 0.1 left 1mm",),
    "+up": (".timerup 0 0.1 up 1mm",),
    "+down": (".timerdown 0 0.1 down 1mm",),
    "-scale_up": (".timerscale_up off",),
    "-scale_down": (".timerscale_down off",),
    "-rotate_cw": (".timerrotate_cw off",),
    "-rotate_ccw": (".timerrotate_ccw off",),
    "-translate_right": (".timertranslate_right off",),
    "-translate_left": (".timertranslate_left off",),
    "-translate_down": (".timertranslate_down off",),
    "-translate_up": (".timertranslate_up off",),
    "-right": (".timerright off",),
    "-left": (".timerleft off",),
    "-up": (".timerup off",),
    "-down": (".timerdown off",),
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
        self.triggered = {}

        _ = self._

        @self.console_command("bind", help=_("bind <key> <console command>"))
        def bind(command, channel, _, args=tuple(), **kwgs):
            """
            Binds a key to a given keyboard keystroke.
            """
            if len(args) == 0:
                channel(_("Binds:"))

                def keymap_index(key):
                    mods, key = key.rsplit("+", 1) if "+" in key else ("", key)
                    return (
                        mods,
                        len(key) if len(key) <= 2 else 3,
                        key,
                    )

                channel(_("    Key                    Command"))
                for i, key in enumerate(sorted(self.keymap.keys(), key=keymap_index)):
                    value = self.keymap[key]
                    channel(f"{i:2d}: {key.ljust(22)} {value}")
                channel("----------")
                return
            key = args[0].lower()
            if key == "default":
                self.default_keymap()
                channel(_("Keymap set to default."))
                return
            command_line = " ".join(args[1:])
            f = command_line.find("bind")
            if f == -1:  # If bind value has a bind, do not evaluate.
                if "$x" in command_line:
                    x, y = self.device.current
                    command_line = command_line.replace("$x", str(x))
                if "$y" in command_line:
                    x, y = self.device.current
                    command_line = command_line.replace("$y", str(y))
            if len(command_line) != 0:
                self.keymap[key] = command_line
            elif key in self.keymap:
                del self.keymap[key]
                channel(_("Unbound {key}").format(key=key))
            return

        self.read_persistent_string_dict(self.keymap, suffix=True)
        if not len(self.keymap):
            self.default_keymap()

    # help transition from old definitions of control-key-combinations
    def is_found(self, keyvalue, target):
        value = False
        if keyvalue is not None:
            s = keyvalue
            if s in target:
                value = True
            else:
                s = keyvalue.replace("ctrl", "control")
                if s in target:
                    keyvalue = s
                    value = True
        return value, keyvalue

    def trigger(self, keyvalue):
        fnd, keyvalue = self.is_found(keyvalue, self.keymap)
        if fnd:
            fnd, keyvalue = self.is_found(keyvalue, self.triggered)
            if not fnd:
                self.triggered[keyvalue] = 1
                action = self.keymap[keyvalue]
                cmds = (action,) if action[0] in "+-" else action.split(";")
                for cmd in cmds:
                    self(f"{cmd}\n")
                return True
        return False

    def untrigger(self, keyvalue):
        keymap = self.keymap
        fnd, keyvalue = self.is_found(keyvalue, self.keymap)
        if fnd:
            fnd, keyvalue = self.is_found(keyvalue, self.triggered)
            if fnd:
                del self.triggered[keyvalue]
            action = keymap[keyvalue]
            if action.startswith("+"):
                # Keyup commands only trigger if the down command started with +
                action = "-" + action[1:]
                self(action + "\n")
                return True
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

    def service_attach(self, *args, **kwargs):
        if not len(self.keymap):
            self.default_keymap()
            return
        # Remap "control+" to "ctrl+"
        for key in list(self.keymap.keys()):
            if key.startswith("control+"):
                newkey = "ctrl+" + key[8:]
                self.keymap[newkey] = self.keymap[key]
                del self.keymap[key]
        for key, values in DEFAULT_KEYMAP.items():
            if key not in self.keymap or self.keymap[key] in values[1:]:
                value = values[0]
                if value:
                    self.keymap[key] = value
                elif key in self.keymap:
                    del self.keymap[key]


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
            _ = self._
            if alias is None:
                reverse_keymap = {v: k for k, v in self.bind.keymap.items()}
                channel(_("Aliases (keybind)`:"))
                channel(_("    Alias                  Command(s)"))
                last = None
                i = -1
                for key in sorted(
                    self.aliases.keys(),
                    key=lambda x: x if x[0] not in "+-" else "+" + x[1:] + x[0],
                ):
                    value = self.aliases[key]
                    keystroke = reverse_keymap[key] if key in reverse_keymap else ""
                    if last is None or last[0] != "+" or key[0] != "-":
                        i += 1
                    if keystroke and len(key) + len(keystroke) < 18:
                        key += f" ({keystroke})"
                        keystroke = ""
                    if keystroke:
                        channel(f"{i:2d}: ({keystroke})")
                    if last and last[0] == "+" and key[0] == "-":
                        channel(f"    {key.ljust(22)} {value}")
                    elif keystroke:
                        channel(f"    {key.ljust(22)} {value}")
                    else:
                        channel(f"{i:2d}: {key.ljust(22)} {value}")
                    last = key

                channel("----------")
                return
            alias = alias.lower()
            if alias == "default":
                self.default_alias()
                channel(_("Aliases set to default."))
                return
            if remainder is None:
                if alias in self.aliases:
                    del self.aliases[alias]
                    channel(_("Alias {alias_name} unset.").format(alias_name=alias))
                else:
                    channel(
                        _("No alias for {alias_name} was set.").format(alias_name=alias)
                    )
            else:
                self.aliases[alias] = remainder

        @self.console_command(".*", regex=True, hidden=True)
        def alias_execute(command, **kwgs):
            """
            Alias execution code. Checks value for matching alias and utilizes that.

            Aliases with ; delimit multipart commands
            """
            if command in self.aliases:
                aliased_command = self.aliases[command]
                for cmd in aliased_command.split(";"):
                    self(f"{cmd}\n")
            else:
                raise CommandMatchRejected(_("This is not an alias."))

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
        self.aliases.clear()
        for key, values in DEFAULT_ALIAS.items():
            value = values[0]
            if value:
                self.aliases[key] = value

    def service_attach(self, *args, **kwargs):
        if not len(self.aliases):
            self.default_alias()
            return
        for key, values in DEFAULT_ALIAS.items():
            if key not in self.aliases or self.aliases[key] in values[1:]:
                value = values[0]
                if value:
                    self.aliases[key] = value
                elif key in self.aliases:
                    del self.aliases[key]


def keymap_execute(context, keyvalue, keydown=True):
    """
    Execute keybind accelerator if it exists and return true

    Else return false
    """
    if keyvalue not in context.keymap:
        return False
    action = context.keymap[keyvalue]
    if keydown or action.startswith("+"):
        if not keydown and action.startswith("+"):
            action = "-" + action[1:]
        for cmd in action.split(";"):
            context(f"{cmd}\n")
    return True
