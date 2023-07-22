import wx


class BasicHSizer:
    """
    A mockup (although working) of a horizontal wx.BoxSizer
    No nested functionality, just something simple - and which
    you have fully under control... (required for a Linux environment)
    """

    def __init__(self, *args):
        self.windows = []
        self.proportions = []
        self.flags = []
        self.activectrl = []
        self.visible = False
        self.x = 0
        self.y = 0
        self.width = 400
        self.height = 25
        self.start_x = 0

    def PrependSpacer(self, newx):
        if newx >= 0:
            self.start_x = newx

    def GetItemCount(self):
        return len(self.windows)

    def Add(self, window, proportion=0, flag=0, border=0):
        min_size = window.GetMinSize()
        if min_size[1] < 10 or min_size[0] < 10:
            min_size[0] = max(min_size[0], 10)
            min_size[1] = max(min_size[1], 10)
            window.SetMinSize(min_size)

        self.windows.append(window)
        self.proportions.append(proportion)
        self.flags.append(flag)
        self.activectrl.append(True)
        window.Show(False)

    def SetActive(self, control, enableit=True):
        cid = control.GetId()
        for idx, wind in enumerate(self.windows):
            if cid == wind.GetId():
                self.activectrl[idx] = enableit
                break

    def Enable(self, enableit=True):
        for wind in self.windows:
            wind.Enable(enableit)

    def ShowItems(self, showit=True):
        self.visible = showit
        for idx, wind in enumerate(self.windows):
            flag = showit and self.activectrl[idx]
            wind.Show(flag)

    def Show(self, showit=True):
        self.ShowItems(showit)

    def Hide(self, hideit=True):
        self.ShowItems(not hideit)

    def Layout(self):
        # Establish all required widths
        slen = len(self.windows)
        self.myx = [0] * slen
        self.myy = [0] * slen
        self.myw = [0] * slen
        self.myh = [0] * slen
        total_proportions = 0
        availw = self.width - self.start_x
        for idx, wind in enumerate(self.windows):
            if not self.activectrl[idx]:
                continue
            min_size = wind.GetMinSize()
            curr_size = wind.GetSize()
            if self.flags[idx] == 0:
                # don't touch the vertical value
                new_h = curr_size[1]
            else:
                new_h = self.height - 2
            if min_size[1] > 0 and min_size[1] > new_h:
                new_h = min_size[1]
            self.myh[idx] = new_h
            self.myy[idx] = self.y + max(0, (self.height - new_h) / 2) + 1
            # print ("Setting values for %s: h=%.1f, y=%.1f" % (type(wind).__name__, new_h, self.myy[idx]))
            total_proportions += self.proportions[idx]
            if self.proportions[idx] <= 0:
                self.myw[idx] = max(curr_size[0], min_size[0])
                availw -= self.myw[idx]
            else:
                self.myw[idx] = -1
        # print ("Total proportions: %.1f, width=%.1f, remaining=%.1f" % (total_proportions, self.width, availw ))
        # Now that we have established the minsize lets see what we have left
        # First iteration, check for maxSize
        if total_proportions > 0:
            for idx, wind in enumerate(self.windows):
                if self.proportions[idx] > 0 and self.activectrl[idx]:
                    max_size = wind.GetMaxSize()
                    min_size = wind.GetMinSize()
                    if min_size[0] < 10:
                        min_size[0] = 10
                    testsize = max(
                        min_size[0], self.proportions[idx] * availw / total_proportions
                    )
                    if 0 < max_size[0] < testsize:
                        # too big
                        self.myw[idx] = max_size[0]
                        # Give remaining size back
                        total_proportions -= self.proportions[idx]
                        availw -= max_size[0]
        # Second iteration, assign remaining space
        if total_proportions > 0:
            for idx, wind in enumerate(self.windows):
                # Don't touch already assigned ones...
                if (
                    self.proportions[idx] > 0
                    and self.activectrl[idx]
                    and self.myw[idx] < 0
                ):
                    min_size = wind.GetMinSize()
                    if min_size[0] < 10:
                        min_size[0] = 10
                    testsize = max(
                        min_size[0], self.proportions[idx] * availw / total_proportions
                    )
                    self.myw[idx] = testsize

        # And now lets move the windows...
        newx = self.start_x + self.x
        for idx, wind in enumerate(self.windows):
            self.myx[idx] = newx
            if self.visible is None:
                self.visible = False
            flag = self.visible and self.activectrl[idx]

            # if self.myx[idx] > self.x + self.width or self.myx[idx] + self.myw[idx] > self.x + self.width:
            if self.myx[idx] > self.x + self.width:
                flag = False
            else:
                # cast everything to int, just to be on the safe side
                rect = wx.Rect(
                    int(self.myx[idx]),
                    int(self.myy[idx]),
                    int(self.myw[idx]),
                    int(self.myh[idx]),
                )
                wind.SetRect(rect)
                # flag = flag and True
            wind.Show(flag)
            newx += self.myw[idx]

    def SetDimension(self, newx, newy, newwidth, newheight):
        # print ("Set dimension called")
        self.x = newx
        self.y = newy
        self.width = newwidth
        self.height = newheight
        self.Layout()

    def Reparent(self, new_parent):
        for wind in self.windows:
            if wind is not None:
                wind.Reparent(new_parent)


class StatusBarWidget(BasicHSizer):
    # class StatusBarWidget(wx.BoxSizer):
    """
    General class to be added to a CustomStatusBar,
    defines some general routines that can be overloaded
    by a concrete implementation
    """

    def __init__(self, **kwargs):
        super().__init__(wx.HORIZONTAL, **kwargs)
        self.identifier = None
        self.context = None
        self.visible = None
        self.active = None
        self.panelidx = None
        self.checked = False
        self.startup = None
        self.parent = None

    def SetActive(self, control, enableit=True):
        # Logic to use own hsizer or wx.BoxSizer
        if hasattr(super(), "SetActive"):
            super().SetActive(control, enableit)
        else:
            control.Show(enableit)

    def RefreshItems(self, showit=True):
        if hasattr(super(), "SetActive"):
            self.ShowItems(showit)
        else:
            pass

    def GenerateControls(self, parent, panelidx, identifier, context):
        """
        Will be called within CustomStatusBar.
        Copy this code to your implementation
        """
        self.panelidx = panelidx
        self.identifier = identifier
        self.parent = parent
        self.context = context
        # COPY:
        #   super().GenerateControls(parent, panelidx, identifier, context)
        # Now add your controls, make sure they are added with
        #   self.btn = wx.Button(self.parent, wx.ID_ANY...)
        #   self.add(self.btn, 1, wx.EXPAND, 0)

    def StartPopulation(self):
        """
        If you want to update controls with values, then you should
         - encapsule things between StartPopulation and EndPopulation
         - check for 'if not self.startup:' in your on_update_ routines
        """
        self.startup = True

    def EndPopulation(self):
        self.startup = False

    def Show(self, showit=True):
        # print ("Called %s - show with %s" % (self.identifier, showit))
        cnt = self.GetItemCount()
        if cnt == 0:
            return
        if cnt == 1:
            # dummylbl = wx.StaticText(self.parent, wx.ID_ANY, "")
            # self.Add(dummylbl, 0, 0, 0)
            self.PrependSpacer(5)

        # Standard action to show or hide, can be redefined
        if showit:
            super().Show(True)
            self.visible = True
        else:
            super().Hide(True)
            self.visible = False
        self.Layout()

    def Reparent(self, parent):
        # Needs to be done to ensure the boxsizer is aware of the parent window
        self.parent = parent
        super().Reparent(parent)

    def Signal(self, signal, *args):
        # needs to be done in the concrete implementation
        return
