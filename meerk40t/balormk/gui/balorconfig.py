import wx

from meerk40t.core.units import Length
from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.device.gui.effectspanel import EffectsPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import dip_size, TextCtrl, StaticBoxSizer

from meerk40t.kernel import Job, signal_listener

_ = wx.GetTranslation

class CorrectionPanel(wx.Panel):

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.SetHelpText("balorcorrection")
        self.parent = args[0]
        self.txt_x_top_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.txt_x_top_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")

        self.txt_y_top_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.txt_y_top_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.txt_y_top_3 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")

        self.txt_x_mid_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.txt_x_mid_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")

        self.txt_y_bottom_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.txt_y_bottom_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.txt_y_bottom_3 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
       
        self.txt_x_bottom_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        self.txt_x_bottom_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="length")
        
        self.label_info = wx.StaticText(self, wx.ID_ANY)
        self.image_info = wx.StaticBitmap(self, wx.ID_ANY, size=wx.Size(100, 100))
        self.btn_define = wx.Button(self, id=wx.ID_ANY, label=_("Define"))
        self.create_images()
        self.set_layout()
        self.set_logic()
        self.Layout()

    def on_button(self, event):
        self.context("widget_corfile\n")

    def set_layout(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sub_sizer = wx.BoxSizer(wx.HORIZONTAL)

        left_sizer = StaticBoxSizer(self, id=wx.ID_ANY, label=_("9-Point correction"), orientation=wx.VERTICAL)
        line_1 = wx.BoxSizer(wx.HORIZONTAL)
        line_2 = wx.BoxSizer(wx.HORIZONTAL)
        line_3 = wx.BoxSizer(wx.HORIZONTAL)
        line_4 = wx.BoxSizer(wx.HORIZONTAL)
        line_5 = wx.BoxSizer(wx.HORIZONTAL)

        line_1.AddStretchSpacer(1)
        line_1.Add(self.txt_x_top_1, 2, wx.EXPAND, 0)
        line_1.Add(self.txt_x_top_2, 2, wx.EXPAND, 0)
        line_1.AddStretchSpacer(1)

        line_2.AddStretchSpacer(1)
        line_2.Add(self.txt_y_top_1, 2, wx.EXPAND, 0)
        line_2.Add(self.txt_y_top_2, 2, wx.EXPAND, 0)
        line_2.Add(self.txt_y_top_3, 2, wx.EXPAND, 0)
        line_2.AddStretchSpacer(1)

        line_3.AddStretchSpacer(1)
        line_3.Add(self.txt_x_mid_1, 2, wx.EXPAND, 0)
        line_3.Add(self.txt_x_mid_2, 2, wx.EXPAND, 0)
        line_3.AddStretchSpacer(1)

        line_4.AddStretchSpacer(1)
        line_4.Add(self.txt_y_bottom_1, 2, wx.EXPAND, 0)
        line_4.Add(self.txt_y_bottom_2, 2, wx.EXPAND, 0)
        line_4.Add(self.txt_y_bottom_3, 2, wx.EXPAND, 0)
        line_4.AddStretchSpacer(1)

        line_5.AddStretchSpacer(1)
        line_5.Add(self.txt_x_bottom_1, 2, wx.EXPAND, 0)
        line_5.Add(self.txt_x_bottom_2, 2, wx.EXPAND, 0)
        line_5.AddStretchSpacer(1)

        left_sizer.Add(line_1, 0, wx.EXPAND)  # wx.ALIGN_CENTER_HORIZONTAL)
        left_sizer.Add(line_2, 0, wx.EXPAND)  # wx.ALIGN_CENTER_HORIZONTAL)
        left_sizer.Add(line_3, 0, wx.EXPAND)  # wx.ALIGN_CENTER_HORIZONTAL)
        left_sizer.Add(line_4, 0, wx.EXPAND)  # wx.ALIGN_CENTER_HORIZONTAL)
        left_sizer.Add(line_5, 0, wx.EXPAND)  # wx.ALIGN_CENTER_HORIZONTAL)
        
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        right_sizer.Add(self.label_info, 0, wx.EXPAND, 0)
        right_sizer.Add(self.image_info, 0, wx.EXPAND, 0)

        sub_sizer.Add(left_sizer, 1, wx.EXPAND, 0)
        sub_sizer.Add(right_sizer, 0, wx.EXPAND, 0)
        main_sizer.Add(sub_sizer, 0, wx.EXPAND, 0)
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        btn_sizer.Add(self.btn_define, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)

    def set_logic(self):
        self.Bind(wx.EVT_BUTTON, self.on_button, self.btn_define)
        self.txt_x_top_1.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_1", 1))
        self.txt_x_top_2.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_2", 2))

        self.txt_y_top_1.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_8", 3))
        self.txt_y_top_2.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_11", 4))
        self.txt_y_top_3.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_3", 5))
        
        self.txt_x_mid_1.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_9", 6))
        self.txt_x_mid_2.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_10", 7))

        self.txt_y_bottom_1.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_7", 8))
        self.txt_y_bottom_2.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_12", 9))
        self.txt_y_bottom_3.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_4", 10))
        
        self.txt_x_bottom_1.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_6", 11))
        self.txt_x_bottom_2.Bind(wx.EVT_SET_FOCUS, self.on_enter("cf_5", 12))
    
    def on_enter(self, atribute, index):
        # Will update the image to show which measurement needs to be taken
        def handler(event):
            self.update_image(index)
        
        return handler

    def update_image(self, index):
        self.label_info.SetLabel(f"Index: {index}")
        self.image_info.SetBitmap(self.preview[index])

    def create_images(self):
        self.preview={}
        bmap_size = 100
        for idx in range(13):
            imgBit = wx.Bitmap(bmap_size, bmap_size)
            dc = wx.MemoryDC(imgBit)
            dc.SelectObject(imgBit)
            dc.SetBackground(wx.WHITE_BRUSH)
            dc.Clear()
            dc.SetPen(wx.BLACK_PEN)
            offs = 5
            bm_full = offs + (bmap_size - 2 * offs)
            bm_half = offs + (bmap_size - 2 * offs) // 2
            dc.DrawLine(offs, offs, bm_full, offs)
            dc.DrawLine(offs, bm_half, bm_full, bm_half)
            dc.DrawLine(offs, bm_full, bm_full, bm_full)
            dc.DrawLine(offs, offs, offs, bm_full)
            dc.DrawLine(bm_half, offs, bm_half, bm_full)
            dc.DrawLine(bm_full, offs, bm_full, bm_full)

            pen = wx.Pen(wx.BLUE)
            pen.SetWidth(5)
            dc.SetPen(pen)
            if idx == 1:
                dc.DrawLine(offs, offs, bm_half, offs)
            elif idx == 2:
                dc.DrawLine(bm_half, offs, bm_full, offs)
            elif idx == 3:
                dc.DrawLine(offs, offs, offs, bm_half)
            elif idx == 4:
                dc.DrawLine(bm_half, offs, bm_half, bm_half)
            elif idx == 5:
                dc.DrawLine(bm_full, offs, bm_full, bm_half)
            elif idx == 6:
                dc.DrawLine(offs, bm_half, bm_half, bm_half)
            elif idx == 7:
                dc.DrawLine(bm_half, bm_half, bm_full, bm_half)
            elif idx == 8:
                dc.DrawLine(offs, bm_half, offs, bm_full)
            elif idx == 9:
                dc.DrawLine(bm_half, bm_half, bm_half, bm_full)
            elif idx == 10:
                dc.DrawLine(bm_full, bm_half, bm_full, bm_full)
            elif idx == 11:
                dc.DrawLine(offs, bm_full, bm_half, bm_full)
            elif idx == 12:
                dc.DrawLine(bm_half, bm_full, bm_full, bm_full)

            dc.SelectObject(wx.NullBitmap)
            self.preview[idx] = imgBit

    @signal_listener("cf_1")
    @signal_listener("cf_2")
    @signal_listener("cf_3")
    @signal_listener("cf_4")
    @signal_listener("cf_5")
    @signal_listener("cf_6")
    @signal_listener("cf_7")
    @signal_listener("cf_8")
    @signal_listener("cf_9")
    @signal_listener("cf_10")
    @signal_listener("cf_11")
    @signal_listener("cf_12")
    def updates_received(self, *args):
        self.pane_show()

    def pane_show(self):
        """
                   01    02        
                a-------b-------c
                |       |       |
             08 |    11 |       | 03
                |  09   |   10  |
                d-------e-------f
                |       |       |
             07 |    12 |       | 04
                |       |       |
                g-------h-------i
                   06       05
        """
        self.txt_x_top_1.SetValue(Length(f"{self.context.device.cf_1}mm", digits=2).length_mm)
        self.txt_x_top_2.SetValue(Length(f"{self.context.device.cf_2}mm", digits=2).length_mm)

        self.txt_y_top_1.SetValue(Length(f"{self.context.device.cf_8}mm", digits=2).length_mm)
        self.txt_y_top_2.SetValue(Length(f"{self.context.device.cf_11}mm", digits=2).length_mm)
        self.txt_y_top_3.SetValue(Length(f"{self.context.device.cf_3}mm", digits=2).length_mm)

        self.txt_x_mid_1.SetValue(Length(f"{self.context.device.cf_9}mm", digits=2).length_mm)
        self.txt_x_mid_2.SetValue(Length(f"{self.context.device.cf_10}mm", digits=2).length_mm)

        self.txt_y_bottom_1.SetValue(Length(f"{self.context.device.cf_7}mm", digits=2).length_mm)
        self.txt_y_bottom_2.SetValue(Length(f"{self.context.device.cf_12}mm", digits=2).length_mm)
        self.txt_y_bottom_3.SetValue(Length(f"{self.context.device.cf_4}mm", digits=2).length_mm)

        self.txt_x_bottom_1.SetValue(Length(f"{self.context.device.cf_6}mm", digits=2).length_mm)
        self.txt_x_bottom_2.SetValue(Length(f"{self.context.device.cf_5}mm", digits=2).length_mm)
    
    def pane_hide(self):
        return
    
class BalorConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(550, 700, *args, **kwds)
        self.context = self.context.device
        self.SetHelpText("balorconfig")
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Balor-Configuration"))
        self._test_pin = False
        self._define_cor = False
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)
        options = (
            ("balor", "Balor"),
            ("balor-redlight", "Redlight"),
            ("balor-global", "Global"),
            ("balor-global-timing", "Timings"),
            ("balor-extra", "Extras"),
            # ("balor-corfile", "Correction"),
        )
        self.test_bits = ""
        injector = (
            {
                "attr": "test_pin",
                "object": self,
                "default": False,
                "type": bool,
                "style": "button",
                "label": _("Test"),
                "tip": _("Turn red dot on for test purposes"),
                "section": "_10_Parameters",
                "subsection": "_30_Pin-Index",
            },
            {
                "attr": "test_bits",
                "object": self,
                "default": "",
                "type": str,
                "enabled": False,
                "label": _("Bits"),
                "section": "_10_Parameters",
                "subsection": "_30_Pin-Index",
            },
        )
        # injector_cor = (
        #     {
        #         "attr": "define_cor",
        #         "object": self,
        #         "default": False,
        #         "type": bool,
        #         "style": "button",
        #         "label": _("Define"),
        #         "tip": _("Open a definition screen"),
        #         "section": _("Correction-Values"),
        #     },
        # )
        self.panels = []
        for item in options:
            section = item[0]
            pagetitle = _(item[1])
            addpanel = self.visible_choices(section)
            if addpanel:
                if item[0] == "balor":
                    injection = injector
                # elif item[0] == "balor-corfile":
                #     injection = injector_cor
                else:
                    injection = None
                newpanel = ChoicePropertyPanel(
                    self,
                    wx.ID_ANY,
                    context=self.context,
                    choices=section,
                    injector=injection,
                )
                self.panels.append(newpanel)
                self.notebook_main.AddPage(newpanel, pagetitle)

        newpanel = CorrectionPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Correction"))

        newpanel = EffectsPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Effects"))

        newpanel = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Warning"))

        newpanel = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Default Actions"))

        newpanel = FormatterPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Display Options"))

        self.Layout()
        for panel in self.panels:
            self.add_module_delegate(panel)
        self.timer = Job(
            process=self.update_bit_info,
            job_name="balor-bit",
            interval=1.0,
            run_main=True,
        )
        self.restore_aspect()

    @property
    def test_pin(self):
        return self._test_pin

    @test_pin.setter
    def test_pin(self, value):
        self._test_pin = not self._test_pin
        if self._test_pin:
            self.context("red on\n")
        else:
            self.context("red off\n")

    # @property
    # def define_cor(self):
    #     return self._define_cor

    # @define_cor.setter
    # def define_cor(self, value):
    #     self._define_cor = value
    #     if self._define_cor:
    #         self.context("widget_corfile\n")

    def update_bit_info(self, *args):
        if not self.context.driver.connected:
            status = "busy"
        else:
            port_list = self.context.driver.connection.read_port()
            ports = port_list[1]
            status = ""
            line1 = ""
            line2 = ""
            for bit in range(16):
                line1 += f"{bit // 10}"
                line2 += f"{bit % 10}"
                if bool((1 << bit) & ports):
                    status += "x"
                else:
                    status += "-"
            # print (line1)
            # print (line2)
            # print (status)
        self.test_bits = status
        self.context.root.signal("test_bits", status, self)

    def window_close(self):
        for panel in self.panels:
            panel.pane_hide()
        self.context.kernel.unschedule(self.timer)

    def window_open(self):
        for panel in self.panels:
            panel.pane_show()
        self.context.kernel.schedule(self.timer)

    @signal_listener("balorpin")
    def on_pin_change(self, origina, *args):
        self.context.driver.connection.define_pins()

    @signal_listener("corfile")
    def on_corfile_changed(self, origin, *args):
        from meerk40t.balormk.controller import GalvoController

        if not self.context.corfile:
            return
        try:
            scale = GalvoController.get_scale_from_correction_file(self.context.corfile)
        except (FileNotFoundError, PermissionError, OSError):
            return
        self.context.lens_size = f"{65536.0 / scale:.03f}mm"
        self.context.signal("lens_size", self.context.lens_size, self.context)

    def window_preserve(self):
        return False

    def visible_choices(self, section):
        result = False
        devmode = self.context.root.setting(bool, "developer_mode", False)
        choices = self.context.lookup("choices", section)
        if choices is not None:
            for item in choices:
                try:
                    dummy = str(item["hidden"])
                    if dummy == "" or dummy == "0":
                        hidden = False
                    else:
                        hidden = False if devmode else True
                except KeyError:
                    hidden = False
                if not hidden:
                    result = True
                    break
        return result

    @staticmethod
    def submenu():
        return "Device-Settings", "Configuration"
