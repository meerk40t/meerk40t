from threading import Timer
import wx
from meerk40t.gui.icons import icons8_next_page_20


class CustomStatusBar(wx.StatusBar):
    """
    Overloading of wx.Statusbar to allow some elements on it
    """

    def __init__(self, parent, panelct):
        # Where shall the different controls be placed?
        self.startup = True
        self.panelct = panelct
        self.context = parent.context
        wx.StatusBar.__init__(self, parent, -1)
        # Make sure that the statusbar elements are visible fully
        self.SetMinHeight(25)
        self.SetFieldsCount(self.panelct)
        self.SetStatusStyles([wx.SB_SUNKEN] * self.panelct)
        self.status_text = [""] * self.panelct
        self.sizeChanged = False
        self.widgets = {}
        self.activesizer = [None] * self.panelct
        self.nextbuttons = []
        for idx in range(self.panelct):
            btn = wx.Button(self, id=wx.ID_ANY, label="", size=wx.Size(20, -1))
            btn.SetBitmap(icons8_next_page_20.GetBitmap(noadjustment=True))
            btn.Show(False)
            btn.Bind(wx.EVT_BUTTON, self.on_button_next)
            btn.Bind(wx.EVT_RIGHT_DOWN, self.on_button_prev)
            self.nextbuttons.append(btn)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.timer_active = False
        self.timer_info = None
        self.timer_lastmsg = -1

        # set the initial position of the checkboxes
        self.Reposition()
        self.startup = False

    def __del__(self):
        if self.timer_info is not None:
            self.timer_info.cancel()
            self.timer_info = None

    def check_for_hidden_infos(self):
        hidden = False
        for idx in range(self.panelct):
            if self.activesizer[idx] is not None and len(self.status_text[idx]) > 0:
                hidden = True
                break
        if hidden and not self.timer_active:
            self.activate_timed_messages(True)
        elif not hidden and self.timer_active:
            self.activate_timed_messages(False)

    def SetStatusText(self, message="", panel=0):
        if panel >= 0 and panel < self.panelct:
            self.status_text[panel] = message
        # Check whether we have hidden messages
        self.check_for_hidden_infos()
        if self.activesizer[panel] is not None and len(message) > 0:
            # Someone wanted to have a message while displaying some control elements
            return
        super().SetStatusText(message, panel)

    def update_info(self):
        # Loop through non-emptive messages
        msg = ""
        for idx in range(self.panelct):
            if idx > self.timer_lastmsg and len(self.status_text[idx]) > 0:
                if idx > 0:
                    msg += str(idx) + "#: "
                msg += self.status_text[idx]
                self.timer_lastmsg = idx
                break
        if len(msg) == 0:
            # didn't find any so reset
            self.timer_lastmsg = -1
            if len(self.status_text[0]) > 0:
                msg = self.status_text[0]
                self.timer_lastmsg = -0
        try:
            super().SetStatusText(msg, 0)
        except RuntimeError:
            return
        # restart timer
        self.timer_info.cancel()
        self.timer_info = Timer(interval=3, function=self.update_info)
        self.timer_info.start()

    def activate_timed_messages(self, active):
        """
        If we can't show the relevant StatusTexts in some panels then
        we circle through the displays
        """
        if active:
            if self.timer_active:
                if self.timer_info is not None:
                    self.timer_info.cancel()
                    self.timer_lastmsg = -1
            self.timer_info = Timer(interval=3, function=self.update_info)
            self.timer_info.start()
            self.timer_active = True
        else:
            if self.timer_info is not None:
                self.timer_info.cancel()
            self.timer_active = False
            self.timer_lastmsg = -1

    def add_panel_widget(self, widget, panel_idx, identifier, visible=True):
        if panel_idx < 0 or panel_idx >= self.panelct:
            return
        # Make sure they belong to me, else the wx.Boxsizer
        # will have wrong information to work with
        widget.GenerateControls(self, panel_idx, identifier, self.context)
        widget.active = visible
        self.widgets[identifier] = widget

    def activate_panel(self, identifier, newflag):
        # Activate Panel will make the indicated panel become choosable
        # print ("Activate Panel: %s -> %s" % (identifier, newflag))
        try:
            oldflag = self.widgets[identifier].active
        except (IndexError, KeyError):
            return
        if oldflag != newflag:
            panelidx = self.widgets[identifier].panelidx

            # Choosable
            self.widgets[identifier].active = newflag
            if newflag and self.activesizer[panelidx] is None:
                self.activesizer[panelidx] = identifier
            elif not newflag and self.activesizer[panelidx] == identifier:
                # Was the active one, so look for an alternative
                self.activesizer[panelidx] = None
                for key in self.widgets:
                    entry = self.widgets[key]
                    if entry.active and entry.panelidx == panelidx:
                        self.activesizer[panelidx] = key
                        break
            self.check_for_hidden_infos()
            self.Reposition(panelidx=panelidx)

    def force_panel(self, identifier):
        # force_panel will make the indicated panel choosable and visible
        try:
            oldflag = self.widgets[identifier].active
        except (IndexError, KeyError):
            return
        if not oldflag:
            # Make it choosable
            self.widgets[identifier].active = True
        panelidx = self.widgets[identifier].panelidx
        self.activesizer[panelidx] = identifier
        self.check_for_hidden_infos()
        self.Reposition(panelidx=panelidx)

    def next_entry_in_panel(self, panelidx):
        if panelidx < 0 or panelidx >= self.panelct:
            return
        first_entry = None
        next_entry = None
        visible_seen = False
        for key in self.widgets:
            entry = self.widgets[key]
            if entry.panelidx == panelidx and entry.active:
                if key == self.activesizer[panelidx]:  # Visible
                    visible_seen = True
                else:
                    if visible_seen and next_entry is None:
                        next_entry = key
                        break
                    else:
                        if first_entry is None:
                            first_entry = key
        if next_entry is None:
            next_entry = first_entry
        if next_entry is not None:
            self.force_panel(next_entry)
        else:
            self.activesizer[panelidx] = None

    def prev_entry_in_panel(self, panelidx):
        if panelidx < 0 or panelidx >= self.panelct:
            return
        last_entry = None
        prev_entry = None
        visible_seen = False
        for key in self.widgets:
            entry = self.widgets[key]
            if entry.panelidx == panelidx and entry.active:
                if key == self.activesizer[panelidx]:  # Visible
                    visible_seen = True
                elif visible_seen:
                    last_entry = key
                else:
                    prev_entry = key
        if prev_entry is None:
            prev_entry = last_entry
        if prev_entry is not None:
            self.force_panel(prev_entry)
        else:
            self.activesizer[panelidx] = None

    def on_button_next(self, event):
        button = event.GetEventObject()
        for idx in range(self.panelct):
            if self.nextbuttons[idx] == button:
                self.next_entry_in_panel(idx)
                break
        #        self.Reposition()
        event.Skip()

    def on_button_prev(self, event):
        button = event.GetEventObject()
        for idx in range(self.panelct):
            if self.nextbuttons[idx] == button:
                self.prev_entry_in_panel(idx)
                break
        #        self.Reposition()
        event.Skip()

    # def debug_me(self):
    #     for key in self.widgets:
    #         entry = self.widgets[key]
    #         print ("%s - Panel=%s Vis=%s" % (key, entry.panelidx, entry.active))

    def Reposition(self, panelidx=None):
        """
        Draw the panels
        """

        # self.debug_me()
        if panelidx is None:
            targets = range(self.panelct)
        else:
            targets = (panelidx,)
        for pidx in targets:
            # print("panel # %d has default: %s" % (pidx, self.activesizer[pidx]))
            panelrect = self.GetFieldRect(pidx)
            # Establish the amount of 'choosable' sizers
            ct = 0
            sizer = None
            for key in self.widgets:
                entry = self.widgets[key]
                # print ("%s = %s" %(key, entry) )
                if entry.panelidx == pidx:
                    if entry.active:  # The right one and choosable...
                        ct += 1
                        if self.activesizer[pidx] is None:
                            self.activesizer[pidx] = key
                        if (
                            self.activesizer[pidx] != key
                        ):  # its not the default, so hide
                            entry.Show(False)
                    else:  # not choosable --> hide:
                        entry.Show(False)
            if ct > 1:
                # Show Button and reduce available width for sizer
                myrect = self.nextbuttons[pidx].GetRect()
                myrect.x = panelrect.x + panelrect.width - myrect.width
                myrect.y = panelrect.y
                self.nextbuttons[pidx].SetRect(myrect)
                panelrect.width -= myrect.width
                self.nextbuttons[pidx].Show(True)
            else:
                self.nextbuttons[pidx].Show(False)
            if self.activesizer[pidx] is not None:
                sizer = self.widgets[self.activesizer[pidx]]
                sizer.SetDimension(
                    panelrect.x, panelrect.y, panelrect.width, panelrect.height
                )
                sizer.Show(True)
                text = self.status_text[pidx]
                if text != "":
                    super().SetStatusText("", pidx)
            else:
                super().SetStatusText(self.status_text[pidx], pidx)
        # debug_me()
        self.sizeChanged = False

    def OnSize(self, evt):
        evt.Skip()
        self.Reposition()  # for normal size events
        self.sizeChanged = True

    def OnIdle(self, evt):
        if self.sizeChanged:
            self.Reposition()

    def Signal(self, signal, *args):
        # Propagate to widgets
        for key in self.widgets:
            self.widgets[key].Signal(signal, *args)
