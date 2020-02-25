import wx

from icons import *
from svgelements import Angle

_ = wx.GetTranslation


class TransformEditor(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: TransformEditor.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((364, 299))
        self.text_a = wx.TextCtrl(self, wx.ID_ANY, "1.0")
        self.text_c = wx.TextCtrl(self, wx.ID_ANY, "0.0")
        self.text_b = wx.TextCtrl(self, wx.ID_ANY, "0.0")
        self.text_d = wx.TextCtrl(self, wx.ID_ANY, "1.0")
        self.text_e = wx.TextCtrl(self, wx.ID_ANY, "0.0")
        self.text_f = wx.TextCtrl(self, wx.ID_ANY, "0.0")
        self.button_scale_down = wx.BitmapButton(self, wx.ID_ANY, icons8_compress_50.GetBitmap())
        self.button_translate_up = wx.BitmapButton(self, wx.ID_ANY, icons8up.GetBitmap())
        self.button_scale_up = wx.BitmapButton(self, wx.ID_ANY, icons8_enlarge_50.GetBitmap())
        self.button_translate_left = wx.BitmapButton(self, wx.ID_ANY, icons8_left_50.GetBitmap())
        self.button_reset = wx.BitmapButton(self, wx.ID_ANY, icons8_delete_50.GetBitmap())
        self.button_translate_right = wx.BitmapButton(self, wx.ID_ANY, icons8_right_50.GetBitmap())
        self.button_rotate_ccw = wx.BitmapButton(self, wx.ID_ANY, icons8_rotate_left_50.GetBitmap())
        self.button_translate_down = wx.BitmapButton(self, wx.ID_ANY, icons8_down_50.GetBitmap())
        self.button_translate_cw = wx.BitmapButton(self, wx.ID_ANY, icons8_rotate_right_50.GetBitmap())

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TEXT, self.on_text_matrix, self.text_a)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_a)
        self.Bind(wx.EVT_TEXT, self.on_text_matrix, self.text_c)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_c)
        self.Bind(wx.EVT_TEXT, self.on_text_matrix, self.text_b)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_b)
        self.Bind(wx.EVT_TEXT, self.on_text_matrix, self.text_d)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_d)
        self.Bind(wx.EVT_TEXT, self.on_text_matrix, self.text_e)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_e)
        self.Bind(wx.EVT_TEXT, self.on_text_matrix, self.text_f)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_matrix, self.text_f)
        self.Bind(wx.EVT_BUTTON, self.on_scale_down, self.button_scale_down)
        self.Bind(wx.EVT_BUTTON, self.on_translate_up, self.button_translate_up)
        self.Bind(wx.EVT_BUTTON, self.on_scale_up, self.button_scale_up)
        self.Bind(wx.EVT_BUTTON, self.on_translate_left, self.button_translate_left)
        self.Bind(wx.EVT_BUTTON, self.on_reset, self.button_reset)
        self.Bind(wx.EVT_BUTTON, self.on_translate_right, self.button_translate_right)
        self.Bind(wx.EVT_BUTTON, self.on_rotate_ccw, self.button_rotate_ccw)
        self.Bind(wx.EVT_BUTTON, self.on_translate_down, self.button_translate_down)
        self.Bind(wx.EVT_BUTTON, self.on_rotate_cw, self.button_translate_cw)
        # end wxGlade
        self.kernel = None
        self.transform = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def on_close(self, event):
        self.kernel.mark_window_closed("TransformEditor")
        event.Skip()  # Call destroy.

    def set_kernel(self, kernel):
        self.kernel = kernel
        self.set_transform(None)

    def set_transform(self, transform):
        if transform is None:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
        else:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(True)

    def __set_properties(self):
        # begin wxGlade: TransformEditor.__set_properties
        self.SetTitle(_("TransformEditor"))
        self.button_scale_down.SetSize(self.button_scale_down.GetBestSize())
        self.button_translate_up.SetSize(self.button_translate_up.GetBestSize())
        self.button_scale_up.SetSize(self.button_scale_up.GetBestSize())
        self.button_translate_left.SetSize(self.button_translate_left.GetBestSize())
        self.button_reset.SetSize(self.button_reset.GetBestSize())
        self.button_translate_right.SetSize(self.button_translate_right.GetBestSize())
        self.button_rotate_ccw.SetSize(self.button_rotate_ccw.GetBestSize())
        self.button_translate_down.SetSize(self.button_translate_down.GetBestSize())
        self.button_translate_cw.SetSize(self.button_translate_cw.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: TransformEditor.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        grid_sizer_2 = wx.FlexGridSizer(3, 3, 0, 0)
        grid_sizer_1 = wx.FlexGridSizer(3, 3, 0, 0)
        grid_sizer_1.Add(self.text_a, 0, 0, 0)
        grid_sizer_1.Add(self.text_c, 0, 0, 0)
        grid_sizer_1.Add((0, 0), 0, 0, 0)
        grid_sizer_1.Add(self.text_b, 0, 0, 0)
        grid_sizer_1.Add(self.text_d, 0, 0, 0)
        grid_sizer_1.Add((0, 0), 0, 0, 0)
        grid_sizer_1.Add((0, 0), 0, 0, 0)
        grid_sizer_1.Add(self.text_e, 0, 0, 0)
        grid_sizer_1.Add(self.text_f, 0, 0, 0)
        sizer_1.Add(grid_sizer_1, 0, wx.EXPAND, 0)
        grid_sizer_2.Add(self.button_scale_down, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_up, 0, 0, 0)
        grid_sizer_2.Add(self.button_scale_up, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_left, 0, 0, 0)
        grid_sizer_2.Add(self.button_reset, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_right, 0, 0, 0)
        grid_sizer_2.Add(self.button_rotate_ccw, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_down, 0, 0, 0)
        grid_sizer_2.Add(self.button_translate_cw, 0, 0, 0)
        sizer_1.Add(grid_sizer_2, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_text_matrix(self, event):  # wxGlade: TransformEditor.<event_handler>
        print(event.Id)

    def on_scale_down(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.post_scale(0.99)
        self.kernel.signal("refresh_scene")

    def on_translate_up(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.post_translate(0, -1)
        self.kernel.signal("refresh_scene")

    def on_scale_up(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.post_scale(1.01)
        self.kernel.signal("refresh_scene")

    def on_translate_left(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.post_translate(-1, 0)
        self.kernel.signal("refresh_scene")

    def on_reset(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.reset()
        self.kernel.signal("refresh_scene")

    def on_translate_right(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.post_translate(1, 0)
        self.kernel.signal("refresh_scene")

    def on_rotate_ccw(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.post_rotate(Angle.degrees(-1))
        self.kernel.signal("refresh_scene")

    def on_translate_down(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.post_translate(0, 1)
        self.kernel.signal("refresh_scene")

    def on_rotate_cw(self, event):  # wxGlade: TransformEditor.<event_handler>
        self.transform.post_rotate(Angle.degrees(1))
        self.kernel.signal("refresh_scene")
