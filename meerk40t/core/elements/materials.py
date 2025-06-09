"""
This module provides a set of console commands for managing materials within the application.
Users can save, load, delete, and list materials, facilitating the organization and retrieval of material settings.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up material commands.
- init_commands(kernel): Initializes the material commands and defines the associated operations.
- materials(command, channel, _, data=None, remainder=None, **kwargs): Displays information about materials or lists the available material sections.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    data: The operations to retrieve materials from.
    remainder: Additional command arguments.
  Returns:
    A tuple containing the type of materials and the data.
- save_materials(command, channel, _, data=None, name=None, author=None, description=None, **kwargs): Saves the current materials to persistent settings under a specified name.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    data: The materials to save.
    name: The name to save the materials under.
    author: The name of the user for the library entry.
    description: A description of the library entry.
  Returns:
    A tuple containing the type of materials and the data.
- load_materials(name=None, **kwargs): Loads materials from persistent settings based on the specified name.
  Args:
    name: The name to load the materials from.
  Returns:
    A tuple containing the type of operations and the loaded materials.
- delete_materials(name=None, **kwargs): Deletes materials from persistent settings based on the specified name.
  Args:
    name: The name to delete the materials from.
  Returns:
    A tuple containing the type of materials and the remaining operations.
- materials_list(channel, _, data=None, name=None, **kwargs): Displays information about the current materials and their settings.
  Args:
    channel: The communication channel for messages.
    data: The materials to list.
    name: The name to display the materials from.
  Returns:
    None
"""

from meerk40t.kernel import CommandSyntaxError


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    # ==========
    # MATERIALS COMMANDS
    # ==========
    @self.console_command(
        "material",
        help=_("material base operation"),
        input_type=(None, "ops"),
        output_type="materials",
    )
    def materials(command, channel, _, data=None, remainder=None, **kwargs):
        if data is None:
            data = list(self.ops(emphasized=True))
        if remainder is None:
            channel("----------")
            channel(_("Materials:"))
            for section in self.op_data.section_set():
                channel(section)
            channel("----------")
        return "materials", data

    @self.console_option(
        "author", "a", type=str, help=_("Name of the user for the library entry")
    )
    @self.console_option(
        "description", "d", type=str, help=_("Description of the library entry")
    )
    @self.console_argument("name", help=_("Name to save the materials under"))
    @self.console_command(
        "save",
        help=_("Save current materials to persistent settings"),
        input_type="materials",
        output_type="materials",
    )
    def save_materials(
        command,
        channel,
        _,
        data=None,
        name=None,
        author=None,
        description=None,
        **kwargs,
    ):
        if name is None:
            raise CommandSyntaxError
        # Load old information just to maintain old infos...
        oplist, opinfo = self.load_persistent_op_list(name)
        opinfo["name"] = name
        if author is not None:
            opinfo["author"] = author
        if description is not None:
            opinfo["description"] = description
        self.save_persistent_operations(name, opinfo=opinfo)
        return "materials", data

    @self.console_argument("name", help=_("Name to load the materials from"))
    @self.console_command(
        "load",
        help=_("Load materials from persistent settings"),
        input_type="materials",
        output_type="ops",
    )
    def load_materials(name=None, **kwargs):
        if name is None:
            raise CommandSyntaxError
        self.load_persistent_operations(name)
        return "ops", list(self.ops())

    @self.console_argument("name", help=_("Name to delete the materials from"))
    @self.console_command(
        "delete",
        help=_("Delete materials from persistent settings"),
        input_type="materials",
        output_type="materials",
    )
    def delete_materials(name=None, **kwargs):
        if name is None:
            raise CommandSyntaxError
        self.clear_persistent_operations(name)
        return "materials", list(self.ops())

    @self.console_argument("name", help=_("Name to display the materials from"))
    @self.console_command(
        "list",
        help=_("Show information about materials"),
        input_type="materials",
        output_type="materials",
    )
    def materials_list(channel, _, data=None, name=None, **kwargs):
        channel("----------")
        channel(_("Materials Current:"))
        for section in self.op_data.section_set():
            if section.endswith("info"):
                continue
            for subsect in self.op_data.derivable(section):
                label = self.op_data.read_persistent(str, subsect, "label", "-")
                channel(f"{subsect}: {label}")
        channel("----------")

    # --------------------------- END COMMANDS ------------------------------
