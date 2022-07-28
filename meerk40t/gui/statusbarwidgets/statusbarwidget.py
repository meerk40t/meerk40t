import wx

class StatusBarWidget(wx.BoxSizer):
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
        self.panelidx = None
        self.checked = False
        self.startup = None
        self.parent = None

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

    def Enable(self, enableit):
        for entry in self.GetChildren():
            wind = entry.GetWindow()
            if wind is not None:
                wind.Enable(enableit)

    def Show(self, showit):
        cnt = self.GetItemCount()
        if cnt==0:
            return
        if cnt==1:
            # Address an assertion issue in wxpython 4.1.1 that throws
            # an error if a sizer contains just one element

            # dummylbl = wx.StaticText(self.parent, wx.ID_ANY, "")
            # self.Add(dummylbl, 0, 0, 0)
            self.Prepend(5)

        # Standard action to show or hide, can be redefined
        if showit:
            super().ShowItems(True)
            super().Show(True)
            self.visible = True
        else:
            super().ShowItems(False)
            super().Hide(True)
            # for siz_item in sizerbox.GetChildren():
            #     wind = siz_item.GetWindow()
            #     if wind is not None:
            #         wind.Show(showit)
            self.visible = False
        self.Layout()

    def Reparent(self, parent):
        # Needs to be done to ensure the boxsizer is aware of the parent window
        self.parent = parent
        for sizeritem in self.GetChildren():
            wind = sizeritem.GetWindow()
            if wind is not None:
                wind.Reparent(self.parent)

    def Signal(self, signal, *args):
        # needs to be done in the concrete implementation
        return
