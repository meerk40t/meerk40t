from copy import copy


class Parameters:
    """
    Parameters is a helper class which seeks to normalize, validate, and extract values from an underlying
    dictionary. This class isn't required and in many cases it's better and more consistent to extract the
    values of various settings directly as keys in the dictionary. This class is provided to simplify those set
    and get operations as well as to normalize the keys used to store and extract the information. Since different
    drivers can have completely different and alien settings the dictionary is the primary storage for these
    settings. Settings outside the scope of this class are still legal and will be passed to the drivers which
    may or may not implement or respect them.
    """

    def __init__(self, obj=None):
        self.color = "transparent"
        self.line_color = "black"
        self.default = False
        self.allowed_attributes = None
        self.output = True
        self.stopop = False
        self.raster_step_x = 0
        self.raster_step_y = 0
        self.desc = ""
        self.dpi = 500
        self.overscan = "0.5mm"
        self.speed = 10.0  # Changes based on operation type.
        self.power = 1000
        self.frequency = 20.0
        self.rapid_speed = 100.0
        self.laser_enabled = True
        self.ppi_enabled = True
        self.dot_length = 1
        self.dot_length_custom = False
        self.shift_enabled = False
        self.passes = 0
        self.passes_custom = False
        self.raster_direction = 1
        self.raster_swing = False

        #####################
        # HATCH PROPERTIES
        #####################
        self.hatch_type = "scanline"
        self.hatch_angle = "0deg"
        self.hatch_distance = "1mm"

        #####################
        # PENBOX PROPERTIES
        #####################
        self.penbox_pass = None
        self.penbox_value = None

        #####################
        # ACCEL PROPERTIES
        #####################
        self.acceleration = None
        self.acceleration_custom = False

        #####################
        # DRATIO PROPERTIES
        #####################
        self.dratio = 0.261
        self.dratio_custom = False

        #####################
        # RASTER POSITION PROPERTIES
        #####################
        self.raster_preference_top = 0
        self.raster_preference_right = 0
        self.raster_preference_left = 0
        self.raster_preference_bottom = 0

        #####################
        # JOG PROPERTIES
        #####################
        self.jog_distance = 15
        self.jog_enable = True

        #####################
        # DWELL PROPERTIES
        #####################
        self.dwell_time = 50.0

        #####################
        # INPUT PROPERTIES
        #####################
        self.input_value = 0
        self.input_mask = 0
        self.input_message = None

        #####################
        # OUTPUT PROPERTIES
        #####################
        self.output_value = 0
        self.output_mask = 0
        self.output_message = None

        if obj is not None:
            for k, v in obj.__dict__.items():
                if k.startswith("_"):
                    continue
                self.__dict__[k] = v

    def __copy__(self):
        return Parameters(self)

    def derive(self):
        return copy(self)

    @property
    def implicit_dotlength(self):
        if not self.dot_length_custom:
            return 1
        return self.dot_length

    @property
    def implicit_passes(self):
        if not self.passes_custom:
            return 1
        return self.passes

    @property
    def implicit_accel(self):
        if not self.acceleration_custom:
            return None
        return self.acceleration

    @property
    def implicit_d_ratio(self):
        if not self.dratio_custom:
            return None
        return self.dratio
