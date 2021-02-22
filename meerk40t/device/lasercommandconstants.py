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
COMMAND_SET_PWM = 203  # sets the PWM power. Out of 1000.
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
