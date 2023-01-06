import unittest

from meerk40t.kernel import Kernel

state = 0


class TestLifeCycle(unittest.TestCase):
    def test_kernel_lifecycle(self):
        def lifecycle_test(obj=None, lifecycle=None):
            global state
            if lifecycle == "preregister":
                self.assertEqual(state, 0)
                state = 1
            if lifecycle == "register":
                self.assertEqual(state, 1)
                state = 2
            if lifecycle == "configure":
                self.assertEqual(state, 2)
                state = 3
            if lifecycle == "preboot":
                self.assertEqual(state, 3)
                state = 4
            if lifecycle == "boot":
                self.assertEqual(state, 4)
                state = 5
            if lifecycle == "postboot":
                self.assertEqual(state, 5)
                state = 6
            if lifecycle == "prestart":
                self.assertEqual(state, 6)
                state = 7
            if lifecycle == "start":
                self.assertEqual(state, 7)
                state = 8
            if lifecycle == "poststart":
                self.assertEqual(state, 8)
                state = 9
            if lifecycle == "ready":
                self.assertEqual(state, 9)
                state = 10
            if lifecycle == "finished":
                self.assertEqual(state, 10)
                state = 11
            if lifecycle == "premain":
                self.assertEqual(state, 11)
                state = 12
            if lifecycle == "mainloop":
                self.assertEqual(state, 12)
                state = 13
            if lifecycle == "mainloop":
                self.assertEqual(state, 13)
                state = 14
                # Mainloop here merely quits.
                kernel.console("quit\n")
            if lifecycle == "preshutdown":
                self.assertEqual(state, 14)
                state = 15
            if lifecycle == "shutdown":
                self.assertEqual(state, 15)
                state = 16
            print(lifecycle)

        kernel = Kernel("MeerK40t", "0.0.0-testing", "MeerK40t")
        kernel.add_plugin(lifecycle_test)
        kernel()
