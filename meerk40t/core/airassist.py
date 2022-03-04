"""
AirAssist contains basic code to externally turn on / off air assist .

"""
from subprocess import run
from threading import Timer
from time import sleep
from io import open
import paho.mqtt.client as mqtt

AA_METHOD_NONE = 0
AA_METHOD_MQTT = 1
AA_METHOD_SHELL = 2
AA_METHOD_RPI_GPIO = 3

# Overarching class with logic and timer control
class onoff:
    myTimer = None
    overshoot = 5.0

    def __init__(self):
        self._status = False

    def cmd_on(self):
        return

    def cmd_off(self):
        return

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, a):
        if a:
            self._status = True
            self.cmd_on()
        else:
            self._status = False
            self.cmd_off()

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


# Just do nothing...
class onoff_none(onoff):
    def __init__(self, *args, **kwargs):
        # Call super_init...
        super().__init__(*args, **kwargs)

    def cmd_on(self):
        print("On: doing nothing")

    def cmd_off(self):
        print("Off: doing nothing")


# Use Paho mqtt
class onoff_mqtt(onoff):
    server = "192.168.0.38"
    port = 1883  # Standard
    subject_publish_on = "cmnd/gosund4/POWER1"
    subject_publish_off = "cmnd/gosund4/POWER1"
    subject_subscribe = "stat/gosund4/POWER1"
    msg_on = "ON"
    msg_off = "OFF"

    def __init__(self, *args, **kwargs):
        # Call super_init...
        super().__init__(*args, **kwargs)
        print("MQTT-Establish")
        self.client = mqtt.Client("meerk40t")
        self.client.connect(self.server, self.port)
        self.client.subscribe(self.subject_subscribe)
        self.client.on_message = self.on_subscribe
        self.client.loop_start()

    def on_subscribe(self, client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

    def cmd_on(self):
        print("MQTT-turnon")
        if not self.client is None:
            print("Will publish %s : %s" % (self.subject_publish_on, self.msg_on))
            for i in range(5):
                result = self.client.publish(self.subject_publish_on, self.msg_on)
                if result[0] == 0:
                    continue
                else:
                    print("Failed, another attempt %d" % i)
                    self.client.loop()
                    sleep(0.1)

    def cmd_off(self):
        print("MQTT-turnoff")
        if not self.client is None:
            print("Will publish %s : %s" % (self.subject_publish_off, self.msg_off))
            for i in range(5):
                result = self.client.publish(self.subject_publish_off, self.msg_off)
                if result[0] == 0:
                    continue
                else:
                    print("Failed, another attempt %d" % i)
                    self.client.loop()
                    sleep(0.1)

    def __del__(self):
        if not self.client is None:
            self.client.loop_stop()
            self.client.disconnect()


# Raspberry PI GPIO
"""
class onoff_rpi(onoff):

import RPi.GPIO as GPIO

    RELAIS_1_GPIO = 17
    GPIO_INVERTED = False

    def __init__(self, *args, **kwargs):
        # Call super_init...
        super().__init__(*args, **kwargs)
        if is_raspberrypi():
            GPIO.setmode(GPIO.BCM)  # GPIO Numbers instead of board numbers
            GPIO.setup(self.RELAIS_1_GPIO, GPIO.OUT)  # GPIO Modus zuweisen
            if self.GPIO_INVERTED:
                g_low = GPIO.HIGH
                g_high = GPIO.LOW
            else:
                g_low = GPIO.LOW
                g_high = GPIO.HIGH

    def cmd_on(self):
        print("On: rpi setting pin %d" % self.RELAIS_1_GPIO)
        if is_raspberrypi():
            GPIO.output(self.RELAIS_1_GPIO, self.g_high)  # an

    def cmd_off(self):
        print("On: rpi setting pin %d" % self.RELAIS_1_GPIO)
        if is_raspberrypi():
            GPIO.output(self.RELAIS_1_GPIO, self.g_low)  # aus
"""

# Call external routine on computer
class onoff_shell(onoff):
    shell_command_on = "turn_aa_on.cmd"
    shell_command_off = "turn_aa_off.cmd"

    def __init__(self, *args, **kwargs):
        # Call super_init...
        super().__init__(*args, **kwargs)

    def cmd_on(self):
        try:
            rc = run(self.shell_command_on)
            # print("Return-Code: %d" % rc.returncode)
        except:
            print("Shell command could not be executed...")

    def cmd_off(self):
        try:
            rc = run(self.shell_command_off)
            # print("Return-Code: %d" % rc.returncode)
        except:
            print("Shell command could not be executed...")


class AirAssist:

    handler = None

    def __init__(self):
        self._method = AA_METHOD_NONE
        self._status = False

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, a):
        if (a < AA_METHOD_NONE) or (a > AA_METHOD_RPI_GPIO):
            raise ValueError("Sorry this AirAssist-method isn't supported")
        if a == AA_METHOD_NONE:
            self.handler = onoff_none()
        elif a == AA_METHOD_MQTT:
            print("MQTT-Method called, need to establish connectivity")
            self.handler = onoff_mqtt()
        elif a == AA_METHOD_SHELL:
            print("Shell-Method called")
            self.handler = onoff_shell()
        elif a == AA_METHOD_RPI_GPIO:
            print("RPI-Method called")
            self.handler = onoff_none()  # onoff_rpi()

        self._method = a

    @property
    def status(self):
        if self.handler is None:
            print("getstatus failed")
            return False
        else:
            print("getstatus")
            return self.handler.status

    @status.setter
    def status(self, a):
        if not self.handler is None:
            print("setstatus")
            self.handler.status = a

    def turn_on(self):
        if not self.handler is None:
            print("turnon")
            self.handler.turn_on()

    def turn_off(self, immediately=None):
        if not self.handler is None:
            print("turnoff")
            self.handler.turn_off(immediately)
