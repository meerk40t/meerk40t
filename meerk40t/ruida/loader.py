"""
RD Loader

Registers the RDLoader for .rd files.

This file type simply loads a blob node.
"""

import os


def data_viewer(data, data_type):
    from meerk40t.core.node.blobnode import BlobNode
    from meerk40t.ruida.rdjob import decode_bytes, determine_magic_via_histogram

    if not data:
        return ""
    magic = determine_magic_via_histogram(data)
    return BlobNode.hex_view(
        data=decode_bytes(data, magic),
        data_type=data_type,
        info = f', Magic={magic} (0x{magic:02x})'
    )


def command_viewer(data, data_type):
    from meerk40t.ruida.rdjob import RDJob

    job = RDJob()
    job.write_blob(data)
    commands = []
    job.channel = commands.append
    try:
        while not job.execute(None):
            pass
    except Exception as e:
        commands.append(f"!! Error !!: {e}")
    return "\n".join(commands)


class RDLoader:
    @staticmethod
    def load_types():
        yield "RDWorks File", ("rd",), "application/x-rd"

    @staticmethod
    def load(kernel, service, pathname, **kwargs):
        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            op_branch = service.get(type="branch ops")
            op_branch.add(
                data=bytearray(f.read()),
                data_type="ruida",
                type="blob",
                label=basename,
                views={"Unswizzled Hex": data_viewer, "Commands": command_viewer},
            )
            kernel.root.close(basename)
            return True
