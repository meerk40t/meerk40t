import re
import wx

from meerk40t.core.units import PX_PER_INCH

# from meerk40t.core.node import node
# from meerk40t.svgelements import Text
# Svg-text has the following properties (and default values)
# .anchor = "start"  # start, middle, end.
# .font_family = "san-serif"
# .font_size = 16.0  # 16px font 'normal' 12pt font
# .font_weight = 400
# NEW since svg 1.7:
# .font_style = "normal" * DONE
# .font_variant = "normal" * NOT SUPPORTED (ornaments, small-caps etc.)
# .font_stretch = "normal" * NOT SUPPORTED (normal, condensed, expanded etc.)
# .line_height = 16.0
# Removed:
# .font_face

def wxfont_to_svg(svgtextnode):
    ###
    ### Translates all wxfont - properties to their svg-equivalents
    ###
    def build_family_name(wxfont):
        fontface = wxfont.GetFaceName()
        if any([ char in fontface for char in [" ", ","] ]):
            fontface = "'" + fontface + "'"
        family = ""
        ff = wxfont.GetFamily()
        if ff == wx.FONTFAMILY_DECORATIVE:
            family = ", fantasy"
        elif ff == wx.FONTFAMILY_ROMAN:
            family = ", serif"
        elif ff == wx.FONTFAMILY_SCRIPT:
            family = ", cursive"
        elif ff == wx.FONTFAMILY_SWISS:
            family = ", sans-serif"
        elif ff == wx.FONTFAMILY_MODERN:
            family = ", sans-serif"
        elif ff == wx.FONTFAMILY_TELETYPE:
            family = ", monospace"
        else:
            family = ", sans-serif"
        family_name = fontface + family
        if family_name.startswith(","):
            family_name = family_name[1:].strip()
        return family_name


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

    family = build_family_name(wxfont)
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

    svgtextnode.text.font_style = fontstyle

    svgtextnode.underline = wxfont.GetUnderlined()
    svgtextnode.strikethrough = wxfont.GetStrikethrough()

def svgfont_to_wx(svgtextnode):
    ###
    ### Translates all svg-text-properties to their wxfont-equivalents
    ###
    def get_font_names(node):
        face_family = node.text.font_family
        fontface = ""
        family = ""
        if face_family is not None and face_family!="":
            components = re.findall(r"(?:[^\s,']|'(?:\\.|[^'\.])*')+", face_family)
            if len(components)>0:
                fontface = components[0]
                family = components[-1]
            else:
                family = components[0]
        return fontface, family

    if not hasattr(svgtextnode, "wxfont"):
        svgtextnode.wxfont = wx.Font()
    wxfont = svgtextnode.wxfont
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
    font_face, font_family = get_font_names(svgtextnode)
    ff = font_family
    if ff == "fantasy":
        family = wx.FONTFAMILY_DECORATIVE
    elif ff == "serif":
        family = wx.FONTFAMILY_ROMAN
    elif ff == "cursive":
        family = wx.FONTFAMILY_SCRIPT
    elif ff == "sans-serif":
        family = wx.FONTFAMILY_SWISS
    elif ff == "monospace":
        family = wx.FONTFAMILY_TELETYPE
    else:
        family = wx.FONTFAMILY_SWISS
    wxfont.SetFamily(family)
    if font_face != "":
        if font_face[0] == "'":
            font_face = font_face.strip("'")
        okay = wxfont.SetFaceName(font_face)
    else:
        try:
            tst = wxfont.GetFaceName()
            okay = True
        except:
            okay = False
    if not okay:
        if font_family != "":
            if font_family[0] == "'":
                font_family = font_family.strip("'")
            ff = font_family
            # Will try Family Name instead
            okay = wxfont.SetFaceName(ff)
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
        wxfont.SetPointSize(int(fsize))
    wxfont.SetUnderlined(svgtextnode.underline)
    wxfont.SetStrikethrough(svgtextnode.strikethrough)
