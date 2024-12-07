"""
This module provides a set of console commands for managing wordlists within the application.
These commands allow users to add, retrieve, and manipulate wordlist entries, as well as manage wordlist files.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up wordlist commands.
- init_commands(kernel): Initializes the wordlist commands and defines the associated operations.
- wordlist_base(command, channel, _, remainder=None, **kwargs): Base operation for wordlist commands.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    remainder: Additional command arguments.
  Returns:
    A tuple containing the wordlist type and an empty string.
- wordlist_add(command, channel, _, key=None, value=None, **kwargs): Adds a value to the wordlist under the specified key.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The key for the wordlist entry.
    value: The content to associate with the key.
  Returns:
    A tuple containing the wordlist type and the key.
- wordlist_addcounter(command, channel, _, key=None, value=None, **kwargs): Adds a numeric counter to the wordlist under the specified key.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The key for the wordlist entry.
    value: The initial value for the counter.
  Returns:
    A tuple containing the wordlist type and the key.
- wordlist_get(command, channel, _, key=None, index=None, **kwargs): Retrieves the current value from the wordlist for the specified key and index.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The key for the wordlist entry.
    index: The index of the value to retrieve.
  Returns:
    A tuple containing the wordlist type and the retrieved value.
- wordlist_set(command, channel, _, key=None, value=None, index=None, **kwargs): Sets a value in the wordlist for the specified key and index.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The key for the wordlist entry.
    value: The value to set.
    index: The index to use for the value.
  Returns:
    A tuple containing the wordlist type and the key.
- wordlist_index(command, channel, _, key=None, index=None, **kwargs): Sets the index in the wordlist for the specified key.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The key for the wordlist entry.
    index: The index to set.
  Returns:
    A tuple containing the wordlist type and the key.
- wordlist_restore(command, channel, _, filename=None, remainder=None, **kwargs): Loads a previously saved wordlist from the specified file.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    filename: The name of the wordlist file to load.
  Returns:
    A tuple containing the wordlist type and an empty string.
- wordlist_backup(command, channel, _, filename=None, remainder=None, **kwargs): Saves the current wordlist to the specified file.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    filename: The name of the file to save the wordlist to.
  Returns:
    A tuple containing the wordlist type and an empty string.
- wordlist_list(command, channel, _, key=None, **kwargs): Lists the values in the wordlist for the specified key.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    key: The key for the wordlist entry.
  Returns:
    A tuple containing the wordlist type and the key.
- wordlist_load(command, channel, _, filename=None, **kwargs): Attaches a CSV file to the wordlist.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    filename: The name of the CSV file to load.
  Returns:
    A tuple containing the wordlist type and the names of the loaded entries.
- wordlist_advance(command, channel, _, **kwargs): Advances all indices in the wordlist if they are in use.
  Args:
    command: The command context.
    channel: The communication channel for messages.
  Returns:
    A tuple containing the wordlist type and an empty string.
"""

import os.path
import re


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    # ==========
    # WORDLISTS COMMANDS
    # ==========

    @self.console_command(
        "wordlist",
        help=_("Wordlist base operation"),
        output_type="wordlist",
    )
    def wordlist_base(command, channel, _, remainder=None, **kwargs):
        return "wordlist", ""

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_argument("value", help=_("Content"))
    @self.console_command(
        "add",
        help=_("add value to wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_add(command, channel, _, key=None, value=None, **kwargs):
        if key is not None:
            if value is None:
                value = ""
            self.mywordlist.add(key, value)
        return "wordlist", key

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_argument("value", help=_("Content"))
    @self.console_command(
        "addcounter",
        help=_("add numeric counter to wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_addcounter(command, channel, _, key=None, value=None, **kwargs):
        if key is not None:
            if value is None:
                value = 1
            else:
                try:
                    value = int(value)
                except ValueError:
                    value = 1
            self.mywordlist.add(key, value, 2)
        return "wordlist", key

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_argument("index", help=_("index to use"))
    @self.console_command(
        "get",
        help=_("get current value from wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_get(command, channel, _, key=None, index=None, **kwargs):
        if key is not None:
            result = self.mywordlist.fetch_value(skey=key, idx=index)
            channel(str(result))
        else:
            channel(_("Missing key"))
            result = ""
        return "wordlist", result

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_argument("value", help=_("Wordlist value"))
    @self.console_argument("index", help=_("index to use"))
    @self.console_command(
        "set",
        help=_("set value to wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_set(command, channel, _, key=None, value=None, index=None, **kwargs):
        if key is not None and value is not None:
            self.mywordlist.set_value(skey=key, value=value, idx=index)
        else:
            channel(_("Not enough parameters given"))
        return "wordlist", key

    @self.console_argument(
        "key", help=_("Individual wordlist value (use @ALL for all)")
    )
    @self.console_argument("index", help=_("index to use, or +2 to increment by 2"))
    @self.console_command(
        "index",
        help=_("sets index in wordlist"),
        input_type="wordlist",
        output_type="wordlist",
        all_arguments_required=True,
    )
    def wordlist_index(command, channel, _, key=None, index=None, **kwargs):
        self.mywordlist.set_index(skey=key, idx=index)
        return "wordlist", key

    @self.console_argument(
        "filename", help=_("Wordlist file (if empty use mk40-default)")
    )
    @self.console_command(
        "restore",
        help=_("Loads a previously saved wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_restore(command, channel, _, filename=None, remainder=None, **kwargs):
        new_file = filename
        if filename is not None:
            new_file = os.path.join(self.kernel.current_directory, filename)
            if not os.path.exists(new_file):
                channel(_("No such file."))
                return
        self.mywordlist.load_data(new_file)
        return "wordlist", ""

    @self.console_argument(
        "filename", help=_("Wordlist file (if empty use mk40-default)")
    )
    @self.console_command(
        "backup",
        help=_("Saves the current wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_backup(command, channel, _, filename=None, remainder=None, **kwargs):
        new_file = filename
        if filename is not None:
            new_file = os.path.join(self.kernel.current_directory, filename)

        self.mywordlist.save_data(new_file)
        return "wordlist", ""

    @self.console_argument("key", help=_("Wordlist value"))
    @self.console_command(
        "list",
        help=_("list wordlist values"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_list(command, channel, _, key=None, **kwargs):
        channel("----------")
        if key is None:
            for skey in self.mywordlist.content:
                channel(str(skey))
        else:
            if key in self.mywordlist.content:
                wordlist = self.mywordlist.content[key]
                channel(
                    _("Wordlist {name} (Type={type}, Index={index}):").format(
                        name=key, type=wordlist[0], index=wordlist[1] - 2
                    )
                )
                for idx, value in enumerate(wordlist[2:]):
                    channel(f"#{idx}: {str(value)}")
            else:
                channel(_("There is no such pattern {name}").format(name=key))
        channel("----------")
        return "wordlist", key

    @self.console_argument("filename", help=_("CSV file"))
    @self.console_command(
        "load",
        help=_("Attach a csv-file to the wordlist"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_load(command, channel, _, filename=None, **kwargs):
        if filename is None:
            channel(_("No file specified."))
            return
        new_file = os.path.join(self.kernel.current_directory, filename)
        if not os.path.exists(new_file):
            channel(_("No such file."))
            return

        rows, columns, names = self.mywordlist.load_csv_file(new_file)
        channel(_("Rows added: {rows}").format(rows=rows))
        channel(_("Values added: {values}").format(columns=columns))
        for name in names:
            channel("  " + name)
        return "wordlist", names

    @self.console_command(
        "advance",
        help=_("advances all indices in wordlist (if wordlist was used)"),
        input_type="wordlist",
        output_type="wordlist",
    )
    def wordlist_advance(command, channel, _, **kwargs):
        usage = False
        brackets = re.compile(r"\{[^}]+\}")
        for node in self.elems():
            if hasattr(node, "text"):
                if node.text:
                    bracketed_key = list(brackets.findall(str(node.text)))
                    if len(bracketed_key) > 0:
                        usage = True
                        break
            elif hasattr(node, "mktext"):
                if node.mktext:
                    bracketed_key = list(brackets.findall(str(node.mktext)))
                    if len(bracketed_key) > 0:
                        usage = True
                        break

        if usage:
            channel("Advancing wordlist indices")
            self.mywordlist.move_all_indices(1)
            self.signal("refresh_scene", "Scene")
        else:
            channel("Leaving wordlist indices untouched as no usage detected")
        return "wordlist", ""

    # --------------------------- END COMMANDS ------------------------------
