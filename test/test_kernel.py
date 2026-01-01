import unittest

from meerk40t.kernel import kernel_console_command, service_console_command
from test import bootstrap


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
    def test_plugin_service_commands(self):
        """
        Test registration of service command via classbased decorator
        """
        def test_plugin_service(kernel, lifecycle):
            if lifecycle == "register":
                service = kernel.elements
                service.add_service_delegate(TestObject())

        kernel = bootstrap.bootstrap(plugins=[test_plugin_service])
        try:
            n = kernel.root("hello")
            self.assertEqual(n, "hello")
        finally:
            kernel()

    def test_plugin_kernel_commands(self):
        """
        Test registration of kernel command via classbased decorator
        """
        def test_plugin_kernel(kernel, lifecycle):
            if lifecycle == "register":
                # Register TestObject directly to kernel for kernel commands
                kernel.add_delegate(TestObject(), kernel)

        kernel = bootstrap.bootstrap(plugins=[test_plugin_kernel])
        try:
            # Test kernel command - should return ("elements", 1)
            result = kernel.root("hello")
            self.assertEqual(result, 1)
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


class TestSignalSystem(unittest.TestCase):

    def test_basic_signal_functionality(self):
        """Test that basic signal sending and receiving works"""
        kernel = bootstrap.bootstrap()
        try:
            received_signals = []

            def test_listener(origin, *message):
                received_signals.append((origin, message))

            # Register listener
            kernel.listen('test_signal', test_listener)
            # Process to add the listener
            kernel.process_queue()

            # Send signal
            kernel.signal('test_signal', 'path', 'arg1', 'arg2')
            kernel.process_queue()

            # Verify signal was received
            self.assertEqual(len(received_signals), 1)
            self.assertEqual(received_signals[0], ('path', ('arg1', 'arg2')))
        finally:
            kernel()

    def test_multiple_listeners_same_signal(self):
        """Test that multiple listeners can register for the same signal"""
        kernel = bootstrap.bootstrap()
        try:
            received1 = []
            received2 = []

            def listener1(origin, *message):
                received1.append((origin, message))

            def listener2(origin, *message):
                received2.append((origin, message))

            kernel.listen('shared_signal', listener1)
            kernel.listen('shared_signal', listener2)
            # Process to add the listeners
            kernel.process_queue()

            kernel.signal('shared_signal', 'path', 'data')
            kernel.process_queue()

            self.assertEqual(len(received1), 1)
            self.assertEqual(len(received2), 1)
            self.assertEqual(received1[0], ('path', ('data',)))
            self.assertEqual(received2[0], ('path', ('data',)))
        finally:
            kernel()

    def test_listener_removal(self):
        """Test that listeners can be properly removed"""
        kernel = bootstrap.bootstrap()
        try:
            received_signals = []

            def test_listener(origin, *message):
                received_signals.append((origin, message))

            kernel.listen('removal_signal', test_listener)
            # Process to add the listener
            kernel.process_queue()

            # Send signal
            kernel.signal('removal_signal', 'path', 'data1')
            kernel.process_queue()
            self.assertEqual(len(received_signals), 1)

            # Remove listener
            kernel.unlisten('removal_signal', test_listener)

            # Send another signal - should not be received
            kernel.signal('removal_signal', 'path', 'data2')
            kernel.process_queue()

            # Should still only have 1 signal (the second should not have been received)
            self.assertEqual(len(received_signals), 1)
        finally:
            kernel()

    def test_exception_handling_in_listener_processing(self):
        """Test that exceptions in listeners don't crash the signal system"""
        kernel = bootstrap.bootstrap()
        try:
            received_signals = []

            def good_listener(origin, *message):
                received_signals.append(('good', origin, message))

            def bad_listener(origin, *message):
                raise RuntimeError("Test exception in listener")

            kernel.listen('exception_signal', good_listener)
            kernel.listen('exception_signal', bad_listener)
            # Process to add the listeners
            kernel.process_queue()

            # Send signal - bad listener should not crash the system
            kernel.signal('exception_signal', 'path', 'data')
            kernel.process_queue()

            # Good listener should still have received the signal
            self.assertEqual(len(received_signals), 1)
            self.assertEqual(received_signals[0][0], 'good')
        finally:
            kernel()

    def test_unlisten_unregistered_listener(self):
        """Test that unlistening an unregistered listener does not cause errors"""
        kernel = bootstrap.bootstrap()
        try:
            def never_registered_listener(origin, *message):
                pass

            # Try to unlisten a listener that was never registered
            # This should not raise an exception
            kernel.unlisten('nonexistent_signal', never_registered_listener)
            kernel.process_queue()

            # Also test unlistening from a signal that exists but doesn't have this listener
            kernel.listen('existing_signal', lambda origin, *message: None)
            kernel.process_queue()

            # Try to unlisten a different listener from the existing signal
            kernel.unlisten('existing_signal', never_registered_listener)
            kernel.process_queue()

            # System should still function normally
            kernel.signal('existing_signal', 'path', 'data')
            kernel.process_queue()

        finally:
            kernel()
