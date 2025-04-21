"""
This module provides a set of console commands for managing the penbox within the application.
Users can add, retrieve, and manipulate pen settings, facilitating the organization and retrieval of pen configurations.
Pens contain a coupöe of burn settings that can be applied by using the pen for a given element.
It will feel familiar to ezc*d users.
It's probably a very similar concept to the material methodology and the material manager.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up penbox commands.
- init_commands(kernel): Initializes the penbox commands and defines the associated operations.
- penbox(command, channel, _, key=None, remainder=None, **kwargs): Displays information about the penbox or lists the available pen entries.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The specific penbox key to retrieve.
    remainder: Additional command arguments.
  Returns:
    A tuple containing the type of penbox and the data.
- penbox_add(command, channel, _, count=None, data=None, remainder=None, **kwargs): Adds a specified number of pens to the chosen penbox.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    count: The number of pens to add.
    data: The penbox to which pens are added.
    remainder: Additional command arguments.
  Returns:
    A tuple containing the type of penbox and the data.
- penbox_del(command, channel, _, count=None, data=None, remainder=None, **kwargs): Deletes a specified number of pens from the chosen penbox.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    count: The number of pens to delete.
    data: The penbox from which pens are deleted.
    remainder: Additional command arguments.
  Returns:
    A tuple containing the type of penbox and the data.
- penbox_set(command, channel, _, index=None, key=None, value=None, data=None, remainder=None, **kwargs): Sets a value in the penbox for the specified index and key.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    index: The index in the penbox to set the value.
    key: The key for the penbox entry.
    value: The value to set in the penbox.
    data: The penbox to modify.
    remainder: Additional command arguments.
  Returns:
    A tuple containing the type of penbox and the data.
- penbox_pass(command, channel, _, key=None, remainder=None, data=None, **kwargs): Sets the penbox pass for the given operation.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The penbox key to set the pass for.
    remainder: Additional command arguments.
    data: The operations to modify.
  Returns:
    A tuple containing the type of operations and the data.
- penbox_value(command, channel, _, key=None, remainder=None, data=None, **kwargs): Sets the penbox value for the given operation.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The penbox key to set the value for.
    remainder: Additional command arguments.
    data: The operations to modify.
  Returns:
    A tuple containing the type of operations and the data.
- load_persistent_penbox(): Loads pen settings from persistent storage into the application.
  Returns:
    None
- save_persistent_penbox(): Saves the current pen settings to persistent storage.
  Returns:
    None
- shutdown(*args, **kwargs): Handles the shutdown process by saving pen settings.
  Returns:
    None
"""

import re

from meerk40t.kernel import CommandSyntaxError, Service, Settings


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "register":
        kernel.add_service("penbox", Penbox(kernel))


def index_range(index_string):
    """
    Parses index ranges in the form <idx>,<idx>-<idx>,<idx>
    @param index_string:
    @return:
    """
    indexes = list()
    for s in index_string.split(","):
        q = list(s.split("-"))
        if len(q) == 1:
            indexes.append(int(q[0]))
        else:
            start = int(q[0])
            end = int(q[1])
            if start > end:
                for q in range(end, start + 1):
                    indexes.append(q)
            else:
                for q in range(start, end + 1):
                    indexes.append(q)
    return indexes


class Penbox(Service):
    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "penbox")
        self.pen_data = Settings(self.kernel.name, "penbox.cfg")
        self.pens = {}
        self.load_persistent_penbox()

        _ = kernel.translation

        # ==========
        # PENBOX COMMANDS
        # ==========

        @self.console_argument("key", help=_("Penbox key"))
        @self.console_command(
            "penbox",
            help=_("Penbox base operation"),
            input_type=None,
            output_type="penbox",
        )
        def penbox(command, channel, _, key=None, remainder=None, **kwargs):
            if remainder is None or key is None:
                channel("----------")
                if key is None:
                    for key in self.pens:
                        channel(str(key))
                else:
                    try:
                        for i, value in enumerate(self.pens[key]):
                            channel(f"{i}: {str(value)}")
                    except KeyError:
                        channel(_("penbox does not exist"))
                channel("----------")
            return "penbox", key

        @self.console_argument("count", help=_("Penbox count"), type=int)
        @self.console_command(
            "add",
            help=_("add pens to the chosen penbox"),
            input_type="penbox",
            output_type="penbox",
        )
        def penbox_add(
            command, channel, _, count=None, data=None, remainder=None, **kwargs
        ):
            if count is None:
                raise CommandSyntaxError
            current = self.pens.get(data)
            if current is None:
                current = list()
                self.pens[data] = current
            current.extend([dict() for _ in range(count)])
            return "penbox", data

        @self.console_argument("count", help=_("Penbox count"), type=int)
        @self.console_command(
            "del",
            help=_("delete pens to the chosen penbox"),
            input_type="penbox",
            output_type="penbox",
        )
        def penbox_del(
            command, channel, _, count=None, data=None, remainder=None, **kwargs
        ):
            if count is None:
                raise CommandSyntaxError
            current = self.pens.get(data)
            if current is None:
                current = list()
                self.pens[data] = current
            for _ in range(count):
                try:
                    del current[-1]
                except IndexError:
                    break
            return "penbox", data

        @self.console_argument("index", help=_("Penbox index"), type=index_range)
        @self.console_argument("key", help=_("Penbox key"), type=str)
        @self.console_argument("value", help=_("Penbox key"), type=str)
        @self.console_command(
            "set",
            help=_("set value in penbox"),
            input_type="penbox",
            output_type="penbox",
        )
        def penbox_set(
            command,
            channel,
            _,
            index=None,
            key=None,
            value=None,
            data=None,
            remainder=None,
            **kwargs,
        ):
            if not value:
                raise CommandSyntaxError
            current = self.pens.get(data)
            if current is None:
                current = list()
                self.pens[data] = current
            rex = re.compile(r"([+-]?[0-9]+)(?:[,-]([+-]?[0-9]+))?")
            m = rex.match(value)
            if not m:
                raise CommandSyntaxError
            value = float(m.group(1))
            end = m.group(2)
            if end:
                end = float(end)

            if not end:
                for i in index:
                    try:
                        current[i][key] = value
                    except IndexError:
                        pass
            else:
                r = len(index)
                try:
                    s = (end - value) / (r - 1)
                except ZeroDivisionError:
                    s = 0
                d = 0
                for i in index:
                    try:
                        current[i][key] = value + d
                    except IndexError:
                        pass
                    d += s
            return "penbox", data

        # ==========
        # PENBOX OPERATION COMMANDS
        # ==========

        @self.console_argument("key", help=_("Penbox key"))
        @self.console_command(
            "penbox_pass",
            help=_("Set the penbox_pass for the given operation"),
            input_type="ops",
            output_type="ops",
        )
        def penbox_pass(
            command, channel, _, key=None, remainder=None, data=None, **kwargs
        ):
            if data is not None:
                if key is not None:
                    for op in data:
                        try:
                            op.settings["penbox_pass"] = key
                            channel(f"{str(op)} penbox_pass changed to {key}.")
                        except AttributeError:
                            pass
                else:
                    if key is None:
                        channel("----------")
                        for op in data:
                            try:
                                key = op.settings.get("penbox_pass")
                                if key is None:
                                    channel(f"{str(op)} penbox_pass is not set.")
                                else:
                                    channel(f"{str(op)} penbox_pass is set to {key}.")
                            except AttributeError:
                                pass  # No op.settings.
                        channel("----------")
            return "ops", data

        @self.console_argument("key", help=_("Penbox key"))
        @self.console_command(
            "penbox_value",
            help=_("Set the penbox_value for the given operation"),
            input_type="ops",
            output_type="ops",
        )
        def penbox_value(
            command, channel, _, key=None, remainder=None, data=None, **kwargs
        ):
            if data is not None:
                if key is not None:
                    for op in data:
                        try:
                            op.settings["penbox_value"] = key
                            channel(f"{str(op)} penbox_value changed to {key}.")
                        except AttributeError:
                            pass
                else:
                    if key is None:
                        channel("----------")
                        for op in data:
                            try:
                                key = op.settings.get("penbox_value")
                                if key is None:
                                    channel(f"{str(op)} penbox_value is not set.")
                                else:
                                    channel(f"{str(op)} penbox_value is set to {key}.")
                            except AttributeError:
                                pass  # No op.settings.
                        channel("----------")
            return "ops", data

        # --------------------------- END COMMANDS ------------------------------

    def load_persistent_penbox(self):
        settings = self.pen_data
        pens = settings.read_persistent_string_dict("pens", suffix=True)
        for pen in pens:
            length = int(pens[pen])
            box = list()
            for i in range(length):
                penbox = dict()
                settings.read_persistent_string_dict(f"{pen} {i}", penbox, suffix=True)
                box.append(penbox)
            self.pens[pen] = box

    def save_persistent_penbox(self):
        sections = {}
        for section in self.pens:
            sections[section] = len(self.pens[section])
        self.pen_data.write_persistent_dict("pens", sections)
        for section in self.pens:
            for i, p in enumerate(self.pens[section]):
                self.pen_data.write_persistent_dict(f"{section} {i}", p)

    def shutdown(self, *args, **kwargs):
        self.save_persistent_penbox()
        self.pen_data.write_configuration()
