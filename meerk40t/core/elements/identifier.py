"""
This is a list of console commands that deals with id creation
"""



def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    
    from meerk40t.core.elements.element_types import root_nodes

    self = kernel.elements

    _ = kernel.translation

    # ==========
    # Identifier
    # ==========

    @self.console_option(
        "detail",
        "d",
        action="store_true",
        type=bool,
        help="Display detailed list",
    )
    @self.console_command(
        "id_list",
        help=_("Overview about ids used"),
        input_type=None,
        output_type=None,
    )
    def list_ids(
        command,
        channel,
        _,
        detail=None,
        **kwargs,
    ):
        stats = dict()
        for node in self.flat():
            if node.type in stats:
                info = stats[node.type]
            else:
                info = {
                    "empty": 0,
                    "duplicate": 0,
                    "ids": list(),
                }
            if node.id is None:
                info["empty"] = info["empty"] + 1
            else:
                if node.id in info["ids"]:
                    info["duplicate"] = info["duplicate"] + 1
                else:
                    idl = info["ids"] 
                    idl.append(node.id)
                    info["ids"] = idl

            stats[node.type] = info
        issues = False
        accepted_empty = list(root_nodes)
        accepted_empty.append("reference")
        for ntype, info in stats.items():
            channel(f"Nodetype: {ntype} - ok: {len(info['ids'])}, empty: {info['empty']}, duplicate: {info['duplicate']}")
            if info["empty"] and ntype not in accepted_empty:
                issues = True
            if info["duplicate"]:
                issues = True
            if detail:
                line = ""
                count = 0
                for id in info["ids"]:
                    count += 1
                    line += " " + id
                    if count > 4:
                        channel(line)
                        line = ""
                        count = 0
                if count:
                    channel(line)
        if issues:
            channel(_("Issues identified, you should run 'id_fix'"))

    @self.console_option(
        "detail",
        "d",
        action="store_true",
        type=bool,
        help="Display detailed list",
    )
    @self.console_command(
        "id_fix",
        help=_("Assign empty / fix duplicate ids"),
        input_type=None,
        output_type=None,
    )
    def fix_ids(
        command,
        channel,
        _,
        detail=None,
        **kwargs,
    ):
        issues, empty, duplicate = self.load_identifiers()
        if not issues:
            channel(_("Good news, no issues with node identifiers found"))
            return
        if len(empty):
            channel(_("Fixing {amount} empty identifiers").format(amount=len(empty)))
            for node in empty:
                node.set_id(None)
                if detail:
                    channel(f"{node.type}{' ' + node.label if node.label is not None else ''}: new '{node.id}'")
        if len(duplicate):
            channel(_("Fixing {amount} duplicate identifiers").format(amount=len(duplicate)))
            for node in duplicate:
                old = node.id
                node.set_id(None)
                if detail:
                    channel(f"{node.type}{' ' + node.label if node.label is not None else ''}: from '{old}' to '{node.id}'")

    # --------------------------- END COMMANDS ------------------------------
