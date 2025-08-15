#!/usr/bin/env python

"""
LaserSpeed

This is the standard library for converting to and from speed code information for LHYMICRO-GL.
"""

from math import floor


class LaserSpeed:
    """
    MIT License.

    This is the standard library for converting to and from speed code information for LHYMICRO-GL.

    The units in the speed code have acceleration/deceleration factors which slightly modifies the equations used
    to convert between values and speeds. The fundamental units within the speed code values are period-ticks.
    All values relate to a value in the counter to count off the number of oscillations within the
    (typically 22.1184) Mhz crystal. The max value here is 65535, with the addition of a diagonal delay.

    For the M2 board, the original Chinese Software gave a slope of 12120. However, experiments with the actual
    physical speed put this value at 11142, which properly reflects that all speeds tend to be at 91.98% of the
    requested speed.

    The board is ultimately controlling a stepper motor and the speed a stepper motor travels is the result of
    the time between the ticks. Since the crystal oscillator is the same, the delay is controlled by the counted
    oscillations subticks, which gives us the time between stepper motor pulses. Most of the devices we are
    dealing with are 1000 dpi stepper motors, so, for example, to travel at 1 inch a second requires that the
    device tick at 1 kHz. To do this it must delay 1 ms between ticks. This corresponds to a value of 48296 in
    the M2 board. Which has an equation of 65536 - (5120 + 12120T) where T is the period requested in ms. This is
    equal to 25.4 mm/s. If we want a 2 ms delay, which is half the speed (0.5kHz, 0.5 inches/second, 12.7 mm/s)
    we do 65536 - (5120 + 24240) which gives us a value of 36176. This would be encoded as a 16-bit number
    broken up into 2 ascii 3 digit strings between 0-255. 141 for the high bits and 80 for the low bits.
    So CV01410801 where the final character "1" is the acceleration factor since it's within that range.

    The speed in mm/s is also used for determining which acceleration to use and as a factor for some boards
    (B2, M2) the horizontal encoded value. Slowing down the device down while traveling diagonally makes the
    diagonal and orthogonal take the same amount of time (thereby cutting to the same depth). These are the same
    period-ticks units and is simply summed with the 65536 - (b + mT) value in cases that both stepper motors
    are used.
    """

    def __init__(
        self,
        board="M2",
        speed=None,
        raster_step=None,
        d_ratio=None,
        suffix_c=None,
        acceleration=None,
        raster_horizontal=True,
        fix_speeds=False,
        fix_lows=False,
        fix_limit=False,
        power_value=None,
    ):
        self.speed = speed
        self.board = board
        self.d_ratio = d_ratio
        self.raster_step = raster_step

        self.acceleration = acceleration
        self.suffix_c = suffix_c
        self.raster_horizontal = raster_horizontal
        self.fix_speeds = fix_speeds
        self.fix_lows = fix_lows
        self.fix_limit = fix_limit
        self.power_value = power_value
        if isinstance(speed, str):
            # this is a speedcode value.
            (
                code_value,
                accel,
                step_value,
                diagonal,
                raster_step,
                suffix_c,
            ) = parse_speed_code(self.speed)
            b, m = get_equation(
                self.board,
                accel=accel,
                suffix_c=suffix_c,
                fix_speeds=self.fix_speeds,
            )
            self.speed = get_speed_from_value(code_value, b, m)
            self.acceleration = accel
            self.raster_step = raster_step
            self.suffix_c = suffix_c

    def __str__(self):
        return self.speedcode

    def __repr__(self):
        parts = list()
        if self.board != "M2":
            parts.append(f'board="{self.board}"')
        if self.speed is not None:
            parts.append(f"speed={self.speed}")
        if self.d_ratio is not None:
            parts.append(f"d_ratio={self.d_ratio}")
        if self.raster_step != 0:
            parts.append(f"raster_step={self.raster_step}")
        if self.suffix_c is not None:
            parts.append(f"suffix_c={str(self.suffix_c)}")
        if self.acceleration is not None:
            parts.append(f"acceleration={self.acceleration}")
        if self.fix_speeds:
            parts.append(f"fix_speeds={str(self.fix_speeds)}")
        if self.fix_lows:
            parts.append(f"fix_lows={str(self.fix_lows)}")
        if self.fix_limit:
            parts.append(f"fix_limit={str(self.fix_limit)}")
        if not self.raster_horizontal:
            parts.append(f"raster_horizontal={str(self.raster_horizontal)}")
        if self.power_value:
            parts.append(f"power_value={str(self.power_value)}")
        return f"LaserSpeed({', '.join(parts)})"

    @property
    def speedcode(self):
        return get_code_from_speed(
            self.speed,
            self.raster_step,
            self.board,
            self.d_ratio,
            self.acceleration,
            self.suffix_c,
            fix_limit=self.fix_limit,
            fix_speeds=self.fix_speeds,
            fix_lows=self.fix_lows,
            raster_horizontal=self.raster_horizontal,
            power_value=self.power_value,
        )


def get_speed_from_code(speed_code, board="M2", fix_speeds=False):
    """
    Gets the speed expected from a speedcode. Should calculate the expected speed from the data code given.
    @param speed_code: The speedcode to check.
    @param board: The board this speedcode was made for.
    @param fix_speeds: Is this speedcode in a fixed_speed code?
    @return:
    """
    (
        code_value,
        accel,
        step_value,
        diagonal,
        raster_step,
        suffix_c,
    ) = parse_speed_code(speed_code)
    b, m = get_equation(board, accel=accel, suffix_c=suffix_c, fix_speeds=fix_speeds)
    return get_speed_from_value(code_value, b, m)


def get_code_from_speed(
    mm_per_second,
    raster_step=0,
    board="M2",
    d_ratio=None,
    acceleration=None,
    suffix_c=None,
    fix_limit=False,
    fix_speeds=False,
    fix_lows=False,
    raster_horizontal=True,
    power_value=None,
):
    """
    Get a speedcode from a given speed. The raster step appends the 'G' value and uses speed ranges.
    The d_ratio uses the default/auto ratio. The accel is optional and forces the speedcode to work
    for that particular acceleration.

    @param mm_per_second: speed to convert to code.
    @param raster_step: raster step mode to use. Use (g0,g1) tuple for unidirectional valuations.
    @param board: Nano Board Model
    @param d_ratio: M1, M2, B1, B2 have ratio of optional speed
    @param acceleration: Optional force acceleration code rather than default for that speed.
    @param suffix_c: Optional force suffix_c mode for the board. (True forces suffix_c on, False forces it off)
    @param fix_limit: Removes max speed limit.
    @param fix_speeds: Give corrected speed (faster by 8.9%)
    @param fix_lows: Force low speeds into correct bounds.
    @param raster_horizontal: is it rastering with the laser head, or the much heavier bar?
    @return: speed code produced.
    """
    if d_ratio is None:
        d_ratio = 0.261199033289
    if not fix_limit and mm_per_second > 240 and raster_step == 0:
        mm_per_second = 19.05  # Arbitrary default speed for out range value.
    if acceleration is None:
        acceleration = get_acceleration_for_speed(
            mm_per_second,
            raster_step != 0,
            raster_horizontal=raster_horizontal,
            fix_speeds=fix_speeds,
        )
    if suffix_c is None:
        suffix_c = get_suffix_c(board, mm_per_second)

    b, m = get_equation(
        board, accel=acceleration, suffix_c=suffix_c, fix_speeds=fix_speeds
    )
    speed_value = get_value_from_speed(mm_per_second, b, m)

    if fix_lows and speed_value < 0:
        # produced a negative speed value, go ahead and set that to 0
        speed_value = 0
    encoded_speed = encode_16bit(speed_value)
    if power_value is None or power_value >= 1000 or power_value < 0:
        power_suffix = ""
    else:
        power_suffix = f"W{int(power_value):03d}"
    if raster_step != 0:
        # There is no C suffix notation for raster step.
        if isinstance(raster_step, tuple):
            return f"V{encoded_speed}{acceleration:1d}G{abs(raster_step[0]):03d}G{abs(raster_step[1]):03d}{power_suffix}"
        else:
            return f"V{encoded_speed}{acceleration:1d}G{abs(raster_step):03d}{power_suffix}"

    if d_ratio == 0 or board in ("A", "B", "M"):
        # We do not need the diagonal code.
        if raster_step == 0:
            if suffix_c:
                return f"CV{encoded_speed}1C{power_suffix}"
            else:
                return f"CV{encoded_speed}{acceleration:1d}{power_suffix}"
    else:
        step_value = min(int(floor(mm_per_second) + 1), 128)
        frequency_kHz = float(mm_per_second) / 25.4
        try:
            period_in_ms = 1 / frequency_kHz
        except ZeroDivisionError:
            period_in_ms = 0
        d_value = d_ratio * m * period_in_ms / float(step_value)

        if fix_lows:
            if d_value > 0xFFFF:
                d_value = 0xFFFF
            if d_value < 0:
                d_value = 0
        encoded_diagonal = encode_16bit(d_value)
        if suffix_c:
            return (
                f"CV{encoded_speed}1{step_value:03d}{encoded_diagonal}C{power_suffix}"
            )
        else:
            return f"CV{encoded_speed}{acceleration:1d}{step_value:03d}{encoded_diagonal}{power_suffix}"


def parse_speed_code(speed_code):
    """
    Parses a speedcode into the relevant parts these are:
    Prefixed codes CV or V, the code value which is a string of numbers that is either
    7 or 16 characters long. With bugged versions being permitted to be 5 characters longer
    being either 12 or 21 characters long. Since the initial 3 character string becomes an
    8 character string falling out of the 000-255 range and becoming (16777216-v).

    Codes with a suffix-c value are equal to 1/12th with different timings.

    Codes with G-values are raster stepped. Two of these codes implies unidirectional rasters
    but the those are a specific (x,0) step sequence.

    @param speed_code: Speedcode to parse
    @return: code_value, accel, step_value, diagonal, raster_step, suffix_c
    """

    suffix_c = False
    prefix_c = False
    start = 0
    end = len(speed_code)
    if speed_code[start] == "C":
        start += 1
        prefix_c = True
    if speed_code[end - 1] == "C":
        end -= 1
        suffix_c = True
    if speed_code[start : start + 4] == "V167" and speed_code[start + 4] not in (
        "0",
        "1",
        "2",
    ):
        # The 4th character can only be 0,1,2 except for error speeds.
        code_value = decode_16bit(speed_code[start + 1 : start + 12])
        start += 12
        # The value for this speed is so low, it's negative
        # and bit-shifted in 24 bits of a negative number.
        # These are produced by chinese software but are not valid.
    else:
        code_value = decode_16bit(speed_code[start + 1 : start + 7])
        start += 7
    code_value = 65536 - code_value
    accel = int(speed_code[start])
    start += 1

    raster_step = 0
    if speed_code[end - 4] == "G":
        raster_step = int(speed_code[end - 3 : end])
        end -= 4
        # Removes Gxxx
    if speed_code[end - 4] == "G":
        raster_step = (int(speed_code[end - 3 : end]), raster_step)
        end -= 4
        # Removes `Gxxx`, means this it was `GxxxGxxx`.
    step_value = 0
    diagonal = 0
    if (end + 1) - start >= 9:
        step_value = int(speed_code[start : start + 3])
        diagonal = decode_16bit(speed_code[start + 3 : end])
    return code_value, accel, step_value, diagonal, raster_step, suffix_c


def get_value_from_speed(mm_per_second, b, m):
    """
    Calculates speed value from a given speed.
    """
    try:
        frequency_kHz = float(mm_per_second) / 25.4
        period_in_ms = 1.0 / frequency_kHz
        return 65536 - get_value_from_period(period_in_ms, b, m)
    except ZeroDivisionError:
        return 65536 - b


def get_value_from_period(x, b, m):
    """
    Takes in period in ms and converts it to value.
    This is a simple linear relationship.
    """
    return m * x + b


def get_speed_from_value(value, b, m):
    try:
        period_in_ms = get_period_from_value(value, b, m)
        frequency_kHz = 1 / period_in_ms
        return 25.4 * frequency_kHz
    except ZeroDivisionError:
        return 0


def get_period_from_value(y, b, m):
    try:
        return (y - b) / m
    except ZeroDivisionError:
        return float("inf")


def decode_16bit(code):
    b1 = int(code[0:-3])
    if b1 > 16000000:
        b1 -= 16777216  # decode error negative numbers
    if b1 > 0x7FFF:
        b1 = b1 - 0xFFFF
    b2 = int(code[-3:])
    return (b1 << 8) + b2


def encode_16bit(value):
    value = int(value)
    b0 = value & 255
    b1 = (value >> 8) & 0xFFFFFF  # unsigned shift, to emulate bugged form.
    return f"{b1:03d}{b0:03d}"


def get_acceleration_for_speed(
    mm_per_second, raster=False, raster_horizontal=True, fix_speeds=False
):
    """
    Gets the acceleration factor for a particular speed.

    It is known that vertical rastering has different acceleration factors.

    This is not fully mapped out but appeared more in line with non-rastering values.

    @param mm_per_second: Speed to find acceleration value for.
    @param raster: Whether this speed is for a rastering.
    @param raster_horizontal: Whether this speed is for horizontal rastering (top-to-bottom, y-axis speed)
    @param fix_speeds: is fixed speed mode on?
    @return: 1-4: Value for the accel factor.
    """
    if fix_speeds:
        # when speeds are fixed the values from the software were determined based on the flawed codes empirically
        mm_per_second /= 0.919493599053179
    if mm_per_second <= 25.4:
        return 1
    if 25.4 < mm_per_second <= 60:
        return 2
    if raster and raster_horizontal:
        if 60 < mm_per_second < 127:
            return 2
        if 127 <= mm_per_second <= 320:
            return 3
        if 320 <= mm_per_second:
            return 4
    else:
        if 60 < mm_per_second < 127:
            return 3
        if 127 <= mm_per_second:
            return 4


def get_suffix_c(board, mm_per_second=None):
    """
    Due to a bug in the Chinese software the cutoff for the B2 machine is the same as the M2
    at 7, but because if the half-stepping the invalid range the minimum speed is 9.509.
    And this is below the threshold. Speeds between 7-9.509 will be invalid.

    Since the B2 board is intended to duplicate this it will error as well.
    """

    if board == "B2":
        if mm_per_second < 7:
            return True
    if board in ("M2", "M3") and mm_per_second < 7:
        return True
    return False


def get_equation(board, accel=1, suffix_c=False, fix_speeds=False):
    """
    The speed for the M2 was physically checked and found to be inaccurate.
    If strict is used it will seek to strictly emulate the Chinese software.

    The physical device scaled properly with a different slope.

    The correct value has been established for the M2 board. It's guessed at for
    the B2 board being twice the M2 board. It is not known for A or B, B1 or B2
    """
    b = 784.0
    if accel == 3:
        b = 896.0
    if accel == 4:
        b = 1024.0
    if board in ("A", "B", "B1"):
        # A, B, B1 have no known suffix-C equations.
        return b, 2000.0

    m = 12120.0
    if fix_speeds:
        m = 11148.0
    if board == "B2":
        m *= 2
        if suffix_c:
            return b, m / 12.0
    else:
        # Non-B2 b-values
        if accel == 3:
            b = 5632.0
        elif accel == 4:
            b = 6144.0
        else:
            b = 5120.0
        if suffix_c:
            return 8.0, m / 12.0
    return b, m
