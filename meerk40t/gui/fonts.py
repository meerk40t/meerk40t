import wx

from meerk40t.core.units import PX_PER_INCH

"""
Svg-text has the following properties (and default values)
 .anchor = "start"  # start, middle, end.
 .font_family = "san-serif"
 .font_size = 16.0  # 16px font 'normal' 12pt font
 .font_weight = 400
NEW since svg 1.7:
 .font_style = "normal" * DONE
 .font_variant = "normal" * NOT SUPPORTED (ornaments, small-caps etc.)
 .font_stretch = "normal" * NOT SUPPORTED (normal, condensed, expanded etc.)
 .line_height = 16.0
Removed:
 .font_face
 
 The wx.FONTWEIGHT_THIN does not exist in wxPython 4.0.x and thus isn't used. 
"""


CONVERSION_SVG_WX = {
    "fantasy": wx.FONTFAMILY_DECORATIVE,
    "serif": wx.FONTFAMILY_ROMAN,
    "cursive": wx.FONTFAMILY_SCRIPT,
    "sans-serif": wx.FONTFAMILY_SWISS,
    "monospace": wx.FONTFAMILY_TELETYPE,
}
CONVERSION_WX_SVG = {
    wx.FONTFAMILY_DECORATIVE: "fantasy",
    wx.FONTFAMILY_ROMAN: "serif",
    wx.FONTFAMILY_SCRIPT: "cursive",
    wx.FONTFAMILY_SWISS: "sans-serif",
    wx.FONTFAMILY_MODERN: "sans-serif",
    wx.FONTFAMILY_TELETYPE: "monospace",
}


def wx_to_svg_family_name(wxfont):
    fontface = wxfont.GetFaceName()
    if " " in fontface or "," in fontface:
        fontface = f"'{fontface}'"
    family = CONVERSION_WX_SVG.get(wxfont.GetFamily(), "sans-serif")
    return f"{fontface}, {family}"


def wx_to_svg_fontstyle(wxfont):
    ff = wxfont.GetStyle()
    if ff == wx.FONTSTYLE_NORMAL:
        return "normal"
    elif ff == wx.FONTSTYLE_ITALIC:
        return "italic"
    elif ff == wx.FONTSTYLE_SLANT:
        return "oblique"
    return "normal"


def wxfont_to_svg(svgtextnode):
    """
    Translates all wxfont - properties to their svg-equivalents
    @param svgtextnode:
    @return:
    """

    if not hasattr(svgtextnode, "wxfont"):
        svgtextnode.wxfont = wx.Font()
    wxfont = svgtextnode.wxfont

    # A point is 1/72 of an inch
    factor = PX_PER_INCH / 72
    svgtextnode.text.font_size = wxfont.GetPointSize() * factor
    svgtextnode.text.font_weight = str(wxfont.GetWeight())
    svgtextnode.text.font_family = wx_to_svg_family_name(wxfont)
    svgtextnode.text.font_style = wx_to_svg_fontstyle(wxfont)
    svgtextnode.underline = wxfont.GetUnderlined()
    svgtextnode.strikethrough = wxfont.GetStrikethrough()


def svg_to_wx_family(svgtextnode, wxfont):
    font_list = svgtextnode.text.font_list
    for ff in font_list:
        if ff == "fantasy":
            family = wx.FONTFAMILY_DECORATIVE
            wxfont.SetFamily(family)
            return
        elif ff == "serif":
            family = wx.FONTFAMILY_ROMAN
            wxfont.SetFamily(family)
            return
        elif ff == "cursive":
            family = wx.FONTFAMILY_SCRIPT
            wxfont.SetFamily(family)
            return
        elif ff == "sans-serif":
            family = wx.FONTFAMILY_SWISS
            wxfont.SetFamily(family)
            return
        elif ff == "monospace":
            family = wx.FONTFAMILY_TELETYPE
            wxfont.SetFamily(family)
            return
        if wxfont.SetFaceName(ff):
            # We found a correct face name.
            return


def svg_to_wx_fontstyle(svgtextnode, wxfont):
    ff = svgtextnode.text.font_style
    if ff == "normal":
        fontstyle = wx.FONTSTYLE_NORMAL
    elif ff == "italic":
        fontstyle = wx.FONTSTYLE_ITALIC
    elif ff == "oblique":
        fontstyle = wx.FONTSTYLE_SLANT
    else:
        fontstyle = wx.FONTSTYLE_NORMAL
    wxfont.SetStyle(fontstyle)


def svgfont_to_wx(svgtextnode):
    """
    Translates all svg-text-properties to their wxfont-equivalents
    @param svgtextnode:
    @return:
    """
    if not hasattr(svgtextnode, "wxfont"):
        svgtextnode.wxfont = wx.Font()
    wxfont = svgtextnode.wxfont
    try:
        wxfont.SetNumericWeight(svgtextnode.text.weight)  # Gets numeric weight.
    except AttributeError:
        # Running version wx4.0. No set Numeric Weight, can only set bold or normal.
        weight = svgtextnode.text.weight
        wxfont.SetWeight(wx.FONTWEIGHT_BOLD if weight > 600 else wx.FONTWEIGHT_NORMAL)  # Gets numeric weight.

    svg_to_wx_family(svgtextnode, wxfont)
    svg_to_wx_fontstyle(svgtextnode, wxfont)

    # A point is 1/72 of an inch
    factor = 72 / PX_PER_INCH
    font_size = svgtextnode.text.font_size * factor
    if font_size < 1:
        if font_size > 0:
            textx = 0
            texty = 0
            if hasattr(svgtextnode.text, "x"):
                textx = svgtextnode.text.x
            if hasattr(svgtextnode.text, "y"):
                texty = svgtextnode.text.y
            svgtextnode.matrix.pre_scale(font_size, font_size, textx, texty)
            font_size = 1
            svgtextnode.text.font_size = font_size  # No zero sized fonts.
    try:
        wxfont.SetFractionalPointSize(font_size)
    except AttributeError:
        wxfont.SetPointSize(int(font_size))
    wxfont.SetUnderlined(svgtextnode.underline)
    wxfont.SetStrikethrough(svgtextnode.strikethrough)
