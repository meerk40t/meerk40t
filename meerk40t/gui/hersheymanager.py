from glob import glob
from math import isinf
import os
import wx
from meerk40t.core.units import UNITS_PER_INCH, Length
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.icons import icons8_choose_font_50, STD_ICON_SIZE
from meerk40t.kernel import get_safe_path
from meerk40t.extra.hershey import create_linetext_node

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade

_ = wx.GetTranslation

def create_preview_image(context, fontfile):
    simplefont = os.path.basename(fontfile)
    base, ext = os.path.splitext(fontfile)
    bmpfile = base + ".png"
    pattern = "The quick brown fox..."
    node = create_linetext_node(context, 0, 0, pattern, font=simplefont, font_size=Length("12pt"))
    if node is None:
        return
    if node.bounds is None:
        return
    make_raster = context.elements.lookup("render-op/make_raster")
    if make_raster is None:
        return
    xmin, ymin, xmax, ymax = node.bounds
    if isinf(xmin):
        # No bounds for selected elements
        return
    width = xmax - xmin
    height = ymax - ymin
    dpi = 150
    dots_per_units = dpi / UNITS_PER_INCH
    new_width = width * dots_per_units
    new_height = height * dots_per_units
    new_height = max(new_height, 1)
    new_width = max(new_width, 1)
    bitmap = make_raster(
        [node],
        bounds=node.bounds,
        width=new_width,
        height=new_height,
        bitmap = True,
    )
    try:
        bitmap.SaveFile(bmpfile, wx.BITMAP_TYPE_PNG)
    except (OSError, IOError, RuntimeError, PermissionError, FileNotFoundError):
        pass

def load_create_preview_file(context, fontfile):
    bitmap = None
    base, ext = os.path.splitext(fontfile)
    bmpfile = base + ".png"
    if not os.path.exists(bmpfile):
        create_preview_image(context, fontfile)
    if os.path.exists(bmpfile):
        bitmap = wx.Bitmap()
        bitmap.LoadFile(bmpfile, wx.BITMAP_TYPE_PNG)
    return bitmap

class PanelFontSelect(wx.Panel):

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        mainsizer = wx.BoxSizer(wx.VERTICAL)

        self.fonts = []

        sizer_fonts = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Fonts (double-click to use)")), wx.VERTICAL)
        mainsizer.Add(sizer_fonts, 1, wx.EXPAND, 0)

        self.list_fonts = wx.ListBox(self, wx.ID_ANY)
        sizer_fonts.Add(self.list_fonts, 1, wx.EXPAND, 0)

        self.bmp_preview = wx.StaticBitmap(self, wx.ID_ANY)
        self.bmp_preview.SetMinSize((-1, 70))
        sizer_fonts.Add(self.bmp_preview, 0, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_fonts.Add(sizer_buttons, 0, wx.EXPAND, 0)

        self.btn_bigger = wx.Button(self, wx.ID_ANY, "++")
        sizer_buttons.Add(self.btn_bigger, 0, wx.EXPAND, 0)

        self.btn_smaller = wx.Button(self, wx.ID_ANY, "--")
        sizer_buttons.Add(self.btn_smaller, 0, wx.EXPAND, 0)

        lbl_spacer = wx.StaticText(self, wx.ID_ANY, "")
        sizer_buttons.Add(lbl_spacer, 1, 0, 0)

        self.SetSizer(mainsizer)

        self.Layout()

        self.Bind(wx.EVT_LISTBOX, self.on_list_font, self.list_fonts)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_font_dclick, self.list_fonts)
        self.Bind(wx.EVT_BUTTON, self.on_btn_bigger, self.btn_bigger)
        self.Bind(wx.EVT_BUTTON, self.on_btn_smaller, self.btn_smaller)

        # end wxGlade
        safe_dir = os.path.realpath(get_safe_path(self.context.kernel.name))
        self.context.setting(str, "font_directory", safe_dir)
        fontdir = self.context.font_directory
        self.load_directory(fontdir)

    def load_directory(self, fontdir):
        self.fonts = []
        self.list_fonts.Clear()
        if os.path.exists(fontdir):
            self.context.font_directory = fontdir
            for ext in ("*.shx", "*.jhf"):
                for p in glob(os.path.join(fontdir, ext.lower())):
                    fn = os.path.basename(p)
                    if fn not in self.fonts:
                        self.fonts.append(fn)
                for p in glob(os.path.join(fontdir, ext.upper())):
                    fn = os.path.basename(p)
                    if fn not in self.fonts:
                        self.fonts.append(fn)
        self.list_fonts.SetItems(self.fonts)
        # index = -1
        # lookfor = getattr(self.context, "sxh_preferred", "")

    def on_btn_bigger(self, event):
        scene = getattr(self.context.root, "mainscene", None)
        if scene is not None:
            scene.signal("linetext;bigger")

    def on_btn_smaller(self, event):
        scene = getattr(self.context.root, "mainscene", None)
        if scene is not None:
            scene.signal("linetext;smaller")

    def on_list_font_dclick(self, event):
        index = self.list_fonts.GetSelection()
        if index >= 0:
            fontname = self.fonts[index]
            scene = getattr(self.context.root, "mainscene", None)
            if scene is not None:
                scene.signal("linetext;font", fontname)

    def on_list_font(self, event):
        if self.list_fonts.GetSelection() >= 0:
            font_file = self.fonts[self.list_fonts.GetSelection()]
            full_font_file = os.path.join(self.context.font_directory, font_file)
            bmp = load_create_preview_file(self.context, full_font_file)
            # if bmp is not None:
            #     bmap_bundle = wx.BitmapBundle().FromBitmap(bmp)
            # else:
            #     bmap_bundle = wx.BitmapBundle()
            # self.bmp_preview.SetBitmap(bmap_bundle)
            if bmp is None:
                bmp = wx.NullBitmap
            self.bmp_preview.SetBitmap(bmp)


class HersheyFontSelector(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(450, 550, submenu="", *args, **kwds)
        self.panel = PanelFontSelect(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_choose_font_50.GetBitmap(resize=25))
        # _icon.CopyFromBitmap(icons8_computer_support_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Font-Selection"))

    def window_open(self):
        pass

    def window_close(self):
        pass

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        # Suppress = True
        return ("", "Font-Selector", True)


class PanelFontManager(wx.Panel):

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        mainsizer = wx.BoxSizer(wx.VERTICAL)

        self.fonts = []

        self.text_info = wx.TextCtrl(self, wx.ID_ANY,
            _("MeerK40t can use Hershey-Fonts or Autocad-86 shape fonts designed to be rendered purely with vectors.\n" +
              "They can be scaled, burned like any other vector shape and are therefore very versatile.\n" +
              "See more: https://en.wikipedia.org/wiki/Hershey_fonts , "
            ), style=wx.BORDER_NONE | wx.TE_MULTILINE | wx.TE_READONLY)

        self.text_info.SetMinSize((-1, 90))
        sizer_info = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Information")), wx.HORIZONTAL)
        mainsizer.Add(sizer_info, 0, wx.EXPAND, 0)
        sizer_info.Add(self.text_info, 1, wx.EXPAND, 0)

        sizer_directory = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Font-Directory")), wx.HORIZONTAL)
        mainsizer.Add(sizer_directory, 0, wx.EXPAND, 0)

        self.text_fontdir = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_directory.Add(self.text_fontdir, 1, wx.EXPAND, 0)

        self.btn_dirselect = wx.Button(self, wx.ID_ANY, "...")
        sizer_directory.Add(self.btn_dirselect, 0, wx.EXPAND, 0)

        sizer_fonts = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Fonts")), wx.VERTICAL)
        mainsizer.Add(sizer_fonts, 1, wx.EXPAND, 0)

        self.list_fonts = wx.ListBox(self, wx.ID_ANY)
        sizer_fonts.Add(self.list_fonts, 1, wx.EXPAND, 0)

        self.bmp_preview = wx.StaticBitmap(self, wx.ID_ANY)
        self.bmp_preview.SetMinSize((-1, 70))
        sizer_fonts.Add(self.bmp_preview, 0, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_fonts.Add(sizer_buttons, 0, wx.EXPAND, 0)

        self.btn_add = wx.Button(self, wx.ID_ANY,_("Import"))
        sizer_buttons.Add(self.btn_add, 0, wx.EXPAND, 0)

        self.btn_delete = wx.Button(self, wx.ID_ANY, _("Delete"))
        sizer_buttons.Add(self.btn_delete, 0, wx.EXPAND, 0)

        lbl_spacer = wx.StaticText(self, wx.ID_ANY, "")
        sizer_buttons.Add(lbl_spacer, 1, 0, 0)

        self.webresources = [
            "https://github.com/kamalmostafa/hershey-fonts/tree/master/hershey-fonts",
            "http://iki.fi/sol/hershey/index.html",
            "https://www.mepwork.com/2017/11/autocad-shx-fonts.html",
        ]
        choices = [_("Goto a font-source..."), _("Hershey Fonts - #1"), _("Hershey Fonts - #2"), _("Autocad-SHX-Fonts"),]
        self.combo_webget = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY,)
        self.combo_webget.SetSelection(0)
        sizer_buttons.Add(self.combo_webget, 0, wx.EXPAND, 0)

        self.SetSizer(mainsizer)

        self.Layout()

        self.Bind(wx.EVT_TEXT, self.on_text_directory, self.text_fontdir)
        self.Bind(wx.EVT_BUTTON, self.on_btn_directory, self.btn_dirselect)
        self.Bind(wx.EVT_LISTBOX, self.on_list_font, self.list_fonts)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_font_dclick, self.list_fonts)
        self.Bind(wx.EVT_BUTTON, self.on_btn_import, self.btn_add)
        self.Bind(wx.EVT_BUTTON, self.on_btn_delete, self.btn_delete)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_webget, self.combo_webget)
        # end wxGlade
        safe_dir = os.path.realpath(get_safe_path(self.context.kernel.name))
        self.context.setting(str, "font_directory", safe_dir)
        self.text_fontdir.SetValue(self.context.font_directory)

    def on_text_directory(self, event):
        fontdir = self.text_fontdir.GetValue()
        self.fonts = []
        self.list_fonts.Clear()
        if os.path.exists(fontdir):
            self.context.font_directory = fontdir
            for ext in ("*.shx", "*.jhf"):
                for p in glob(os.path.join(fontdir, ext.lower())):
                    fn = os.path.basename(p)
                    if fn not in self.fonts:
                        self.fonts.append(fn)
                for p in glob(os.path.join(fontdir, ext.upper())):
                    fn = os.path.basename(p)
                    if fn not in self.fonts:
                        self.fonts.append(fn)
        self.list_fonts.SetItems(self.fonts)

    def on_btn_directory(self, event):
        fontdir = self.text_fontdir.GetValue()
        dlg = wx.DirDialog (
            None, _("Choose font directory"), fontdir, style=wx.DD_DEFAULT_STYLE
            #| wx.DD_DIR_MUST_EXIST
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.text_fontdir.SetValue(dlg.GetPath())
        # Only destroy a dialog after you're done with it.
        dlg.Destroy()

    def on_list_font_dclick(self, event):
        if self.list_fonts.GetSelection() >= 0:
            font_file = self.fonts[self.list_fonts.GetSelection()]
            self.context.setting(str, "shx_preferred", None)
            self.context.shx_preferred = font_file

            # full_font_file = os.path.join(self.context.font_directory, font_file)
           #  print(f"Fontfile: {font_file}, full: {full_font_file}")

    def on_list_font(self, event):
        if self.list_fonts.GetSelection() >= 0:
            font_file = self.fonts[self.list_fonts.GetSelection()]
            full_font_file = os.path.join(self.context.font_directory, font_file)
            bmp = load_create_preview_file(self.context, full_font_file)
            # if bmp is not None:
            #     bmap_bundle = wx.BitmapBundle().FromBitmap(bmp)
            # else:
            #     bmap_bundle = wx.BitmapBundle()
            # self.bmp_preview.SetBitmap(bmap_bundle)
            if bmp is None:
                bmp = wx.NullBitmap
            self.bmp_preview.SetBitmap(bmp)

    def on_btn_import(self, event):
        wildcard = "Vector-Fonts|*.shx;*.SHX;*.jhf;*.JHF|Hershey-Fonts|*.jhf;*.JHF|Autocad-Fonts|*.shx;*.SHX"
        dlg = wx.FileDialog(
            self,
            message=_("Select a font-file to be imported into the the font-directory {fontdir}").format(fontdir=self.context.font_directory),
            defaultDir="", defaultFile="",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        )
        font_files = None
        paths = None
        if dlg.ShowModal() == wx.ID_OK:
            font_files = dlg.GetPaths()
        # Only destroy a dialog after you're done with it.
        dlg.Destroy()
        stats =  [0, 0]  # Successful, errors
        if font_files is None:
            return
        for sourcefile in font_files:
            basename = os.path.basename(sourcefile)
            destfile = os.path.join(self.context.font_directory, basename)
            # print (f"Source File: {sourcefile}\nTarget: {destfile}")
            try:
                with open(sourcefile, 'rb') as f, open(destfile, 'wb') as g:
                    while True:
                        block = f.read(1*1024*1024)  # work by blocks of 1 MB
                        if not block:  # end of file
                            break
                        g.write(block)
                stats[0] += 1
                create_preview_image(self.context, destfile)
            except (OSError, IOError, RuntimeError, PermissionError, FileNotFoundError):
                stats[1] += 1
        wx.MessageBox(
            _("Font-Import completed.\nImported: {ok}\nFailed: {fail}\nTotal: {total}").format(ok=stats[0], fail=stats[1], total=stats[0] + stats[1]),
            _("Import completed"),
            wx.OK | wx.ICON_INFORMATION
        )
        # Reload....
        self.on_text_directory(None)

    def on_btn_delete(self, event):
        if self.list_fonts.GetSelection() >= 0:
            font_file = self.fonts[self.list_fonts.GetSelection()]
            full_font_file = os.path.join(self.context.font_directory, font_file)
            if wx.MessageBox(
                _("Do you really want to delete this font: {font}").format(font=font_file),
                _("Confirm"),
                wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
            ) == wx.YES:
                try:
                    os.remove(full_font_file)
                    # Reload dir...
                    self.on_text_directory(None)
                except (OSError, IOError, RuntimeError, PermissionError, FileNotFoundError):
                    pass

    def on_combo_webget(self, event):
        idx = self.combo_webget.GetSelection() - 1
        if idx>=0:
            url = self.webresources[idx]
            if wx.MessageBox(
                _("You will be led now to a source in the web, where you can download free fonts.\n" +
                "Please be respect individual property rights!\nDestination: {url}\n").format(url=url) +
                _("Unpack the downloaded archive after the download and select the extracted files with help of the 'Import'-Button."),
                _("Confirm"),
                wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION,
            ) == wx.YES:
                import webbrowser

                webbrowser.open(url, new=0, autoraise=True)


# end of class FontManager

class HersheyFontManager(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(551, 234, submenu="", *args, **kwds)
        self.panel = PanelFontManager(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_choose_font_50.GetBitmap(resize=25))
        # _icon.CopyFromBitmap(icons8_computer_support_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Font-Manager"))

    def window_open(self):
        pass

    def window_close(self):
        pass

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        return ("", "Font-Manager")

    @staticmethod
    def sub_register(kernel):
        buttonsize = int(STD_ICON_SIZE)
        kernel.register(
            "button/config/HersheyFontManager",
            {
                "label": _("Font-Manager"),
                "icon": icons8_choose_font_50,
                "tip": _("Open alignment dialog with advanced options"),
                "action": lambda v: kernel.console("window toggle HersheyFontManager\n"),
                "size": buttonsize,
            },
        )
