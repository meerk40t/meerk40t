"""
Tests for the balor footpedal polling loop, focused on the "arm_start" pedal mode which
arms the laser and starts the current job on a press.
"""

import unittest
from unittest import mock

from test import bootstrap

from meerk40t.core.spoolers import Spooler


class ScriptedPort:
    """
    Stands in for the controller, feeding scripted GPIO port bits to the polling loop.

    `read_port` returns (status, port_bits) as the real controller does. The sequence ends
    by returning None, which is what a disconnected controller looks like.
    """

    def __init__(self, values):
        self.values = list(values)
        self.connected = True

    def read_port(self):
        if not self.values:
            return None
        return 0, self.values.pop(0)


class TestBalorPedal(unittest.TestCase):
    """
    Drives one polling loop iteration per scripted port value and checks which console
    commands the pedal causes.
    """

    def setUp(self):
        self.kernel = bootstrap.bootstrap()
        self.addCleanup(self.kernel)
        self.kernel.console("service device start -i balor 0\n")
        self.device = self.kernel.device
        self.driver = self.device.driver

        # Take over the connection and the polling thread from the running service.
        self.driver._shutdown = True
        self.driver.stop_pedal_polling(force=True)

        self.messages = []
        # Watch the real console channel: the driver reports pedal decisions there, and
        # watching it (rather than stubbing the channel) is what proves it does.
        self.console = self.kernel.channel("console")
        self.watcher = self.messages.append
        self.console.watch(self.watcher)
        self.addCleanup(self.console.unwatch, self.watcher)
        self.device.footpedal_pin = 15
        self.device.pedal_active_low = True
        self.device.pedal_mode = "arm_start"
        self.released = 1 << 15
        self.pressed = 0
        self.started = []

    def _register_start_commands(self):
        """
        Register the arm/startjob pair the gui provides, recording what the pedal runs.
        """

        def recorder(name):
            def handler(*args, **kwargs):
                self.started.append(name)

            return handler

        self.kernel.console_command("arm", help="test")(recorder("arm"))
        self.kernel.console_command("startjob", help="test")(recorder("startjob"))

    def _add_burnable_element(self):
        self.kernel.console("rect 1mm 1mm 1mm 1mm cut\n")
        self.assertTrue(self.kernel.elements.have_burnable_elements())

    def _poll(self, values, interval=0.05):
        """
        Run the polling loop over the given port bit sequence.

        @param values: port bit values, one per poll cycle
        @param interval: the configured pedal_poll_interval for the run
        """
        driver = self.driver
        port = ScriptedPort(values)
        scripted_read = port.read_port

        def read_port():
            result = scripted_read()
            if result is None:
                driver._pedal_thread_running = False
            return result

        port.read_port = read_port
        driver.connection = port
        driver.service.pedal_poll_interval = interval
        driver._pedal_thread_running = True
        driver._shutdown = False
        driver._pedal_polling_worker()

    def assertNoPollingError(self):
        errors = [m for m in self.messages if "Pedal polling error" in str(m)]
        self.assertEqual([], errors)

    def test_press_arms_and_starts(self):
        self._register_start_commands()
        self._add_burnable_element()
        self._poll([self.released, self.pressed])
        self.assertNoPollingError()
        self.assertEqual(["arm", "startjob"], self.started)
        self.assertTrue(
            any(
                "Footpedal pressed: arming, starting job." in str(m)
                for m in self.messages
            )
        )

    def test_release_after_start_does_not_restart(self):
        self._register_start_commands()
        self._add_burnable_element()
        self._poll([self.released, self.pressed, self.released])
        self.assertNoPollingError()
        self.assertEqual(["arm", "startjob"], self.started)

    def test_second_press_starts_again(self):
        self._register_start_commands()
        self._add_burnable_element()
        self._poll([self.released, self.pressed, self.released, self.pressed])
        self.assertNoPollingError()
        self.assertEqual(["arm", "startjob", "arm", "startjob"], self.started)

    def test_pedal_held_at_start_is_not_a_press(self):
        self._register_start_commands()
        self._add_burnable_element()
        self._poll([self.pressed])
        self.assertNoPollingError()
        self.assertEqual([], self.started)

    def test_press_ignored_while_job_is_queued(self):
        self._register_start_commands()
        self._add_burnable_element()
        with mock.patch.object(Spooler, "is_idle", False):
            self._poll([self.released, self.pressed])
        self.assertNoPollingError()
        self.assertEqual([], self.started)
        self.assertTrue(any("ignored" in str(m) for m in self.messages))

    def test_press_ignored_without_burnable_elements(self):
        self._register_start_commands()
        self.assertFalse(self.kernel.elements.have_burnable_elements())
        self._poll([self.released, self.pressed])
        self.assertNoPollingError()
        self.assertEqual([], self.started)
        self.assertTrue(any("ignored" in str(m) for m in self.messages))

    def test_poll_interval_falls_back_to_the_declared_default(self):
        """An unset or unparsable interval uses the default the setting declares, floored at 0.05s."""
        default = self.device.pedal_poll_interval
        self.assertEqual(0.25, default)
        for value in (None, 0, "no interval"):
            self._poll([self.released], interval=value)
            self.assertNoPollingError()
            self.assertEqual(default, self.driver._pedal_poll_interval)
        self._poll([self.released], interval=0.001)
        self.assertEqual(0.05, self.driver._pedal_poll_interval)

    def test_pedal_status_reports_decoded_port_state(self):
        # The report is the support tool for exactly this feature; a wrong decode
        # (pin or polarity) would send the next debugging session down the wrong path.
        self._register_start_commands()
        self.driver.connection = ScriptedPort([self.pressed, self.pressed])
        self.device("pedal_status\n")
        text = "\n".join(str(m) for m in self.messages)
        self.assertIn(f"Pin: {self.device.footpedal_pin}", text)
        self.assertIn("Decoded: pressed", text)
        self.assertIn("Burnable elements: False", text)

    def test_press_ignored_without_arm_commands(self):
        # No gui: the arm/startjob commands are not registered in this kernel.
        self.assertFalse(self.kernel.has_command("arm"))
        self._add_burnable_element()
        self._poll([self.released, self.pressed])
        self.assertNoPollingError()
        self.assertEqual([], self.started)
        self.assertTrue(any("ignored" in str(m) for m in self.messages))
