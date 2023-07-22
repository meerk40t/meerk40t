"""
RD Loader

Registers the RDLoader for .rd files.

This file type simply loads a blob node.
"""

import os


def data_viewer(data, data_type):
    from meerk40t.ruida.rdjob import decode_bytes
    from meerk40t.core.node.blobnode import BlobNode

    return BlobNode.hex_view(data=decode_bytes(data), data_type=data_type)


def command_viewer(data, data_type):
    from meerk40t.ruida.rdjob import RDJob
    job = RDJob()
    job.write_blob(data)
    commands = list()
    job.channel = commands.append
    while not job.execute(None):
        pass
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
