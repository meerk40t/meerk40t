import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel

_ = wx.GetTranslation


class OutputPropertyPanel(wx.Panel):
    name = "Output"

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.operation = node

        choices = [
            {
                "attr": "mask_bit0",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mask Bit0"),
                "tip": _("Mask Bit0"),
            },
            {
                "attr": "mask_bit1",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mask Bit1"),
                "tip": _("Mask Bit1"),
            },
            {
                "attr": "mask_bit2",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mask Bit2"),
                "tip": _("Mask Bit2"),
            },
            {
                "attr": "mask_bit3",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mask Bit3"),
                "tip": _("Mask Bit3"),
            },
            {
                "attr": "mask_bit4",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mask Bit4"),
                "tip": _("Mask Bit4"),
            },
            {
                "attr": "mask_bit5",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mask Bit5"),
                "tip": _("Mask Bit5"),
            },
            {
                "attr": "mask_bit6",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mask Bit6"),
                "tip": _("Mask Bit6"),
            },
            {
                "attr": "mask_bit7",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Mask Bit7"),
                "tip": _("Mask Bit7"),
            },
            {
                "attr": "value_bit0",
                "object": self,
                "default": False,
                "type": bool,
                "conditional": (self, "mask_bit0"),
                "label": _("Value Bit0"),
                "tip": _("Value Bit0"),
            },
            {
                "attr": "value_bit1",
                "object": self,
                "default": False,
                "type": bool,
                "conditional": (self, "mask_bit1"),
                "label": _("Value Bit1"),
                "tip": _("Value Bit1"),
            },
            {
                "attr": "value_bit2",
                "object": self,
                "default": False,
                "type": bool,
                "conditional": (self, "mask_bit2"),
                "label": _("Value Bit2"),
                "tip": _("Value Bit2"),
            },
            {
                "attr": "value_bit3",
                "object": self,
                "default": False,
                "type": bool,
                "conditional": (self, "mask_bit3"),
                "label": _("Value Bit3"),
                "tip": _("Value Bit3"),
            },
            {
                "attr": "value_bit4",
                "object": self,
                "default": False,
                "type": bool,
                "conditional": (self, "mask_bit4"),
                "label": _("Value Bit4"),
                "tip": _("Value Bit4"),
            },
            {
                "attr": "value_bit5",
                "object": self,
                "default": False,
                "type": bool,
                "conditional": (self, "mask_bit5"),
                "label": _("Value Bit5"),
                "tip": _("Value Bit5"),
            },
            {
                "attr": "value_bit6",
                "object": self,
                "default": False,
                "type": bool,
                "conditional": (self, "mask_bit6"),
                "label": _("Value Bit6"),
                "tip": _("Value Bit6"),
            },
            {
                "attr": "value_bit7",
                "object": self,
                "default": False,
                "type": bool,
                "conditional": (self, "mask_bit7"),
                "label": _("Value Bit7"),
                "tip": _("Value Bit7"),
            },
        ]
        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices
        )
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)
        self.Layout()

    @property
    def mask_bit0(self):
        return self.operation.get_mask(0)

    @property
    def mask_bit1(self):
        return self.operation.get_mask(1)

    @property
    def mask_bit2(self):
        return self.operation.get_mask(2)

    @property
    def mask_bit3(self):
        return self.operation.get_mask(3)

    @property
    def mask_bit4(self):
        return self.operation.get_mask(4)

    @property
    def mask_bit5(self):
        return self.operation.get_mask(5)

    @property
    def mask_bit6(self):
        return self.operation.get_mask(6)

    @property
    def mask_bit7(self):
        return self.operation.get_mask(7)

    @property
    def value_bit0(self):
        return self.operation.get_value(0)

    @property
    def value_bit1(self):
        return self.operation.get_value(1)

    @property
    def value_bit2(self):
        return self.operation.get_value(2)

    @property
    def value_bit3(self):
        return self.operation.get_value(3)

    @property
    def value_bit4(self):
        return self.operation.get_value(4)

    @property
    def value_bit5(self):
        return self.operation.get_value(5)

    @property
    def value_bit6(self):
        return self.operation.get_value(6)

    @property
    def value_bit7(self):
        return self.operation.get_value(7)

    @mask_bit0.setter
    def mask_bit0(self, v):
        if v:
            self.operation.mask_on(0)
        else:
            self.operation.mask_off(0)
        self.context.elements.signal("element_property_update", self.operation)

    @mask_bit1.setter
    def mask_bit1(self, v):
        if v:
            self.operation.mask_on(1)
        else:
            self.operation.mask_off(1)
        self.context.elements.signal("element_property_update", self.operation)

    @mask_bit2.setter
    def mask_bit2(self, v):
        if v:
            self.operation.mask_on(2)
        else:
            self.operation.mask_off(2)
        self.context.elements.signal("element_property_update", self.operation)

    @mask_bit3.setter
    def mask_bit3(self, v):
        if v:
            self.operation.mask_on(3)
        else:
            self.operation.mask_off(3)
        self.context.elements.signal("element_property_update", self.operation)

    @mask_bit4.setter
    def mask_bit4(self, v):
        if v:
            self.operation.mask_on(4)
        else:
            self.operation.mask_off(4)
        self.context.elements.signal("element_property_update", self.operation)

    @mask_bit5.setter
    def mask_bit5(self, v):
        if v:
            self.operation.mask_on(5)
        else:
            self.operation.mask_off(5)
        self.context.elements.signal("element_property_update", self.operation)

    @mask_bit6.setter
    def mask_bit6(self, v):
        if v:
            self.operation.mask_on(6)
        else:
            self.operation.mask_off(6)
        self.context.elements.signal("element_property_update", self.operation)

    @mask_bit7.setter
    def mask_bit7(self, v):
        if v:
            self.operation.mask_on(7)
        else:
            self.operation.mask_off(7)
        self.context.elements.signal("element_property_update", self.operation)

    @value_bit0.setter
    def value_bit0(self, v):
        if v:
            self.operation.value_on(0)
        else:
            self.operation.value_off(0)
        self.context.elements.signal("element_property_update", self.operation)

    @value_bit1.setter
    def value_bit1(self, v):
        if v:
            self.operation.value_on(1)
        else:
            self.operation.value_off(1)
        self.context.elements.signal("element_property_update", self.operation)

    @value_bit2.setter
    def value_bit2(self, v):
        if v:
            self.operation.value_on(2)
        else:
            self.operation.value_off(2)
        self.context.elements.signal("element_property_update", self.operation)

    @value_bit3.setter
    def value_bit3(self, v):
        if v:
            self.operation.value_on(3)
        else:
            self.operation.value_off(3)
        self.context.elements.signal("element_property_update", self.operation)

    @value_bit4.setter
    def value_bit4(self, v):
        if v:
            self.operation.value_on(4)
        else:
            self.operation.value_off(4)
        self.context.elements.signal("element_property_update", self.operation)

    @value_bit5.setter
    def value_bit5(self, v):
        if v:
            self.operation.value_on(5)
        else:
            self.operation.value_off(5)
        self.context.elements.signal("element_property_update", self.operation)

    @value_bit6.setter
    def value_bit6(self, v):
        if v:
            self.operation.value_on(6)
        else:
            self.operation.value_off(6)
        self.context.elements.signal("element_property_update", self.operation)

    @value_bit7.setter
    def value_bit7(self, v):
        if v:
            self.operation.value_on(7)
        else:
            self.operation.value_off(7)
        self.context.elements.signal("element_property_update", self.operation)

    def pane_hide(self):
        self.panel.pane_hide()

    def pane_show(self):
        self.panel.pane_show()

    def set_widgets(self, node):
        self.operation = node
