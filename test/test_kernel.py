from __future__ import print_function

import unittest

from meerk40t.bootstrap import bootstrap
from meerk40t.kernel import Kernel


class TestKernel(unittest.TestCase):
    def test_kernel_commands(self):
        """
        Tests all commands with no arguments to test for crashes.

        :return:
        """
        kernel = Kernel()
        bootstrap(kernel)
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Elemental")
        kernel_root.activate("modifier/Planner")
        kernel_root.activate("modifier/ImageTools")
        kernel_root.activate("modifier/BindAlias")

        for command in kernel.match("command/.*"):
            cmd = kernel.registered[command]
            if not cmd.regex:
                kernel.console(command.split("/")[-1] + "\n")
