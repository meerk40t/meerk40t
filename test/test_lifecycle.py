import unittest

from meerk40t.kernel import Kernel

state_1 = 0
state_2 = 0


class TestLifeCycle(unittest.TestCase):
    def test_kernel_lifecycle_partial(self):
        def lifecycle_test(obj=None, lifecycle=None):
            global state_1
            if lifecycle == "preregister":
                self.assertEqual(state_1, 0)
                state_1 = 1
            if lifecycle == "register":
                self.assertEqual(state_1, 1)
                state_1 = 2
            if lifecycle == "configure":
                self.assertEqual(state_1, 2)
                state_1 = 3
            if lifecycle == "preboot":
                self.assertEqual(state_1, 3)
                state_1 = 4
            if lifecycle == "boot":
                self.assertEqual(state_1, 4)
                state_1 = 5
            if lifecycle == "postboot":
                self.assertEqual(state_1, 5)
                state_1 = 6
            if lifecycle == "prestart":
                self.assertEqual(state_1, 6)
                state_1 = 7
            if lifecycle == "start":
                self.assertEqual(state_1, 7)
                state_1 = 8
            if lifecycle == "poststart":
                self.assertEqual(state_1, 8)
                state_1 = 9
            if lifecycle == "ready":
                self.assertEqual(state_1, 9)
                state_1 = 10
            if lifecycle == "finished":
                self.assertEqual(state_1, 10)
                state_1 = 11
            if lifecycle == "premain":
                self.assertEqual(state_1, 11)
                state_1 = 12
            if lifecycle == "mainloop":
                self.assertEqual(state_1, 12)
                state_1 = 13
            if lifecycle == "mainloop":
                self.assertEqual(state_1, 13)
                state_1 = 14
                # Mainloop here merely quits.
                kernel.console("quit\n")
            if lifecycle == "preshutdown":
                self.assertEqual(state_1, 14)
                state_1 = 15
            if lifecycle == "shutdown":
                self.assertEqual(state_1, 15)
                state_1 = 16
            print(lifecycle)

        kernel = Kernel("MeerK40t", "0.0.0-testing", "MeerK40t")
        kernel.add_plugin(lifecycle_test)
        kernel(partial=True)

    def test_kernel_lifecycle(self):
        def lifecycle_test(obj=None, lifecycle=None):
            global state_2
            if lifecycle == "preregister":
                self.assertEqual(state_2, 0)
                state_2 = 1
            if lifecycle == "register":
                self.assertEqual(state_2, 1)
                state_2 = 2
            if lifecycle == "configure":
                self.assertEqual(state_2, 2)
                state_2 = 3
            if lifecycle == "preboot":
                self.assertEqual(state_2, 3)
                state_2 = 4
            if lifecycle == "boot":
                self.assertEqual(state_2, 4)
                state_2 = 5
            if lifecycle == "postboot":
                self.assertEqual(state_2, 5)
                state_2 = 6
            if lifecycle == "prestart":
                self.assertEqual(state_2, 6)
                state_2 = 7
            if lifecycle == "start":
                self.assertEqual(state_2, 7)
                state_2 = 8
            if lifecycle == "poststart":
                self.assertEqual(state_2, 8)
                state_2 = 9
            if lifecycle == "ready":
                self.assertEqual(state_2, 9)
                state_2 = 10
            if lifecycle == "finished":
                self.assertEqual(state_2, 10)
                state_2 = 11
            if lifecycle == "premain":
                self.assertEqual(state_2, 11)
                state_2 = 12
            if lifecycle == "mainloop":
                self.assertEqual(state_2, 12)
                state_2 = 13
            if lifecycle == "mainloop":
                self.assertEqual(state_2, 13)
                state_2 = 14
                # Mainloop does not quit, we expect full execution without a catch.
            if lifecycle == "preshutdown":
                self.assertEqual(state_2, 14)
                state_2 = 15
            if lifecycle == "shutdown":
                self.assertEqual(state_2, 15)
                state_2 = 16
            print(lifecycle)

        kernel = Kernel("MeerK40t", "0.0.0-testing", "MeerK40t")
        kernel.add_plugin(lifecycle_test)
        kernel()
