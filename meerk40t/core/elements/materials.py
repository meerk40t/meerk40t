"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
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

    @self.console_argument("name", help=_("Name to save the materials under"))
    @self.console_command(
        "save",
        help=_("Save current materials to persistent settings"),
        input_type="materials",
        output_type="materials",
    )
    def save_materials(command, channel, _, data=None, name=None, **kwargs):
        if name is None:
            raise CommandSyntaxError
        self.save_persistent_operations(name)
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
            for subsect in self.op_data.derivable(section):
                label = self.op_data.read_persistent(str, subsect, "label", "-")
                channel(f"{subsect}: {label}")
        channel("----------")

    # --------------------------- END COMMANDS ------------------------------
