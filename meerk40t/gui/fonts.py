import wx

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


def wxfont_to_svg(textnode):
    """
    Translates all wxfont - properties to their svg-equivalents
    @param textnode:
    @return:
    """

    anychanges = False
    if not hasattr(textnode, "wxfont"):
        textnode.wxfont = wx.Font()
        anychanges = True

    wxfont = textnode.wxfont

    if textnode.font_size != wxfont.GetPointSize():
        textnode.font_size = wxfont.GetPointSize()
        anychanges = True
    if textnode.font_weight != str(wxfont.GetWeight()):
        textnode.font_weight = str(wxfont.GetWeight())
        anychanges = True
    if textnode.font_family != wx_to_svg_family_name(wxfont):
        textnode.font_family = wx_to_svg_family_name(wxfont)
        anychanges = True
    if textnode.font_style != wx_to_svg_fontstyle(wxfont):
        textnode.font_style = wx_to_svg_fontstyle(wxfont)
        anychanges = True
    if textnode.underline != wxfont.GetUnderlined():
        textnode.underline = wxfont.GetUnderlined()
        anychanges = True
    if textnode.strikethrough != wxfont.GetStrikethrough():
        textnode.strikethrough = wxfont.GetStrikethrough()
        anychanges = True
    if anychanges:
        textnode.modified()
