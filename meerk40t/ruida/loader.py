"""
RD Loader

Registers the RDLoader for .rd files.

This file type simply loads a blob node.
"""

import os


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
                data=bytearray(f.read()), data_type="ruida", type="blob", label=basename
            )
            kernel.root.close(basename)
            return True
