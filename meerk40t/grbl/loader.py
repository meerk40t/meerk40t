"""
GCode Loader

Provides the required hooks to register the loader of gcode file.
"""

import os


class GCodeLoader:
    @staticmethod
    def load_types():
        yield "Gcode File", ("gcode", "nc", "gc"), "application/x-gcode"

    @staticmethod
    def load(kernel, service, pathname, **kwargs):
        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            op_branch = service.get(type="branch ops")
            op_branch.add(data=f.read(), data_type="grbl", type="blob", name=basename)
            kernel.root.close(basename)
            return True
