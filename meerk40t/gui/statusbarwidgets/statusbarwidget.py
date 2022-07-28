import wx

class StatusBarWidget(wx.BoxSizer):
    """
    General class to be added to a CustomStatusBar,
    defines some general routines that can be overloaded
    by a concrete implementation
    """
    def __init__(self, parent, panelidx, identifier, context, **args):
        super().init(wx.HORIZONTAL, args)
        self.identifier = identifier
        self.context = context
        self.visible = None
        self.panelidx = panelidx
        self.checked = False
        self.startup = None
        self.parent = parent

    def StartPopulation(self):
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

    def Signal(self, signal, **args):
        # needs to be done in the concrete implementation
        return
