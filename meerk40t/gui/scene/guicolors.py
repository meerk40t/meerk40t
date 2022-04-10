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
        self.default_color = (
            wx.Colour(0xA0, 0x7F, 0xA0),
            wx.Colour(0x00, 0x00, 0xFF, 0x40),
            wx.Colour(0xA0, 0xA0, 0xA0, 128),
            wx.Colour(0x00, 0x00, 0x00),
            wx.Colour("Grey"),
            wx.Colour(0xFF, 0xA0, 0xA0, 0x60),
            wx.Colour(0xA0, 0xA0, 0xA0, 0x40),
            wx.Colour(0x00, 0xFF, 0x00, 0xA0),
            wx.Colour(0xFF, 0x00, 0x00),
            wx.Colour(0x00, 0xFF, 0x00),
            wx.Colour(0x00, 0x00, 0xFF),
            wx.Colour(0xFF, 0xFF, 0xFF)
        )

        self.context.setting(str, "color_manipulation", color_to_str(self.default_color[0].GetRGBA()))
        self.context.setting(str, "color_laserpath", color_to_str(self.default_color[1].GetRGBA()))
        self.context.setting(str, "color_grid", color_to_str(self.default_color[2].GetRGBA()))
        self.context.setting(str, "color_guide", color_to_str(self.default_color[3].GetRGBA()))
        self.context.setting(str, "color_background", color_to_str(self.default_color[4].GetRGBA()))
        self.context.setting(str, "color_magnetline", color_to_str(self.default_color[5].GetRGBA()))
        self.context.setting(str, "color_snap_visible", color_to_str(self.default_color[6].GetRGBA()))
        self.context.setting(str, "color_snap_closeup", color_to_str(self.default_color[7].GetRGBA()))
        self.context.setting(str, "color_selection1", color_to_str(self.default_color[8].GetRGBA()))
        self.context.setting(str, "color_selection2", color_to_str(self.default_color[9].GetRGBA()))
        self.context.setting(str, "color_selection3", color_to_str(self.default_color[10].GetRGBA()))
        self.context.setting(str, "color_bed", color_to_str(self.default_color[11].GetRGBA()))

    def set_default_colors(self):
        '''
        Reset all colors to default values...
        '''
        self.context("set color_manipulation %s" % color_to_str(self.default_color[0].GetRGBA()))
        self.context("set color_laserpath %s" % color_to_str(self.default_color[1].GetRGBA()))
        self.context("set color_grid %s" % color_to_str(self.default_color[2].GetRGBA()))
        self.context("set color_guide %s" % color_to_str(self.default_color[3].GetRGBA()))
        self.context("set color_background %s" % color_to_str(self.default_color[4].GetRGBA()))
        self.context("set color_magnetline %s" % color_to_str(self.default_color[5].GetRGBA()))
        self.context("set color_snap_visible %s" % color_to_str(self.default_color[6].GetRGBA()))
        self.context("set color_snap_closeup %s" % color_to_str(self.default_color[7].GetRGBA()))
        self.context("set color_selection1 %s" % color_to_str(self.default_color[8].GetRGBA()))
        self.context("set color_selection2 %s" % color_to_str(self.default_color[9].GetRGBA()))
        self.context("set color_selection3 %s" % color_to_str(self.default_color[10].GetRGBA()))
        self.context("set color_bed %s" % color_to_str(self.default_color[11].GetRGBA()))

    @property
    def color_manipulation(self):
        try:
            value = str_to_color(self.context.color_manipulation)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[0].GetRGBA())
        return result

    @property
    def color_laserpath(self):
        try:
            value = str_to_color(self.context.color_laserpath)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[1].GetRGBA())
        return result

    @property
    def color_grid(self):
        try:
            value = str_to_color(self.context.color_grid)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[2].GetRGBA())
        return result

    @property
    def color_guide(self):
        try:
            value = str_to_color(self.context.color_guide)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[3].GetRGBA())
        return result

    @property
    def color_background(self):
        try:
            value = str_to_color(self.context.color_background)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[4].GetRGBA())
        return result

    @property
    def color_magnetline(self):
        try:
            value = str_to_color(self.context.color_magnetline)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[5].GetRGBA())
        return result

    @property
    def color_snap_visible(self):
        try:
            value = str_to_color(self.context.color_snap_visible)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[6].GetRGBA())
        return result

    @property
    def color_snap_closeup(self):
        try:
            value = str_to_color(self.context.color_snap_closeup)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[7].GetRGBA())
        return result

    @property
    def color_selection1(self):
        try:
            value = str_to_color(self.context.color_selection1)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[8].GetRGBA())
        return result

    @property
    def color_selection2(self):
        try:
            value = str_to_color(self.context.color_selection2)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[9].GetRGBA())
        return result

    @property
    def color_selection3(self):
        try:
            value = str_to_color(self.context.color_selection3)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[10].GetRGBA())
        return result

    @property
    def color_bed(self):
        try:
            value = str_to_color(self.context.color_bed)
            result = wx.Colour(value)
        except (ValueError, TypeError):
            result = wx.Colour(self.default_color[11].GetRGBA())
        return result
