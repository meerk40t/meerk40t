import wx

def color_to_str(value):
    temp = hex(value)
    # The representation is backwards ABGR --> change
    result = temp[:2] + temp[8:] + temp[6:8] + temp[4:6]+ temp[2:4]
    # print("c2s from %s = %s" % (hex(value), result))
    return result

def str_to_color(value):
    # The representation needs to be ABGR --> change
    if len(value)<=8:
        value = value + "FF" # append opacity
    result = value[:2] + value[8:] + value[6:8] + value[4:6]+ value[2:4]
    return int(result, base=16)

class GuiColors():
    '''
    Provides and stores all relevant colors for a scene
    '''
    def __init__(self, context):
        self.context = context
        self.default_color = {
            "manipulation": wx.Colour(0xA0, 0x7F, 0xA0),
            "laserpath": wx.Colour(0x00, 0x00, 0xFF, 0x40),
            "grid": wx.Colour(0xA0, 0xA0, 0xA0, 128),
            "guide": wx.Colour(0x00, 0x00, 0x00),
            "background": wx.Colour("Grey"),
            "magnetline": wx.Colour(0xFF, 0xA0, 0xA0, 0x60),
            "snap_visible": wx.Colour(0xA0, 0xA0, 0xA0, 0x40),
            "snap_closeup": wx.Colour(0x00, 0xFF, 0x00, 0xA0),
            "selection1": wx.Colour(0xFF, 0x00, 0x00),
            "selection2": wx.Colour(0x00, 0xFF, 0x00),
            "selection3": wx.Colour(0x00, 0x00, 0xFF),
            "bed": wx.Colour(0xFF, 0xFF, 0xFF)
        }

        self.context.setting(str, "color_manipulation", color_to_str(self.default_color["manipulation"].GetRGBA()))
        self.context.setting(str, "color_laserpath", color_to_str(self.default_color["laserpath"].GetRGBA()))
        self.context.setting(str, "color_grid", color_to_str(self.default_color["grid"].GetRGBA()))
        self.context.setting(str, "color_guide", color_to_str(self.default_color["guide"].GetRGBA()))
        self.context.setting(str, "color_background", color_to_str(self.default_color["background"].GetRGBA()))
        self.context.setting(str, "color_magnetline", color_to_str(self.default_color["magnetline"].GetRGBA()))
        self.context.setting(str, "color_snap_visible", color_to_str(self.default_color["snap_visible"].GetRGBA()))
        self.context.setting(str, "color_snap_closeup", color_to_str(self.default_color["snap_closeup"].GetRGBA()))
        self.context.setting(str, "color_selection1", color_to_str(self.default_color["selection1"].GetRGBA()))
        self.context.setting(str, "color_selection2", color_to_str(self.default_color["selection2"].GetRGBA()))
        self.context.setting(str, "color_selection3", color_to_str(self.default_color["selection3"].GetRGBA()))
        self.context.setting(str, "color_bed", color_to_str(self.default_color["bed"].GetRGBA()))

    def set_default_colors(self):
        '''
        Reset all colors to default values...
        '''
        self.context.color_manipulation = color_to_str(self.default_color["manipulation"].GetRGBA())
        self.context.color_laserpath = color_to_str(self.default_color["laserpath"].GetRGBA())
        self.context.color_grid = color_to_str(self.default_color["grid"].GetRGBA())
        self.context.color_guide = color_to_str(self.default_color["guide"].GetRGBA())
        self.context.color_background = color_to_str(self.default_color["background"].GetRGBA())
        self.context.color_magnetline = color_to_str(self.default_color["magnetline"].GetRGBA())
        self.context.color_snap_visible = color_to_str(self.default_color["snap_visible"].GetRGBA())
        self.context.color_snap_closeup = color_to_str(self.default_color["snap_closeup"].GetRGBA())
        self.context.color_selection1 = color_to_str(self.default_color["selection1"].GetRGBA())
        self.context.color_selection2 = color_to_str(self.default_color["selection2"].GetRGBA())
        self.context.color_selection3 = color_to_str(self.default_color["selection3"].GetRGBA())
        self.context.color_bed = color_to_str(self.default_color["bed"].GetRGBA())

    @property
    def color_manipulation(self):
        try:
            value = str_to_color(self.context.color_manipulation)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["manipulation"].GetRGBA())
            self.context.color_manipulation = color_to_str(self.default_color["manipulation"].GetRGBA())
        return result

    @property
    def color_laserpath(self):
        try:
            value = str_to_color(self.context.color_laserpath)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["laserpath"].GetRGBA())
            self.context.color_laserpath = color_to_str(self.default_color["laserpath"].GetRGBA())
        return result

    @property
    def color_grid(self):
        try:
            value = str_to_color(self.context.color_grid)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["grid"].GetRGBA())
            self.context.color_grid = color_to_str(self.default_color["grid"].GetRGBA())
        return result

    @property
    def color_guide(self):
        try:
            value = str_to_color(self.context.color_guide)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["guide"].GetRGBA())
            self.context.color_guide = color_to_str(self.default_color["guide"].GetRGBA())
        return result

    @property
    def color_background(self):
        try:
            value = str_to_color(self.context.color_background)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["background"].GetRGBA())
            self.context.color_background = color_to_str(self.default_color["background"].GetRGBA())
        return result

    @property
    def color_magnetline(self):
        try:
            value = str_to_color(self.context.color_magnetline)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["magnetline"].GetRGBA())
            self.context.color_magnetline = color_to_str(self.default_color["magnetline"].GetRGBA())
        return result

    @property
    def color_snap_visible(self):
        try:
            value = str_to_color(self.context.color_snap_visible)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["snap_visible"].GetRGBA())
            self.context.color_snap_visible = color_to_str(self.default_color["snap_visible"].GetRGBA())
        return result

    @property
    def color_snap_closeup(self):
        try:
            value = str_to_color(self.context.color_snap_closeup)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["snap_closeup"].GetRGBA())
            self.context.color_snap_closeup = color_to_str(self.default_color["snap_closeup"].GetRGBA())
        return result

    @property
    def color_selection1(self):
        try:
            value = str_to_color(self.context.color_selection1)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["selection1"].GetRGBA())
            self.context.color_selection1 = color_to_str(self.default_color["selection1"].GetRGBA())
        return result

    @property
    def color_selection2(self):
        try:
            value = str_to_color(self.context.color_selection2)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["selection2"].GetRGBA())
            self.context.color_selection2 = color_to_str(self.default_color["selection2"].GetRGBA())
        return result

    @property
    def color_selection3(self):
        try:
            value = str_to_color(self.context.color_selection3)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["selection3"].GetRGBA())
            self.context.color_selection3 = color_to_str(self.default_color["selection3"].GetRGBA())
        return result

    @property
    def color_bed(self):
        try:
            value = str_to_color(self.context.color_bed)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color["bed"].GetRGBA())
            self.context.color_bed = color_to_str(self.default_color["bed"].GetRGBA())
        return result
