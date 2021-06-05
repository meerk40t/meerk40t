"""
Laser Commands are a middle language of commands for spooling and interpreting.

NOTE: Never use the integer value, only the command name. The integer values are
permitted to change.

COMMAND_PLOT: takes a plot object to generate simple plot commands.
Simple plot values are x, y, on. Where x and y are the position in absolute values and on is whether the laser fires
for that particular move command.

A COMMAND_RESUME would have to be issued in realtime since in a paused state the commands are not processed.
"""

COMMAND_LASER_OFF = 1  # Turns laser off
COMMAND_LASER_ON = 2  # Turns laser on
COMMAND_LASER_DISABLE = 5  # Disables the laser
COMMAND_LASER_ENABLE = 6  # Enables the laser
COMMAND_MOVE = 10  # Performs a line move
COMMAND_CUT = 11  # Performs a line cut.
COMMAND_WAIT = 20  # Pauses the given time in seconds. (floats accepted).
COMMAND_WAIT_FINISH = 21  # WAIT until the buffer is finished.
COMMAND_JOG = 30  # Jogs the machine in rapid mode.
COMMAND_JOG_SWITCH = 31  # Jogs the machine in rapid mode.
COMMAND_JOG_FINISH = 32

COMMAND_MODE_RAPID = 50
COMMAND_MODE_FINISHED = 51
COMMAND_MODE_PROGRAM = 52
COMMAND_MODE_RASTER = 53


COMMAND_PLOT = 100  # Takes a cutobject
COMMAND_PLOT_START = 101  # Starts plotter

COMMAND_SET_SPEED = 200  # sets the speed for the device
COMMAND_SET_POWER = 201  # sets the power. Out of 1000. Unknown power method.
COMMAND_SET_PPI = 203  # sets the PPI power. Out of 1000.
COMMAND_SET_PWM = 204  # sets the PWM power. Out of 1000.
COMMAND_SET_STEP = 205  # sets the raster step for the device
COMMAND_SET_DIRECTION = 209  # sets the directions for the device.
COMMAND_SET_OVERSCAN = 206
COMMAND_SET_D_RATIO = 207  # sets the diagonal_ratio for the device
COMMAND_SET_ACCELERATION = 208  # sets the acceleration for the device 1-4
COMMAND_SET_INCREMENTAL = 210  # sets the commands to be relative to current position
COMMAND_SET_ABSOLUTE = 211  # sets the commands to be absolute positions.
COMMAND_SET_POSITION = (
    220  # Without moving sets the current position to the given coord.
)

COMMAND_HOME = 300  # Homes the device
COMMAND_LOCK = 301  # Locks the rail
COMMAND_UNLOCK = 302  # Unlocks the rail.
COMMAND_BEEP = 320  # Beep.
COMMAND_FUNCTION = 350  # Execute the function given by this command. Blocking.
COMMAND_SIGNAL = 360  # Sends the signal, given: "signal_name", operands.

REALTIME_RESET = 1000  # Resets the state, purges buffers
REALTIME_PAUSE = 1010  # Issue a pause command.
REALTIME_RESUME = 1020  # Issue a resume command.
REALTIME_STATUS = 1030  # Issue a status command.
REALTIME_SAFETY_DOOR = 1040  # Issues a forced safety_door state.
REALTIME_JOG_CANCEL = (
    1050  # Issues a jog cancel. This should cancel any jogging being processed.
)
REALTIME_SPEED_PERCENT = 1060  # Set the speed to this percent value of total.
REALTIME_RAPID_PERCENT = 1070  # Sets the rapid speed to this percent value of total.
REALTIME_POWER_PERCENT = 1080  # Sets the power to this percent value of total.
REALTIME_SPEED = 1061  # Set the speed to this percent value of total.
REALTIME_RAPID = 1071  # Sets the rapid speed to this percent value of total.
REALTIME_POWER = 1081  # Sets the power to this percent value of total.
REALTIME_OVERSCAN = 1091  # Sets the overscan amount to this value.
REALTIME_LASER_DISABLE = 1100  # Disables the laser.
REALTIME_LASER_ENABLE = 1101  # Enables the laser.
REALTIME_FLOOD_COOLANT = 1210  # Toggle flood coolant
REALTIME_MIST_COOLANT = 1220  # Toggle mist coolant.


def lasercode_string(code):
    if code == COMMAND_LASER_OFF:
        return "COMMAND_LASER_OFF"  # Turns laser off
    if code == COMMAND_LASER_ON:
        return "COMMAND_LASER_ON"  # Turns laser on
    if code == COMMAND_LASER_DISABLE:
        return "COMMAND_LASER_DISABLE"  # Disables the laser
    if code == COMMAND_LASER_ENABLE:
        return "COMMAND_LASER_ENABLE"  # Enables the laser
    if code == COMMAND_MOVE:
        return "COMMAND_MOVE"  # Performs a line move
    if code == COMMAND_CUT:
        return "COMMAND_CUT"  # Performs a line cut.
    if code == COMMAND_WAIT:
        return "COMMAND_WAIT"  # Pauses the given time in seconds. (floats accepted).
    if code == COMMAND_WAIT_FINISH:
        return "COMMAND_WAIT_FINISH"  # WAIT until the buffer is finished.
    if code == COMMAND_JOG:
        return "COMMAND_JOG"  # Jogs the machine in rapid mode.
    if code == COMMAND_JOG_SWITCH:
        return "COMMAND_JOG_SWITCH"  # Jogs the machine in rapid mode.
    if code == COMMAND_JOG_FINISH:
        return "COMMAND_JOG_FINISH"
    if code == COMMAND_MODE_RAPID:
        return "COMMAND_MODE_RAPID"
    if code == COMMAND_MODE_FINISHED:
        return "COMMAND_MODE_FINISHED"
    if code == COMMAND_MODE_PROGRAM:
        return "COMMAND_MODE_PROGRAM"
    if code == COMMAND_MODE_RASTER:
        return "COMMAND_MODE_RASTER"
    if code == COMMAND_PLOT:
        return "COMMAND_PLOT"  # Takes a cutobject
    if code == COMMAND_PLOT_START:
        return "COMMAND_PLOT_START"  # Starts plotter
    if code == COMMAND_SET_SPEED:
        return "COMMAND_SET_SPEED"  # sets the speed for the device
    if code == COMMAND_SET_POWER:
        return "COMMAND_SET_POWER"  # sets the power. Out of 1000. Unknown power method.
    if code == COMMAND_SET_PPI:
        return "COMMAND_SET_PPI"  # sets the PPI power. Out of 1000.
    if code == COMMAND_SET_PWM:
        return "COMMAND_SET_PWM"  # sets the PWM power. Out of 1000.
    if code == COMMAND_SET_STEP:
        return "COMMAND_SET_STEP"  # sets the raster step for the device
    if code == COMMAND_SET_DIRECTION:
        return "COMMAND_SET_DIRECTION"  # sets the directions for the device.
    if code == COMMAND_SET_OVERSCAN:
        return "COMMAND_SET_OVERSCAN"
    if code == COMMAND_SET_D_RATIO:
        return "COMMAND_SET_D_RATIO"  # sets the diagonal_ratio for the device
    if code == COMMAND_SET_ACCELERATION:
        return "COMMAND_SET_ACCELERATION"  # sets the acceleration for the device 1-4
    if code == COMMAND_SET_INCREMENTAL:
        return "COMMAND_SET_INCREMENTAL"  # sets the commands to be relative to current position
    if code == COMMAND_SET_ABSOLUTE:
        return "COMMAND_SET_ABSOLUTE"  # sets the commands to be absolute positions.
    if code == COMMAND_SET_POSITION:
        return "COMMAND_SET_POSITION"  # Without moving sets the current position to the given coord.
    if code == COMMAND_HOME:
        return "COMMAND_HOME"  # Homes the device
    if code == COMMAND_LOCK:
        return "COMMAND_LOCK"  # Locks the rail
    if code == COMMAND_UNLOCK:
        return "COMMAND_UNLOCK"  # Unlocks the rail.
    if code == COMMAND_BEEP:
        return "COMMAND_BEEP"  # Beep.
    if code == COMMAND_FUNCTION:
        return (
            "COMMAND_FUNCTION"  # Execute the function given by this command. Blocking.
        )
    if code == COMMAND_SIGNAL:  # Sends the signal, given: "signal_name:
        return "COMMAND_SIGNAL"  # Sends the signal, given: "signal_name", operands.
    if code == REALTIME_RESET:
        return "REALTIME_RESET"  # Resets the state, purges buffers
    if code == REALTIME_PAUSE:
        return "REALTIME_PAUSE"  # Issue a pause command.
    if code == REALTIME_RESUME:
        return "REALTIME_RESUME"  # Issue a resume command.
    if code == REALTIME_STATUS:
        return "REALTIME_STATUS"  # Issue a status command.
    if code == REALTIME_SAFETY_DOOR:
        return "REALTIME_SAFETY_DOOR"  # Issues a forced safety_door state.
    if code == REALTIME_JOG_CANCEL:
        return "REALTIME_JOG_CANCEL"  # Issues a jog cancel. This should cancel any jogging being processed.
    if code == REALTIME_SPEED_PERCENT:
        return "REALTIME_SPEED_PERCENT"  # Set the speed to this percent value of total.
    if code == REALTIME_RAPID_PERCENT:
        return "REALTIME_RAPID_PERCENT"  # Sets the rapid speed to this percent value of total.
    if code == REALTIME_POWER_PERCENT:
        return (
            "REALTIME_POWER_PERCENT"  # Sets the power to this percent value of total.
        )
    if code == REALTIME_SPEED:
        return "REALTIME_SPEED"  # Set the speed to this percent value of total.
    if code == REALTIME_RAPID:
        return "REALTIME_RAPID"  # Sets the rapid speed to this percent value of total.
    if code == REALTIME_POWER:
        return "REALTIME_POWER"  # Sets the power to this percent value of total.
    if code == REALTIME_OVERSCAN:
        return "REALTIME_OVERSCAN"  # Sets the overscan amount to this value.
    if code == REALTIME_LASER_DISABLE:
        return "REALTIME_LASER_DISABLE"  # Disables the laser.
    if code == REALTIME_LASER_ENABLE:
        return "REALTIME_LASER_ENABLE"  # Enables the laser.
    if code == REALTIME_FLOOD_COOLANT:
        return "REALTIME_FLOOD_COOLANT"  # Toggle flood coolant
    if code == REALTIME_MIST_COOLANT:
        return "REALTIME_MIST_COOLANT"  # Toggle mist coolant.
