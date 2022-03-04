"""
AirAssist contains basic code to externally turn on / off air assist .

"""
from subprocess import run
from threading import Timer


AA_METHOD_NONE = 0
AA_METHOD_MQTT = 1
AA_METHOD_SHELL = 2
AA_METHOD_RPI_GPIO = 3


class AirAssist:

    myTimer = None
    overshoot = 5.0
    shell_command_on = "turn_aa_on.cmd"
    shell_command_off = "turn_aa_off.cmd"

    def __init__(self):
        self._method = AA_METHOD_NONE
        self._status = False

    # function to get value of _method
    @property
    def method(self):
        return self._method

    # function to set value of _method
    @method.setter
    def method(self, a):
        if (a < AA_METHOD_NONE) or (a > AA_METHOD_RPI_GPIO):
            raise ValueError("Sorry this AirAssist-method isn't supported")

        if a == AA_METHOD_NONE:
            pass
        elif a == AA_METHOD_MQTT:
            print("MQTT-Method called, need to establish connectivity")
        elif a == AA_METHOD_SHELL:
            print("Shell-Method called")
        elif a == AA_METHOD_RPI_GPIO:
            print("RPI-Method called")

        self._method = a

    @property
    def status(self):
        return self._status

    @method.setter
    def status(self, a):
        if a:
            self._status = True
        else:
            self._status = False
        if self._method == AA_METHOD_NONE:
            print(
                "AirAssist ignored, would have been set to %s"
                % ("ON" if self._status else "OFF")
            )
        elif self._method == AA_METHOD_MQTT:
            print(
                "AirAssist MQTT, would have been set to %s"
                % ("ON" if self._status else "OFF")
            )
        elif self._method == AA_METHOD_SHELL:
            print(
                "AirAssist shell, would have been set to %s"
                % ("ON" if self._status else "OFF")
            )
            try:
                if self._status:
                    rc = run(shell_command_on)
                else:
                    rc = run(shell_command_off)
                print("Return-Code: %d" % rc.returncode)
            except:
                print("Shell command could not be executed...")
        elif self._method == AA_METHOD_RPI_GPIO:
            print(
                "AirAssist RPI, would have been set to %s"
                % ("ON" if self._status else "OFF")
            )

    def turn_on(self):
        print("AA turn on")
        self.status = True
        if not self.myTimer is None:
            self.myTimer.cancel()
            self.myTimer = None

    def turn_off_timer(self):
        print("Turn-off of AA after %.0f seconds" % self.overshoot)
        self.status = False
        self.myTimer.cancel()
        self.myTimer = None

    def turn_off(self, immediately=None):
        # This will turn off the airassist after xx seconds by default...
        # If you want to turn off the airassist immediately you can provide the parameter
        if immediately is None:
            immediately = False
        if self.overshoot <= 0:
            immediately = True

        if immediately:
            print("AA turn off, immediate")
            self.status = False
        else:
            print("AA turn off, Timer started")
            if self.myTimer is None:
                self.myTimer = Timer(
                    interval=self.overshoot, function=self.turn_off_timer
                )
                self.myTimer.start()
            else:  # Hmm, second call lets kill the timer and stop AA
                print("Forced turn-off of AA")
                self.status = False
                self.myTimer.cancel()
                self.myTimer = None
