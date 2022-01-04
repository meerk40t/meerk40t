import unittest

from meerk40t.kernel import Kernel

state = 0

class TestLifeCycle(unittest.TestCase):

    def test_kernel_lifecycle(self):

        def lifecycle_test(obj=None, lifecycle=None):
            global state
            if lifecycle == "preregister":
                self.assertEquals(state, 0)
                state = 1
            if lifecycle == "register":
                self.assertEquals(state, 1)
                state = 2
            if lifecycle == "configure":
                self.assertEquals(state, 2)
                state = 3
            if lifecycle == "preboot":
                self.assertEquals(state, 3)
                state = 4
            if lifecycle == "boot":
                self.assertEquals(state, 4)
                state = 5
            if lifecycle == "postboot":
                self.assertEquals(state, 5)
                state = 6
            if lifecycle == "prestart":
                self.assertEquals(state, 6)
                state = 7
            if lifecycle == "start":
                self.assertEquals(state, 7)
                state = 8
            if lifecycle == "poststart":
                self.assertEquals(state, 8)
                state = 9
            if lifecycle == "ready":
                self.assertEquals(state, 9)
                state = 10
            if lifecycle == "finished":
                self.assertEquals(state, 10)
                state = 11
            if lifecycle == "premain":
                self.assertEquals(state, 11)
                state = 12
            if lifecycle == "mainloop":
                self.assertEquals(state, 12)
                state = 13
            if lifecycle == "mainloop":
                self.assertEquals(state, 13)
                state = 14
                # Mainloop here merely quits.
                kernel.console("quit\n")
            if lifecycle == "preshutdown":
                self.assertEquals(state, 14)
                state = 15
            if lifecycle == "shutdown":
                self.assertEquals(state, 15)
                state = 16
            print(lifecycle)
        kernel = Kernel("MeerK40t", "0.0.0-testing", "MeerK40t")
        kernel.add_plugin(lifecycle_test)
        kernel()

