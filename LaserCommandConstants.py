COMMAND_SIMPLE_MOVE = 0  # At speed, performs a octant move
COMMAND_LASER_OFF = 1  # Turns laser off
COMMAND_LASER_ON = 2  # Tuns laser on
COMMAND_SIMPLE_CUT = 10  # At speed, performs a octant cut (laser on)
COMMAND_SIMPLE_SHIFT = 11  # At speed, performs a octant shift (laser off)
COMMAND_RAPID_MOVE = 20  # In default mode, performs any move
COMMAND_HSTEP = 30  # Causes horizontal raster step
COMMAND_VSTEP = 31  # Causes a vertical raster step

COMMAND_MODE_DEFAULT = 50
COMMAND_MODE_COMPACT = 51
COMMAND_MODE_CONCAT = 52

COMMAND_MOVE_TO = 100  # At speed, performs a line move

COMMAND_CUT_LINE = 81  # At speed, performs a line cut
COMMAND_CUT_CUBIC = 82  # At speed, performs a cubic bezier cut
COMMAND_CUT_QUAD = 83  # At speed, performs a quadratic bezier cut
COMMAND_CUT_ARC = 84  # At speed, performs an arc cut

COMMAND_CUT_LINE_TO = 101  # From current position. At speed, performs a line cut
COMMAND_CUT_CUBIC_TO = 102  # From current position. At speed, performs a cubic bezier cut
COMMAND_CUT_QUAD_TO = 103  # From current position. At speed, performs a quadratic bezier cut
COMMAND_CUT_ARC_TO = 104  # From current position. At speed, performs an arc cut

COMMAND_SET_SPEED = 200  # sets the speed for the device
COMMAND_SET_STEP = 201  # sets the speed for the device

COMMAND_HOME = 300  # Homes the device
COMMAND_LOCK = 301  # Locks the rail
COMMAND_UNLOCK = 302  # Unlocks the rail.
