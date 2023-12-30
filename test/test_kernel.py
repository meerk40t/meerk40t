import unittest
from test import bootstrap

from meerk40t.kernel import kernel_console_command, service_console_command


def test_plugin_service(kernel, lifecycle):
    if lifecycle == "register":
        service = kernel.elements
        service.add_service_delegate(TestObject())


def test_plugin_kernel(kernel, lifecycle):
    if lifecycle == "register":
        kernel.add_delegate(TestObject(), kernel)


class TestObject:
    """
    Object flagged with service and kernel console commands.
    """

    @service_console_command("hello")
    def service_console_command(self, command, channel, **kwargs):
        return "elements", "hello"

    @kernel_console_command("hello")
    def kernel_console_command2(self, command, channel, **kwargs):
        return "elements", 1


class TestKernel(unittest.TestCase):
    def test_object_service_commands(self):
        """
        Test registration of service command via classbased decorator
        """
        kernel = bootstrap.bootstrap(plugins=[test_plugin_service])
        try:
            n = kernel.root("hello")
            self.assertEqual(n, "hello")
        finally:
            kernel()

    def test_object_kernel_commands(self):
        """
        Test registration of kernel command via classbased decorator
        """
        kernel = bootstrap.bootstrap(plugins=[test_plugin_kernel])
        try:
            n = kernel.root("hello")
            self.assertEqual(n, 1)
        finally:
            kernel()

    def test_kernel_commands(self):
        """
        Tests all commands with no arguments to test for crashes...
        """
        kernel = bootstrap.bootstrap()
        try:
            for cmd, path, command in kernel.find("command/.*"):
                if "server" in command:
                    continue
                if "ruida" in command:
                    continue
                if "grbl" in command:
                    continue
                if "usb_" in command:
                    continue
                if command in (
                    "quit",
                    "shutdown",
                    "restart",
                    "interrupt",
                    "+laser",
                    "-laser",
                    "left",
                    "right",
                    "top",
                    "bottom",
                    "home",
                    "unlock",
                    "lock",
                    "physical_home",
                    "test_dot_and_home",
                ):
                    continue
                if not cmd.regex:
                    print(f"Testing command: {command}")
                    # command should be generated with something like
                    # kernel.console(" ".join(command.split("/")[1:]) + "\n")
                    # if first parameter is not base but this fails so not
                    # changing yet
                    kernel.console(command.split("/")[-1] + "\n")
        finally:
            kernel()

    def test_tree_menu(self):
        """
        Tests all commands with no arguments to test for crashes...
        """
        from PIL import Image

        from meerk40t.core.treeop import tree_operations_for_node

        image = Image.new("RGBA", (256, 256))
        from PIL import ImageDraw

        draw = ImageDraw.Draw(image)
        draw.ellipse((0, 0, 255, 255), "black")
        image = image.convert("L")

        kwargs_nodes = (
            {"type": "elem ellipse", "center": 0j, "r": 10000},
            {"type": "elem image", "image": image, "dpi": 500},
            {"type": "elem path", "d": "M0,0L10000,10000"},
            {"type": "elem point", "x": 0, "y": 0},
            {
                "type": "elem polyline",
                "points": (
                    0j,
                    10000j,
                ),
            },
            {"type": "elem rect", "x": 0, "y": 0, "width": 10000, "height": 20000},
            {"type": "elem line", "x1": 0, "y1": 0, "x2": 20000, "y2": 20000},
            {"type": "elem text", "text": "Hello World."},
        )
        kernel = bootstrap.bootstrap()
        try:
            for kws in kwargs_nodes:
                print(f"Creating: {kws.get('type')}")
                n = kernel.elements.elem_branch.add(**kws)
                print(n)

                nodes = tree_operations_for_node(kernel.elements, n)
                for func in nodes:
                    func_dict = dict(func.func_dict)
                    print(f"Executing: {func.name}")
                    func(n, **func_dict)
                    if n.parent is None:
                        # This function removed the element. Put it back in the tree.
                        kernel.elements.elem_branch.add_node(n)
        finally:
            kernel.console("elements\n")
            kernel()

    def test_external_plugins(self):
        """
        This tests the functionality of external plugins which typically ran pkg_resources but was switched to
        importlib on the release of python 3.12. This code functions if and only if no crash happens.

        @return:
        """

        class Args:
            no_plugins = False

        kernel = bootstrap.bootstrap()
        kernel.args = Args()
        try:
            from meerk40t.external_plugins import plugin

            q = plugin(kernel=kernel, lifecycle="plugins")
            print(q)
        finally:
            kernel()


class TestGetSafePath(unittest.TestCase):
    def test_get_safe_path(self):
        import os

        from meerk40t.kernel import get_safe_path

        """
        Tests the get_safe_path method for all o/ses
        """
        sep = os.sep
        self.assertEqual(
            str(get_safe_path("test", system="Darwin")),
            (
                os.path.expanduser("~")
                + sep
                + "Library"
                + sep
                + "Application Support"
                + sep
                + "test"
            ),
        )
        self.assertEqual(
            str(get_safe_path("test", system="Windows")),
            (os.path.expandvars("%LOCALAPPDATA%") + sep + "test"),
        )
        self.assertEqual(
            str(get_safe_path("test", system="Linux")),
            (os.path.expanduser("~") + sep + ".config" + sep + "test"),
        )


class TestEchoCommand(unittest.TestCase):
    def test_echo_and_ansi(self):
        """
        Tests all echo options separately and combined
        with output to ansi terminal window
        """
        echo_commands = [
            "echo",
            "echo [bg-white][black] black text",
            "echo [red] red text",
            "echo [green] green text",
            "echo [yellow] yellow text",
            "echo [blue] blue text",
            "echo [magenta] magenta text",
            "echo [cyan] cyan text",
            "echo [bg-black][white] white text",
            "echo [bg-black][white] black background",
            "echo [bg-red] red background",
            "echo [bg-green] green background",
            "echo [bg-yellow] yellow background",
            "echo [bg-blue] blue background",
            "echo [bg-magenta] magenta background",
            "echo [bg-cyan] cyan background",
            "echo [bg-white][black] white background",
            "echo [bg-white][black] bright black text",
            "echo [bold][red] bright red text",
            "echo [bold][green] bright green text",
            "echo [bold][yellow] bright yellow text",
            "echo [bold][blue] bright blue text",
            "echo [bold][magenta] bright magenta text",
            "echo [bold][cyan] bright cyan text",
            "echo [bold][bg-black][white] bright white text",
            "echo [bold] bold text [/bold] normal text",
            "echo [italic] italic text [/italic] normal text",
            "echo [underline] underline text [/underline] normal text",
            "echo [underscore] underscore text [/underscore] normal text",
            "echo [negative] negative text [positive] positive text",
            "echo [negative] negative text [normal] normal text",
            "echo [raw][red] red bbcode and normal text",
        ]

        kernel = bootstrap.bootstrap()
        try:
            for echo in echo_commands:
                print(f"Testing echo command: {echo}")
                kernel.console(echo + "\n")
        finally:
            kernel()
