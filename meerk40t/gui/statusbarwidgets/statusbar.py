import wx
from meerk40t.gui.icons import icons8_next_page_20

class CustomStatusBar(wx.StatusBar):
    """Overloading of Statusbar to allow some elements on it"""

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
        self.previous_text = [""] * self.panelct
        self.sizeChanged = False
        self.box_id_visible = {}
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

        # set the initial position of the checkboxes
        self.Reposition()
        self.startup = False

    def SetStatusText(self, message="", panel=0):
        if panel >= 0 and panel < self.panelct:
            self.status_text[panel] = message
        if self.activesizer[panel] is not None and len(message) > 0:
            # Someone wanted to have a message while displaying some control elements
            return
        super().SetStatusText(message, panel)

    def add_sizer_panel(self, panel_idx, wx_boxsizer, identifier, visible=True, callback=None):
        if panel_idx < 0 or panel_idx >= self.panelct:
            return
        # Mke sure they belong to me, else the wx.Boxsizer
        # will have wrong information to work with
        for sizeritem in wx_boxsizer.GetChildren():
            wind = sizeritem.GetWindow()
            if wind is not None:
                wind.Reparent(self)

        storage = [wx_boxsizer, panel_idx, visible, callback]  # Visible by default
        self.box_id_visible[identifier] = storage

    def activate_panel(self, identifier, newflag):
        # Activate Panel will make the indicated panel become choosable
        try:
            oldflag = self.box_id_visible[identifier][2]
        except (IndexError, KeyError):
            return
        if oldflag != newflag:
            panelidx = self.box_id_visible[identifier][1]

            # Choosable
            self.box_id_visible[identifier][2] = newflag
            if newflag and self.activesizer[panelidx] is None:
                self.activesizer[panelidx] = identifier
            elif not newflag and self.activesizer[panelidx] == identifier:
                # Was the active one
                self.activesizer[panelidx] = None
                for key in self.box_id_visible:
                    entry = self.box_id_visible[key]
                    if entry[2] and entry[1] == panelidx:
                        self.activesizer[panelidx] = key
                        break
            self.Reposition(panelidx=panelidx)

    def force_panel(self, identifier):
        # force_panel will make the indicated panel choosable and visible
        try:
            oldflag = self.box_id_visible[identifier][2]
        except (IndexError, KeyError):
            return
        if not oldflag:
            # Make it choosable
            self.box_id_visible[identifier][2] = True
        panelidx = self.box_id_visible[identifier][1]
        self.activesizer[panelidx] = identifier
        self.Reposition(panelidx=panelidx)

    def next_entry_in_panel(self, panelidx):
        if panelidx < 0 or panelidx >= self.panelct:
            return
        first_entry = None
        next_entry = None
        visible_seen = False
        for key in self.box_id_visible:
            entry = self.box_id_visible[key]
            if entry[1] == panelidx and entry[2]:
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
        for key in self.box_id_visible:
            entry = self.box_id_visible[key]
            if entry[1] == panelidx and entry[2]:
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

    # Draw the panels
    def Reposition(self, panelidx=None):
        # def debug_me():
        #     for key in self.box_id_visible:
        #         siz = self.box_id_visible[key][0]
        #         items = siz.GetItemCount()
        #         print("Sizer '%s', children=%s" % (key, items))
        #         for idx in range(items):
        #             print("   Item #%d - shown=%s" % (idx, siz.IsShown(idx)))

        def deep_show_hide(sizerbox, key, showit, callback):
            # print ("Showit: key=%s, flag=%s, idx=%d, default=%s" % (key, showit, debugidx, debugdefault))
            if showit:
                if callback is None:
                    sizerbox.ShowItems(True)
                else:
                    callback(True)
                sizerbox.Show(True)
            else:
                if callback is None:
                    sizerbox.ShowItems(False)
                else:
                    callback(True)
                sizerbox.Hide(True)
            # for siz_item in sizerbox.GetChildren():
            #     wind = siz_item.GetWindow()
            #     if wind is not None:
            #         wind.Show(showit)
            sizerbox.Layout()

        # selfrect = self.GetRect()
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
            for key in self.box_id_visible:
                entry = self.box_id_visible[key]
                # print ("%s = %s" %(key, entry) )
                if entry[1] == pidx:
                    if entry[2]:  # The right one and choosable...
                        ct += 1
                        if self.activesizer[pidx] is None:
                            self.activesizer[pidx] = key
                        if (
                            self.activesizer[pidx] != key
                        ):  # its not the default, so hide
                            deep_show_hide(entry[0], key, False, entry[3])
                    else:  # not choosable --> hide:
                        deep_show_hide(entry[0], key, False, entry[3])
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
                sizer = self.box_id_visible[self.activesizer[pidx]][0]
                callback = self.box_id_visible[self.activesizer[pidx]][3]
                # print ("Panel %s='%s' - %s" % (pidx, self.activesizer[pidx], panelrect))
                # print ("Entries: %s" % sizer.GetItemCount())
                sizer.SetDimension(
                    panelrect.x, panelrect.y, panelrect.width, panelrect.height
                )
                deep_show_hide(sizer, self.activesizer[pidx], True, callback)
                text = self.status_text[pidx]
                if text != "":
                    self.previous_text[pidx] = text
                self.SetStatusText("", pidx)
            else:
                self.SetStatusText(self.previous_text[pidx], pidx)
        # debug_me()
        self.sizeChanged = False

    def OnSize(self, evt):
        evt.Skip()
        self.Reposition()  # for normal size events
        self.sizeChanged = True

    def OnIdle(self, evt):
        if self.sizeChanged:
            self.Reposition()