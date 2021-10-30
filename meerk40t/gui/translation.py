import re

import wx

from .icons import icons8_connected_50
from .mwindow import MWindow

PUNCTUATION = (".", "?", "!", ":", ";")


class TranslationPanel(wx.Panel):
    def __init__(self, *args, context=None, language=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.language = language
        translations = open("./locale/%s/LC_MESSAGES/meerk40t.po" % language, "r", encoding="utf-8")

        self.entries = []
        file_lines = translations.readlines()
        index = 0
        while index < len(file_lines):
            comment = ""
            msgid = ""
            msgstr = ""
            try:
                # Find comments and all multiline comments
                if re.match("#\"(.*)\"", file_lines[index]):
                    m = re.match("#\"(.*)\"", file_lines[index])
                    comment = m.group(1)
                    index += 1
                    if index >= len(file_lines):
                        break
                    while re.match("^#(.*)$", file_lines[index]):
                        m = re.match("^#(.*)$", file_lines[index])
                        comment += m.group(1)
                        index += 1

                # find msgid and all multiline message ids
                if re.match("msgid \"(.*)\"", file_lines[index]):
                    m = re.match("msgid \"(.*)\"", file_lines[index])
                    msgid = m.group(1)
                    index += 1
                    if index >= len(file_lines):
                        break
                    while re.match("^\"(.*)\"$", file_lines[index]):
                        m = re.match("^\"(.*)\"$", file_lines[index])
                        msgid += m.group(1)
                        index += 1

                # find all message strings and all multi-line message strings
                if re.match("msgstr \"(.*)\"", file_lines[index]):
                    m = re.match("msgstr \"(.*)\"", file_lines[index])
                    msgstr = m.group(1)
                    index += 1
                    while re.match("^\"(.*)\"$", file_lines[index]):
                        m = re.match("^\"(.*)\"$", file_lines[index])
                        msgstr += m.group(1)
                        index += 1
            except IndexError:
                break
            if len(comment) or len(msgid) or len(msgstr):
                self.entries.append([comment, msgid, msgstr, list()])
            index += 1

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)

        self.tree_translation_tree = wx.TreeCtrl(self, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_HAS_VARIABLE_ROW_HEIGHT | wx.TR_HIDE_ROOT | wx.TR_NO_LINES | wx.TR_SINGLE | wx.TR_TWIST_BUTTONS)
        sizer_1.Add(self.tree_translation_tree, 1, wx.EXPAND, 0)

        self.root = self.tree_translation_tree.AddRoot("en -> %s" % language)

        self.workflow = self.tree_translation_tree.AppendItem(self.root, "Workflow")
        self.errors = self.tree_translation_tree.AppendItem(self.root, "Errors")
        self.issues = self.tree_translation_tree.AppendItem(self.root, "Issues")

        self.tree_translation_tree.SetItemTextColour(self.errors, wx.RED)
        self.printf = self.tree_translation_tree.AppendItem(self.errors, "printf-tokens")

        self.tree_translation_tree.SetItemTextColour(self.issues, wx.Colour(127, 127, 0))
        self.equal = self.tree_translation_tree.AppendItem(self.issues, "msgid==msgstr")
        self.start_capital = self.tree_translation_tree.AppendItem(self.issues, "capitalization")
        self.end_punct = self.tree_translation_tree.AppendItem(self.issues, "ending punctuation")
        self.end_space = self.tree_translation_tree.AppendItem(self.issues, "ending whitespace")
        self.double_space = self.tree_translation_tree.AppendItem(self.issues, "double space")

        self.all = self.tree_translation_tree.AppendItem(self.workflow, "All Translations")
        self.untranslated = self.tree_translation_tree.AppendItem(self.workflow, "Untranslated")
        self.translated = self.tree_translation_tree.AppendItem(self.workflow, "Translated")
        for entry in self.entries:
            self.process_validate_entry(entry)
        self.tree_translation_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_selection)
        self.tree_translation_tree.ExpandAll()

        self.panel_entry = wx.Panel(self, wx.ID_ANY)
        sizer_1.Add(self.panel_entry, 3, wx.EXPAND, 0)

        sizer_2 = wx.BoxSizer(wx.VERTICAL)

        self.text_comment = wx.TextCtrl(self.panel_entry, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer_2.Add(self.text_comment, 3, wx.EXPAND, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)

        text_quality = wx.StaticText(self.panel_entry, wx.ID_ANY, "Valid")
        text_quality.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        sizer_3.Add(text_quality, 1, wx.EXPAND, 0)

        self.checkbox_1 = wx.CheckBox(self.panel_entry, wx.ID_ANY, "Fuzzy")
        self.checkbox_1.SetFont(wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        sizer_3.Add(self.checkbox_1, 0, 0, 0)

        self.text_original_text = wx.TextCtrl(self.panel_entry, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer_2.Add(self.text_original_text, 6, wx.EXPAND, 0)

        self.text_translated_text = wx.TextCtrl(self.panel_entry, wx.ID_ANY, "", style=wx.TE_MULTILINE)
        sizer_2.Add(self.text_translated_text, 6, wx.EXPAND, 0)

        self.panel_entry.SetSizer(sizer_2)

        self.SetSizer(sizer_1)

        self.Layout()

        self.Bind(wx.EVT_TEXT, self.on_text_translated, self.text_translated_text)
        self.text_translated_text.SetFocus()
        self.text_original_text.SetCanFocus(False)
        self.text_comment.SetCanFocus(False)
        # end wxGlade
        self.entry = None

    def update_translation_values(self):
        if self.entry is not None:
            self.text_comment.SetValue(self.entry[0])
            self.text_original_text.SetValue(self.entry[1])
            self.text_translated_text.SetValue(self.entry[2])

    def on_tree_selection(self, event):
        try:
            data = [
                self.tree_translation_tree.GetItemData(item) for item in self.tree_translation_tree.GetSelections()
            ]
            if len(data) > 0:
                self.entry = data[0]
                self.update_translation_values()
        except RuntimeError:
            pass

    def source(self):
        self.text_translated_text.SetValue(self.text_original_text.GetValue())

    def next(self):
        for item in list(self.tree_translation_tree.GetSelections()):
            t = self.tree_translation_tree.GetNextSibling(item)
            if t.IsOk():
                self.tree_translation_tree.SelectItem(t)

    def previous(self):
        for item in list(self.tree_translation_tree.GetSelections()):
            t = self.tree_translation_tree.GetPrevSibling(item)
            if t.IsOk():
                self.tree_translation_tree.SelectItem(t)

    def process_validate_entry(self, entry):
        comment = entry[0]
        msgid = entry[1]
        msgstr = entry[2]
        items = entry[3]
        if msgid == "":
            msgid = "HEADER"
        items.append(self.tree_translation_tree.AppendItem(self.all, msgid, data=entry))
        if not msgstr:
            items.append(self.tree_translation_tree.AppendItem(self.untranslated, msgid, data=entry))
            return
        else:
            items.append(self.tree_translation_tree.AppendItem(self.translated, msgid, data=entry))
        if msgid == "HEADER":
            return
        if msgid == msgstr:
            items.append(self.tree_translation_tree.AppendItem(self.equal, msgid, data=entry))
        if msgid[-1] != msgstr[-1]:
            if msgid[-1] in PUNCTUATION or msgstr[-1] in PUNCTUATION:
                items.append(self.tree_translation_tree.AppendItem(self.end_punct, msgid, data=entry))
            if msgid[-1] == " " or msgstr[-1] == " ":
                items.append(self.tree_translation_tree.AppendItem(self.end_space, msgid, data=entry))
        if "%f" in msgid and "%f" not in msgid:
            items.append(self.tree_translation_tree.AppendItem(self.printf, msgid, data=entry))
        elif "%s" in msgid and "%s" not in msgid:
            items.append(self.tree_translation_tree.AppendItem(self.printf, msgid, data=entry))
        elif "%d" in msgid and "%d" not in msgid:
            items.append(self.tree_translation_tree.AppendItem(self.printf, msgid, data=entry))
        if msgid[0].isupper() != msgstr[0].isupper():
            items.append(self.tree_translation_tree.AppendItem(self.start_capital, msgid, data=entry))
        if "  " in msgstr and "  " not in msgid:
            items.append(self.tree_translation_tree.AppendItem(self.double_space, msgid, data=entry))

    def on_text_translated(self, event):  # wxGlade: TranslationPanel.<event_handler>
        if self.entry:
            self.entry[2] = self.text_translated_text.GetValue()


class Translation(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(1200, 800, *args, **kwds)

        self.panel = TranslationPanel(self, wx.ID_ANY, context=self.context, language="hu")

        # Menu Bar
        self.frame_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Open\tCtrl+O", "")
        self.Bind(wx.EVT_MENU, self.on_menu_open, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Save\tCtrl+S", "")
        self.Bind(wx.EVT_MENU, self.on_menu_save, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Save as", "")
        self.Bind(wx.EVT_MENU, self.on_menu_saveas, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Export", "")
        self.Bind(wx.EVT_MENU, self.on_menu_export, item)
        self.frame_menubar.Append(wxglade_tmp_menu, "File")
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Previous Entry\tCtrl+Up", "")
        self.Bind(wx.EVT_MENU, self.on_menu_previous, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Next Entry\tCtrl+Down", "")
        self.Bind(wx.EVT_MENU, self.on_menu_next, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Copy Source\tAlt+Down", "")
        self.Bind(wx.EVT_MENU, self.on_menu_source, item)
        self.frame_menubar.Append(wxglade_tmp_menu, "Navigate")
        self.SetMenuBar(self.frame_menubar)
        # Menu Bar end

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_connected_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle("Translation")

    def window_open(self):
        pass

    def window_close(self):
        pass

    def on_menu_open(self, event):  # wxGlade: MyFrame.<event_handler>
        print("Event handler 'on_menu_open' not implemented!")
        event.Skip()

    def on_menu_save(self, event):  # wxGlade: MyFrame.<event_handler>
        print("Event handler 'on_menu_save' not implemented!")
        event.Skip()

    def on_menu_saveas(self, event):  # wxGlade: MyFrame.<event_handler>
        print("Event handler 'on_menu_saveas' not implemented!")
        event.Skip()

    def on_menu_export(self, event):  # wxGlade: MyFrame.<event_handler>
        print("Event handler 'on_menu_export' not implemented!")
        event.Skip()

    def on_menu_previous(self, event):  # wxGlade: MyFrame.<event_handler>
        self.panel.previous()

    def on_menu_next(self, event):  # wxGlade: MyFrame.<event_handler>
        self.panel.next()

    def on_menu_source(self, event):  # wxGlade: MyFrame.<event_handler>
        self.panel.source()
