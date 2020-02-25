"""
Laser Commands are a middle language of commands for spooling and interpreting.

NOTE: Never use the integer value, only the command name. The integer values are
permitted to change.

Some commands have a implication:
'Rapid' implies the command is performed in default mode.
'Cut' implies the laser is on for the command.
'Shift' implies the laser is off for this command.
'Simple' means the movement must be an octant move. Either +-x, +-y, or +-x and +-y where abs(x) == abs(y).

Move alone doesn't imply anything about the laser mode.

COMMAND_PLOT: takes a plot object with a .plot() function which generates simple plot commands.
COMMAND_RASTER: takes a plot object with a .plot() function which generates simple raster commands.

A COMMAND_RESUME would have to be issued in realtime since in a paused state the commands
will not be processed.
"""

COMMAND_LASER_OFF = 1  # Turns laser off
COMMAND_LASER_ON = 2  # Tuns laser on

COMMAND_RAPID_MOVE = 10  # In default mode, performs move
COMMAND_MOVE = 20  # At speed, performs a line move (laser state current)
COMMAND_SHIFT = 21  # At speed, performs a line shift (laser off)
COMMAND_CUT = 22  # At speed, performs a line cut (laser on)
COMMAND_CUT_QUAD = 23  # From current position. At speed, performs a quadratic bezier cut
COMMAND_CUT_CUBIC = 24  # From current position. At speed, performs a cubic bezier cut
COMMAND_HSTEP = 30  # Causes horizontal raster step
COMMAND_VSTEP = 40  # Causes a vertical raster step
COMMAND_WAIT = 50  # Pauses the given time in seconds. (floats accepted).
COMMAND_WAIT_BUFFER_EMPTY = 51  # WAIT until the buffer is empty or below 1 sendable packet.

COMMAND_PLOT = 100
COMMAND_RASTER = 101

COMMAND_MODE_DEFAULT = 1000
COMMAND_MODE_COMPACT = 1001
COMMAND_MODE_CONCAT = 1002

COMMAND_SET_SPEED = 200  # sets the speed for the device
COMMAND_SET_POWER = 201  # sets the PPI power. Out of 1000.
COMMAND_SET_STEP = 202  # sets the raster step for the device
COMMAND_SET_D_RATIO = 203  # sets the d_ratio for the device
COMMAND_SET_ACCELERATION = 204  # sets the acceleration for the device 1-4
COMMAND_SET_DIRECTION = 205  # sets the directions for the device.
COMMAND_SET_INCREMENTAL = 206  # sets the commands to be relative to current position
COMMAND_SET_ABSOLUTE = 207  # sets the commands to be absolute positions.
COMMAND_SET_POSITION = 210  # Without moving sets the current position to the given coord.

COMMAND_HOME = 300  # Homes the device
COMMAND_LOCK = 301  # Locks the rail
COMMAND_UNLOCK = 302  # Unlocks the rail.
COMMAND_BEEP = 320  # Beep.
COMMAND_FUNCTION = 350  # Execute the function given by this command. Blocking.
COMMAND_SIGNAL = 360  # Sends the signal, given: "signal_name", operands.

COMMAND_OPEN = 400  # Opens the channel, general hello.
COMMAND_CLOSE = 500  # The channel will close. No valid commands will be parsed after this.

COMMAND_RESET = 600  # Resets the state, purges buffers
COMMAND_PAUSE = 610  # Issue a pause command.
COMMAND_RESUME = 620  # Issue a resume command.
COMMAND_STATUS = 630  # Issue a status command.
