#!/usr/bin/env python

from math import floor


class LaserSpeed:
    """
    MIT License.

    This is the standard library for converting to and from speed code information for LHYMICRO-GL.

    The units in the speed code have particular bands/gears which slightly modifies the equations used
    to convert between values and speeds. The fundamental units within the speed code values are period-ticks.
    All values relate to a value in the counter to count off the number of oscillations within the
    (typically 22.1184) Mhz crystal. The max value here is 65535, potentially with the addition of a diagonal delay.

    For the M2 board, the original Chinese Software gave a slope of 12120. However experiments with the actual
    physical speed put this value at 11142, which properly reflects all speeds tend to be at 91.98% of the requested
    speed.

    The board is ultimately controlling a stepper motor and the speed a stepper motor travels is the result of
    the time between the ticks. Since the crystal oscillator is the same, the delay is controlled by the counted
    oscillations subticks, which gives us the time between stepper motor pulses. Most of the devices we are
    dealing with are 1000 dpi stepper motors, so, for example, to travel at 1 inch a second requires that the
    device tick at 1 kHz. To do this it must delay 1 ms between ticks. This corresponds to a value of 48296 in
    the M2 board. Which has an equation of 65536 - (5120 + 12120T) where T is the period requested in ms. This is
    equal to 25.4 mm/s. If we want a 2 ms delay, which is half the speed (0.5kHz, 0.5 inches/second, 12.7 mm/s)
    we do 65536 - (5120 + 24240) which gives us a value of 36176. This would be encoded as a 16 bit number
    broken up into 2 ascii 3 digit strings between 0-255. 141 for the high bits and 80 for the low bits.
    So CV01410801 where the final character "1" is the gearing equation we used.

    The speed in mm/s is also used for determining which gearing to use and as a factor for the horizontal
    encoded value, for some boards (B2, M2). Slowing down the device down while traveling diagonal to make the
    diagonal and orthogonal take the same amount of time (thereby cutting to the same depth). These are the same
    period-ticks units and is simply summed with the 65536 - (b + mT) value in cases that both stepper motors
    are used.
    """

    def __init__(self):
        pass

    @staticmethod
    def get_speed_from_code(speed_code, board="LASER-M2"):
        code_value, gear, step_value, diagonal, raster_step = LaserSpeed.parse_speed_code(speed_code)
        b, m, gear = LaserSpeed.get_gearing(board, gear=gear, uses_raster_step=raster_step != 0)
        return LaserSpeed.get_speed_from_value(code_value, b, m)

    @staticmethod
    def get_code_from_speed(mm_per_second, raster_step=0, board="LASER-M2", d_ratio=0.261199033289, gear=None):
        """
        Get a speedcode from a given speed. The raster step appends the 'G' value and uses speed ranges.
        The d_ratio uses the default/auto ratio. The gearing is optional and forces the speedcode to work
        for that particular gearing. Gear=0 refers to C-suffix notation speeds.

        :param mm_per_second: speed to convert to code.
        :param raster_step: raster step mode to use.
        :param board: Nano Board Model to do the conversion for.
        :param d_ratio: M1, M2, B1, B2 have ratio of optional speed
        :param gear: Optional force gearing rather than default gear for that speed.
        :return: speed code produced.
        """
        if mm_per_second > 240 and raster_step == 0:
            mm_per_second = 19.05  # Arbitrary default speed for out range value.
        b, m, gear = LaserSpeed.get_gearing(board, mm_per_second, raster_step != 0, gear)

        speed_value = LaserSpeed.get_value_from_speed(mm_per_second, b, m)
        encoded_speed = LaserSpeed.encode_value(speed_value)

        if raster_step != 0:
            if gear == 0:  # There is no C suffix notation for gear raster step.
                gear = 1
            return "V%s%1dG%03d" % (
                encoded_speed,
                gear,
                raster_step
            )

        if d_ratio == 0 or board == "A" or board == "B" or board == "M" or board == "LASER-A" or board == "LASER-B" or board == "LASER-M":
            # We do not need the diagonal code.
            if raster_step == 0:
                if gear == 0:
                    return "CV%s1C" % (
                        encoded_speed
                    )
                else:
                    return "CV%s%1d" % (
                        encoded_speed,
                        gear)
        else:
            step_value = min(int(floor(mm_per_second) + 1), 128)
            frequency_kHz = float(mm_per_second) / 25.4
            try:
                period_in_ms = 1 / frequency_kHz
            except ZeroDivisionError:
                period_in_ms = 0
            d_value = d_ratio * m * period_in_ms / float(step_value)
            encoded_diagonal = LaserSpeed.encode_value(d_value)
            if gear == 0:
                return "CV%s1%03d%sC" % (
                    encoded_speed,
                    step_value,
                    encoded_diagonal
                )
            else:
                return "CV%s%1d%03d%s" % (
                    encoded_speed,
                    gear,
                    step_value,
                    encoded_diagonal)

    @staticmethod
    def parse_speed_code(speed_code):
        is_shortened = False
        normal = False
        if speed_code[0] == "C":
            speed_code = speed_code[1:]
            normal = True
        if speed_code[-1] == "C":
            speed_code = speed_code[:-1]
            is_shortened = True
            # This is a -C suffix speed.
        if "V1677" in speed_code or "V1676" in speed_code or \
                "V1675" in speed_code or "V1674" in speed_code:
            # The 4th character can only be 0,1,2 except for error speeds.
            code_value = LaserSpeed.decode_value(speed_code[1:12])
            speed_code = speed_code[12:]
            # The value for this speed is so low, it's negative
            # and bit-shifted in 24 bits of a negative number.
        else:
            code_value = LaserSpeed.decode_value(speed_code[1:7])
            speed_code = speed_code[7:]
        code_value = 65536 - code_value
        gear = int(speed_code[0])
        speed_code = speed_code[1:]

        if is_shortened:
            gear = 0  # Flags as step zero during code error.
        raster_step = 0

        if normal:
            step_value = 0
            diagonal = 0
            if len(speed_code) > 1:
                step_value = int(speed_code[:3])
                diagonal = LaserSpeed.decode_value(speed_code[3:])
            return code_value, gear, step_value, diagonal, raster_step
        else:
            if "G" in speed_code:
                raster_step = int(speed_code[-3:])
            return code_value, gear, 1, 1, raster_step

    @staticmethod
    def get_value_from_speed(mm_per_second, b, m):
        """
        Takes in speed in mm per second and returns speed value.
        """
        try:
            frequency_kHz = float(mm_per_second) / 25.4
            period_in_ms = 1.0 / frequency_kHz
            return 65536 - LaserSpeed.get_value_from_period(period_in_ms, b, m)
        except ZeroDivisionError:
            return 65536 - b

    @staticmethod
    def get_value_from_period(x, b, m):
        """
        Takes in period in ms and converts it to value.
        This is a simple linear relationship.
        """
        return m * x + b

    @staticmethod
    def get_speed_from_value(value, b, m):
        try:
            period_in_ms = LaserSpeed.get_period_from_value(value, b, m)
            frequency_kHz = 1 / period_in_ms
            return 25.4 * frequency_kHz
        except ZeroDivisionError:
            return 0

    @staticmethod
    def get_period_from_value(y, b, m):
        try:
            return (y - b) / m
        except ZeroDivisionError:
            return float('inf')

    @staticmethod
    def decode_value(code):
        b1 = int(code[0:-3])
        if b1 > 16000000:
            b1 -= 16777216  # decode error negative numbers
        if b1 > 0x7FFF:
            b1 = b1 - 0xFFFF
        b2 = int(code[-3:])
        return (b1 << 8) + b2

    @staticmethod
    def encode_value(value):
        value = int(value)
        b0 = value & 255
        b1 = (value >> 8) & 0xFFFFFF  # unsigned shift, to emulate bugged form.
        return "%03d%03d" % (b1, b0)

    @staticmethod
    def get_gear_for_speed(mm_per_second, uses_raster_step=False):
        if mm_per_second <= 25.4:
            return 1
        if 25.4 < mm_per_second <= 60:
            return 2
        if not uses_raster_step:
            if 60 < mm_per_second < 127:
                return 3
            if 127 <= mm_per_second:
                return 4
        else:
            if 60 < mm_per_second < 127:
                return 2
            if 127 <= mm_per_second <= 320:
                return 3
            if 320 <= mm_per_second:
                return 4

    @staticmethod
    def get_gearing(board, mm_per_second=None, uses_raster_step=False, gear=None):
        """The gearing equations are divided into two sets distinct groups.
        The LASER-[ABM][12]? values and the [ABM][12]? values. If the 'BOARD'
        prefix is specified it will give the correct value to create a given speed.
        Without the prefix, it will give the values the chinese software produced.

        For the M2 board this was physically checked and found to be inaccurate.
        The physical device scaled properly with a different slope.

        This value has been established for the M2 board. It's guessed at for the B2
        board being twice the M2 board. However it is not known for A or B, B1 or B2
        In this case LASER-X returns the same value as X.
        """
        if gear is None:
            gear = LaserSpeed.get_gear_for_speed(mm_per_second, uses_raster_step)
            if board == "B2":
                if mm_per_second < 7:
                    # speeds below 9.509 will be in error. But the Chinese Software drew the line for suffix-C at
                    # 7 so, this package does as well. Even though it means impossible speeds at between 7 and 9.509.
                    if uses_raster_step:
                        return 784.0, 2020.0, 1
                        # C-suffix code, pretending to be gear 1, the results are raster
                        # speedcodes that do not actually provide full circle capabilities.
                        # There are no permitted very slow raster speed codes. But to properly
                        # emulate the Chinese software this is added because that is how it
                        # works in that package.
                    else:
                        gear = 0
                        # Use C-suffice notation.
            elif board == "LASER-B2":
                if mm_per_second < 8.75:
                    if uses_raster_step:
                        return 784.0, 1858.0, 1
                    # Speeds below 8.75 will be in error.
                    # The LASER-XX spec is intended to fix things, so the error code range of the B2 are dismissed
                    gear = 0  # Use C-suffix notion below this level.
            elif board == "M2":
                if mm_per_second < 7:
                    gear = 0  # Use C-suffix notion below this level.
            elif board == "LASER-M2":
                if mm_per_second < 7:
                    gear = 0  # Use C-suffix notion below this level.
        A_B_B1 = [
            (784.0, 2000.0, 0),  # A, B, B1 have no known suffix-C equations.
            (784.0, 2000.0, 1),
            (784.0, 2000.0, 2),
            (896.0, 2000.0, 3),
            (1024.0, 2000.0, 4)
        ]
        M_M1 = [
            (5120.0, 12120.0, 0),  # M, M1 has no known suffix-C equations.
            (5120.0, 12120.0, 1),
            (5120.0, 12120.0, 2),
            (5632.0, 12120.0, 3),
            (6144.0, 12120.0, 4)
        ]
        BOARD_M_M1 = [
                (5120.0, 11148.0, 0),  # M has no known suffix-C equations.
                (5120.0, 11148.0, 1),
                (5120.0, 11148.0, 2),
                (5632.0, 11148.0, 3),
                (6144.0, 11148.0, 4)
                # The physical speed elements were guessed at with regard to the M2 that were tested
            ]
        speedcode_dict = {
            "A": A_B_B1,
            "B": A_B_B1,
            "B1": A_B_B1,
            "B2": [
                (784.0, 2020.0, 0),
                (784.0, 24240.0, 1),
                (784.0, 24240.0, 2),
                (896.0, 24240.0, 3),
                (1024.0, 24240.0, 4)
            ],
            "M": M_M1,
            "M1": M_M1,
            "M2": [
                (8.0, 1010.0, 0),
                (5120.0, 12120.0, 1),
                (5120.0, 12120.0, 2),
                (5632.0, 12120.0, 3),
                (6144.0, 12120.0, 4)
            ],
            "LASER-A": A_B_B1,
            # It is unknown if these values are correct with regard to physical speed.
            "LASER-B": A_B_B1,
            # It is unknown if these values are correct with regard to physical speed.
            "LASER-B1": A_B_B1,
            # It is unknown if these values are correct with regard to physical speed.
            "LASER-B2": [
                (784.0, 1858.0, 0),
                (784.0, 22296.0, 1),
                (784.0, 22296.0, 2),
                (896.0, 22296.0, 3),
                (1024.0, 22296.0, 4)
                # The physical speed elements were assumed to be 2x the real M2 values.
            ],
            "LASER-M": BOARD_M_M1,
            "LASER-M1": BOARD_M_M1,
            "LASER-M2": [
                (8.0, 929.0, 0),
                (5120.0, 11148.0, 1),
                (5120.0, 11148.0, 2),
                (5632.0, 11148.0, 3),
                (6144.0, 11148.0, 4)
            ],
        }
        return speedcode_dict[board][gear]

    @staticmethod
    def validate_speed(mm_per_second, board, uses_raster_step=False):
        """
        Validate a speed.

        Some boards and speeds have bugs or issues, calling this will put your speed to the nearest value
        that does not have any issues.

        :param mm_per_second: speed to validate
        :param board: Nano Board Model
        :param uses_raster_step: is this speed for a raster_step
        :return: validated speed.
        """
        if board == "A" or board == "B" or board == "B1":
            if mm_per_second < 0.785:
                return 0.785
        elif board == "LASER-A" or board == "LASER-B" or board == "LASER-B1":
            # The boards manufacturer says specifically the correct slowest speed is  0.762 mm
            # This suggests the speed for these boards is likely 3% slower.
            if mm_per_second < 0.785:
                return 0.785
        elif board == "LASER-B2":
            if mm_per_second < 8.750 and uses_raster_step:
                return 8.750
            if mm_per_second < 0.730:
                return 0.730
        elif board == "B2":
            if mm_per_second < 9.509 and (mm_per_second >= 7 or uses_raster_step):
                return 9.509
            if mm_per_second < 0.793:
                return 0.793
        elif board == "M" or board == "M1":
            if mm_per_second < 5.096:
                return 5.096
        elif board == "LASER-M" or board == "LASER-M1":
            if mm_per_second < 4.688:
                return 4.688
        elif board == "M2":
            if mm_per_second < 5.096 and uses_raster_step:
                return 5.096
            if mm_per_second < 0.392:
                return 0.392
        elif board == "LASER-M2":
            if mm_per_second < 4.688 and uses_raster_step:
                return 4.688
            if mm_per_second < 0.361:
                return 0.361
        if uses_raster_step:
            if mm_per_second > 500:
                return 500.0
        else:
            if mm_per_second > 240:
                return 240.0
        return mm_per_second
