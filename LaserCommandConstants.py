# Rapid move is move performed in default mode. This implicitly converts to default mode.
# Move does imply anything about the laser mode.
# Cut means the laser is on for this process.
# Shift means the laser is off for this process.
# Simple means the move must be an octent change. Either +-x, +-y, or +-x and +-y where abs(x) == abs(y).
# COMMAND_PLOT takes a plot object with a .plot() function which generates single pixel plot commands.

COMMAND_LASER_OFF = 1  # Turns laser off
COMMAND_LASER_ON = 2  # Tuns laser on

COMMAND_RAPID_MOVE = 10  # In default mode, performs move
COMMAND_MOVE = 20  # At speed, performs a line move
COMMAND_SHIFT = 21  # At speed, performs a line move
COMMAND_CUT = 22  # At speed, performs a line move
COMMAND_HSTEP = 30  # Causes horizontal raster step
COMMAND_VSTEP = 40  # Causes a vertical raster step
COMMAND_SIMPLE_MOVE = 50  # At speed, performs a octant move (laser current_state)
COMMAND_SIMPLE_SHIFT = 51  # At speed, performs a octant shift (laser off)
COMMAND_SIMPLE_CUT = 52  # At speed, performs a octant cut (laser on)

COMMAND_PLOT = 100
COMMAND_CUT_LINE_TO = 110  # From current position. At speed, performs a line cut
COMMAND_CUT_QUAD_TO = 120  # From current position. At speed, performs a quadratic bezier cut
COMMAND_CUT_CUBIC_TO = 130  # From current position. At speed, performs a cubic bezier cut

COMMAND_MODE_DEFAULT = 1000
COMMAND_MODE_COMPACT = 1001
COMMAND_MODE_CONCAT = 1002

COMMAND_SET_SPEED = 200  # sets the speed for the device
COMMAND_SET_STEP = 201  # sets the raster step for the device
COMMAND_SET_D_RATIO = 202  # sets the d_ratio for the device
COMMAND_SET_DIRECTION = 203  # sets the directions for the device.
COMMAND_SET_INCREMENTAL = 204  # sets the commands to be relative to current position
COMMAND_SET_ABSOLUTE = 205  # sets the commands to be absolute positions.
COMMAND_SET_POSITION = 210  # Without moving sets the current position to the given coord.

COMMAND_HOME = 300  # Homes the device
COMMAND_LOCK = 301  # Locks the rail
COMMAND_UNLOCK = 302  # Unlocks the rail.
