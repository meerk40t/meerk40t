import wx

from meerk40t.core.units import PX_PER_INCH

# from meerk40t.core.node import node
# from meerk40t.svgelements import Text


def wxfont_to_svg(svgtextnode):
    ###
    ### Translates all wxfont - properties to their svg-equivalents
    ###
    if not hasattr(svgtextnode, "wxfont"):
        svgtextnode.wxfont = wx.Font()

    wxfont = svgtextnode.wxfont
    # A point is 1/72 of an inch
    factor = PX_PER_INCH / 72
    svgtextnode.text.font_size = wxfont.GetPointSize() * factor

    fw = wxfont.GetWeight()
    if fw in (wx.FONTWEIGHT_THIN, wx.FONTWEIGHT_EXTRALIGHT, wx.FONTWEIGHT_LIGHT):
        fontweight = "lighter"
    elif fw in (wx.FONTWEIGHT_NORMAL, wx.FONTWEIGHT_MEDIUM):
        fontweight = "normal"
    elif fw in (wx.FONTWEIGHT_SEMIBOLD, wx.FONTWEIGHT_BOLD):
        fontweight = "bold"
    elif fw in (wx.FONTWEIGHT_EXTRABOLD, wx.FONTWEIGHT_HEAVY, wx.FONTWEIGHT_EXTRAHEAVY):
        fontweight = "bolder"
    else:
        fontweight = "normal"
    svgtextnode.text.font_weight = fontweight

    svgtextnode.text.font_face = wxfont.GetFaceName()
    ff = wxfont.GetFamily()
    if ff == wx.FONTFAMILY_DECORATIVE:
        family = "fantasy"
    elif ff == wx.FONTFAMILY_ROMAN:
        family = "serif"
    elif ff == wx.FONTFAMILY_SCRIPT:
        family = "cursive"
    elif ff == wx.FONTFAMILY_SWISS:
        family = "sans-serif"
    elif ff == wx.FONTFAMILY_MODERN:
        family = "sans-serif"
    elif ff == wx.FONTFAMILY_TELETYPE:
        family = "monospace"
    else:
        family = "sans-serif"
    svgtextnode.text.font_family = family

    ff = wxfont.GetStyle()
    if ff == wx.FONTSTYLE_NORMAL:
        fontstyle = "normal"
    elif ff == wx.FONTSTYLE_ITALIC:
        fontstyle = "italic"
    elif ff == wx.FONTSTYLE_SLANT:
        fontstyle = "oblique"
    else:
        fontstyle = "normal"

    svgtextnode.font_style = fontstyle


def svgfont_to_wx(svgtextnode):
    ###
    ### Translates all svg-text-properties to their wxfont-equivalents
    ###
    if not hasattr(svgtextnode, "wxfont"):
        svgtextnode.wxfont = wx.Font()
    wxfont = svgtextnode.wxfont
    # A point is 1/72 of an inch
    factor = 72 / PX_PER_INCH
    fsize = svgtextnode.text.font_size * factor
    if fsize < 1:
        if fsize > 0:
            textx = 0
            texty = 0
            if hasattr(svgtextnode.text, "x"):
                textx = svgtextnode.text.x
            if hasattr(svgtextnode.text, "y"):
                texty = svgtextnode.text.y
            svgtextnode.matrix.pre_scale(fsize, fsize, textx, texty)
            fsize = 1
            svgtextnode.text.font_size = fsize  # No zero sized fonts.
    try:
        wxfont.SetFractionalPointSize(fsize)
    except AttributeError:
        wxfont.SetSize(int(fsize))

    fw = svgtextnode.text.font_weight
    if fw == "lighter":
        fontweight = wx.FONTWEIGHT_THIN
    elif fw == "normal":
        fontweight = wx.FONTWEIGHT_NORMAL
    elif fw == "bold":
        fontweight = wx.FONTWEIGHT_BOLD
    elif fw == "bolder":
        fontweight = wx.FONTWEIGHT_EXTRABOLD
    else:
        fontweight = wx.FONTWEIGHT_NORMAL
    wxfont.SetWeight(fontweight)

    ff = svgtextnode.text.font_family

    if ff == "fantasy":
        family = wx.FONTFAMILY_DECORATIVE
    elif ff == "serif":
        family = wx.FONTFAMILY_ROMAN
    elif ff == "cursive":
        family = wx.FONTFAMILY_SCRIPT
    elif ff == "sans-serif":
        family = wx.FONTFAMILY_MODERN
    elif ff == "monospace":
        family = wx.FONTFAMILY_TELETYPE
    else:
        family = wx.FONTFAMILY_SWISS
    wxfont.SetFamily(family)
    okay = False
    if not svgtextnode.text.font_face is None:
        if svgtextnode.text.font_face[0] == "'":
            svgtextnode.text.font_face = svgtextnode.text.font_face.strip("'")
        okay = wxfont.SetFaceName(svgtextnode.text.font_face)
    if not okay:
        if not svgtextnode.text.font_family is None:
            if svgtextnode.text.font_family[0] == "'":
                svgtextnode.text.font_family = svgtextnode.text.font_family.strip("'")
            ff = svgtextnode.text.font_family
            # Will try Family Name instead
            okay = wxfont.SetFaceName(ff)
            if okay:
                svgtextnode.text.font_face = ff

    ff = svgtextnode.font_style
    if ff == "normal":
        fontstyle = wx.FONTSTYLE_NORMAL
    elif ff == "italic":
        fontstyle = wx.FONTSTYLE_ITALIC
    elif ff == "oblique":
        fontstyle = wx.FONTSTYLE_SLANT
    else:
        fontstyle = wx.FONTSTYLE_NORMAL
    wxfont.SetStyle(fontstyle)
