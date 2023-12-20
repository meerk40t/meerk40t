"""
GUI to manage material library entries.
In essence a material library setting is a persistent list of operations.
They are stored in the operations.cfg file in the meerk40t working directory
"""

import os
import xml.etree.ElementTree as ET

import wx
import wx.lib.mixins.listctrl as listmix

from ..core.node.node import Node
from ..kernel.kernel import get_safe_path
from ..kernel.settings import Settings
from .icons import (
    icon_library,
    icon_points,
    icons8_direction,
    icons8_image,
    icons8_laser_beam,
    icons8_laserbeam_weak,
)
from .mwindow import MWindow
from .wxutils import ScrolledPanel, StaticBoxSizer, TextCtrl, dip_size

_ = wx.GetTranslation


class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    """TextEditMixin allows any column to be edited."""

    # ----------------------------------------------------------------------
    def __init__(
        self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0
    ):
        """Constructor"""
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)


class MaterialPanel(ScrolledPanel):
    """
    Panel to modify material library settings.
    In essence a material library setting is a persistent list of operations.
    They are stored in the operations.cfg file in the meerk40t working directory

    Internal development note:
    I have tried the dataview TreeListCtrl to self.display_list the different entries:
    this was crashing consistently, so I stopped following this path
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.op_data = self.context.elements.op_data
        self.SetHelpText("materialmanager")
        self.parent_panel = None
        self.current_item = None
        self._active_material = None
        self._active_operation = None
        self.no_reload = False

        # Categorisation
        # 0 = Material (thickness), 1 = Lasertype (Material), 2 = Thickness (Material)
        self.categorisation = 0
        # Intentionally not translated, to allow data exchange
        materials = [
            "Plywood",
            "Solid wood",
            "Acrylic",
            "Foam",
            "Leather",
            "Cardboard",
            "Cork",
            "Textiles",
            "Slate",
            "Paper",
            "Aluminium",
            "Steel",
            "Copper",
            "Silver",
            "Gold",
            "Metal",
        ]
        # Dictionary with key=Materialname, entry=Description (Name, Lasertype, entries)
        self.material_list = dict()
        self.operation_list = dict()
        self.display_list = list()
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        filter_box = StaticBoxSizer(
            self, wx.ID_ANY, _("Filter Materials"), wx.HORIZONTAL
        )
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Material"))
        filter_box.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_material = wx.ComboBox(
            self, wx.ID_ANY, choices=materials, style=wx.CB_SORT
        )
        # self.txt_material = TextCtrl(self, wx.ID_ANY, "", limited=True)

        filter_box.Add(self.txt_material, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, _("Thickness"))
        filter_box.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_thickness = TextCtrl(self, wx.ID_ANY, "", limited=True)
        filter_box.Add(self.txt_thickness, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label_3 = wx.StaticText(self, wx.ID_ANY, _("Laser"))
        filter_box.Add(label_3, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.laser_choices = [
            _("<All Lasertypes>"),
        ]
        dev_infos = list(self.context.find("provider/friendly"))
        # Gets a list of tuples (description, key, path)
        dev_infos.sort(key=lambda e: e[0][1])
        for e in dev_infos:
            self.laser_choices.append(e[0][0])

        self.combo_lasertype = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.laser_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_lasertype.SetMaxSize(dip_size(self, 110, -1))

        filter_box.Add(self.combo_lasertype, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_reset = wx.Button(self, wx.ID_ANY, _("Reset Filter"))
        filter_box.Add(self.btn_reset, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        main_sizer.Add(filter_box, 0, wx.EXPAND, 0)
        result_box = StaticBoxSizer(
            self, wx.ID_ANY, _("Matching library entries"), wx.VERTICAL
        )
        self.tree_library = wx.TreeCtrl(
            self,
            wx.ID_ANY,
            style=wx.BORDER_SUNKEN | wx.TR_HAS_BUTTONS
            # | wx.TR_HIDE_ROOT
            | wx.TR_ROW_LINES | wx.TR_SINGLE,
        )
        self.tree_library.SetToolTip(_("Click to select / Right click for actions"))

        self.list_preview = EditableListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.list_preview.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=55)
        self.list_preview.AppendColumn(
            _("Operation"),
            format=wx.LIST_FORMAT_LEFT,
            width=60,
        )
        self.list_preview.AppendColumn(_("Id"), format=wx.LIST_FORMAT_LEFT, width=60)
        self.list_preview.AppendColumn(
            _("Label"), format=wx.LIST_FORMAT_LEFT, width=100
        )
        self.list_preview.AppendColumn(_("Power"), format=wx.LIST_FORMAT_LEFT, width=50)
        self.list_preview.AppendColumn(_("Speed"), format=wx.LIST_FORMAT_LEFT, width=50)
        self.list_preview.SetToolTip(_("Click to select / Right click for actions"))
        self.opinfo = {
            "op cut": ("Cut", icons8_laser_beam, 0),
            "op raster": ("Raster", icons8_direction, 0),
            "op image": ("Image", icons8_image, 0),
            "op engrave": ("Engrave", icons8_laserbeam_weak, 0),
            "op dots": ("Dots", icon_points, 0),
        }
        self.state_images = wx.ImageList()
        self.state_images.Create(width=25, height=25)
        for key in self.opinfo:
            info = self.opinfo[key]
            image_id = self.state_images.Add(
                bitmap=info[1].GetBitmap(resize=(25, 25), noadjustment=True)
            )
            info = (info[0], info[1], image_id)
            self.opinfo[key] = info

        self.list_preview.AssignImageList(self.state_images, wx.IMAGE_LIST_SMALL)

        param_box = StaticBoxSizer(self, wx.ID_ANY, _("Information"), wx.VERTICAL)

        box1 = wx.BoxSizer(wx.HORIZONTAL)
        box2 = wx.BoxSizer(wx.HORIZONTAL)

        label = wx.StaticText(self, wx.ID_ANY, _("Id"))
        label.SetMinSize(
            dip_size(
                self,
                60,
                -1,
            )
        )
        box1.Add(label, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.txt_entry_section = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="empty",
        )
        box1.Add(self.txt_entry_section, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label = wx.StaticText(self, wx.ID_ANY, _("Name"))
        label.SetMinSize(
            dip_size(
                self,
                60,
                -1,
            )
        )
        box1.Add(label, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        # self.txt_entry_name = wx.TextCtrl(self, wx.ID_ANY, "")
        self.txt_entry_name = wx.ComboBox(
            self, wx.ID_ANY, choices=materials, style=wx.CB_SORT
        )

        box1.Add(self.txt_entry_name, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label = wx.StaticText(self, wx.ID_ANY, _("Thickness"))
        label.SetMinSize(
            dip_size(
                self,
                60,
                -1,
            )
        )
        box2.Add(label, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.txt_entry_thickness = TextCtrl(self, wx.ID_ANY, "", limited=True)
        box2.Add(self.txt_entry_thickness, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label = wx.StaticText(self, wx.ID_ANY, _("Laser"))
        label.SetMinSize(
            dip_size(
                self,
                60,
                -1,
            )
        )
        box2.Add(label, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        choices = self.laser_choices  # [1:]
        self.combo_entry_type = wx.ComboBox(
            self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_entry_type.SetMaxSize(dip_size(self, 110, -1))

        box2.Add(self.combo_entry_type, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_set = wx.Button(self, wx.ID_ANY, _("Set"))
        self.btn_set.SetToolTip(
            _(
                "Change the name / lasertype of the current entry\nRight-Click: assign lasertype to all visible entries"
            )
        )

        box2.Add(self.btn_set, 0, wx.EXPAND, 0)
        param_box.Add(box1, 0, wx.EXPAND, 0)
        param_box.Add(box2, 0, wx.EXPAND, 0)
        self.txt_entry_note = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_MULTILINE)
        self.txt_entry_note.SetMinSize(dip_size(self, -1, 2 * 23))
        param_box.Add(self.txt_entry_note, 0, wx.EXPAND, 0)
        result_box.Add(self.tree_library, 1, wx.EXPAND, 0)
        result_box.Add(param_box, 0, wx.EXPAND, 0)
        result_box.Add(self.list_preview, 1, wx.EXPAND, 0)

        self.txt_material.SetToolTip(_("Filter entries with a certain title."))
        self.txt_thickness.SetToolTip(
            _("Filter entries with a certain material thickness.")
        )
        self.combo_lasertype.SetToolTip(_("Filter entries of a certain laser type"))

        self.txt_entry_section.SetToolTip(_("Internal name of the library entry."))
        self.txt_entry_name.SetToolTip(_("Name of the library entry."))
        self.txt_entry_thickness.SetToolTip(_("Thickness of the material."))
        self.combo_entry_type.SetToolTip(
            _("Is this entry specific for a certain laser?")
        )
        self.txt_entry_note.SetToolTip(_("You can add additional information here."))

        button_box = wx.BoxSizer(wx.VERTICAL)

        self.btn_new = wx.Button(self, wx.ID_ANY, _("Add new"))
        self.btn_new.SetToolTip(_("Add a new library entry"))
        self.btn_use_current = wx.Button(self, wx.ID_ANY, _("Get current"))
        self.btn_use_current.SetToolTip(_("Use the currently defined operations"))
        self.btn_apply = wx.Button(self, wx.ID_ANY, _("Load into Tree"))
        self.btn_apply.SetToolTip(
            _("Apply the current library entry to the operations branch")
        )
        self.btn_simple_apply = wx.Button(self, wx.ID_ANY, _("Use for statusbar"))
        self.btn_simple_apply.SetToolTip(
            _("Use the current library entry for the statusbar icons")
        )
        self.btn_delete = wx.Button(self, wx.ID_ANY, _("Delete"))
        self.btn_delete.SetToolTip(_("Delete the current library entry"))
        self.btn_duplicate = wx.Button(self, wx.ID_ANY, _("Duplicate"))
        self.btn_duplicate.SetToolTip(_("Duplicate the current library entry"))
        self.btn_import = wx.Button(self, wx.ID_ANY, _("Import"))
        self.btn_import.SetToolTip(
            _("Import a material library from ezcad or LightBurn")
        )
        self.btn_share = wx.Button(self, wx.ID_ANY, _("Share"))
        self.btn_share.SetToolTip(
            _("Share the current library entry with the MeerK40t community")
        )

        button_box.Add(self.btn_new, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_use_current, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_apply, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_simple_apply, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_delete, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_duplicate, 0, wx.EXPAND, 0)
        button_box.AddSpacer(self.btn_duplicate.Size[1])
        button_box.Add(self.btn_import, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_share, 0, wx.EXPAND, 0)
        outer_box = wx.BoxSizer(wx.HORIZONTAL)
        outer_box.Add(result_box, 1, wx.EXPAND, 0)
        outer_box.Add(button_box, 0, wx.EXPAND, 0)
        main_sizer.Add(outer_box, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        self.Layout()
        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.combo_lasertype.Bind(wx.EVT_COMBOBOX, self.update_list)
        self.txt_material.Bind(wx.EVT_TEXT, self.update_list)
        self.txt_thickness.Bind(wx.EVT_TEXT, self.update_list)
        self.btn_new.Bind(wx.EVT_BUTTON, self.on_new)
        self.btn_use_current.Bind(wx.EVT_BUTTON, self.on_use_current)
        self.btn_apply.Bind(wx.EVT_BUTTON, self.on_apply_tree)
        self.btn_simple_apply.Bind(wx.EVT_BUTTON, self.on_apply_statusbar)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        self.btn_duplicate.Bind(wx.EVT_BUTTON, self.on_duplicate)
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import)
        self.btn_share.Bind(wx.EVT_BUTTON, self.on_share)
        self.btn_set.Bind(wx.EVT_BUTTON, self.update_entry)
        self.btn_set.Bind(wx.EVT_RIGHT_DOWN, self.update_lasertype_for_all)
        self.tree_library.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_list_selection)
        self.list_preview.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_preview_selection)
        self.list_preview.Bind(
            wx.EVT_LIST_BEGIN_LABEL_EDIT, self.before_operation_update
        )
        self.list_preview.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_operation_update)

        self.tree_library.Bind(
            wx.EVT_RIGHT_DOWN,
            self.on_library_rightclick,
        )
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_preview_rightclick, self.list_preview
        )
        self.Bind(
            wx.EVT_LIST_COL_RIGHT_CLICK, self.on_preview_rightclick, self.list_preview
        )
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.SetupScrolling()
        # Hide not-yet-supported functions
        self.btn_share.Show(False)
        self.active_material = None
        self.on_reset(None)

    @property
    def active_material(self):
        return self._active_material

    @active_material.setter
    def active_material(self, newvalue):
        self._active_material = newvalue
        active = bool(newvalue is not None)
        self.btn_apply.Enable(active)
        self.btn_simple_apply.Enable(active)
        self.btn_delete.Enable(active)
        self.btn_duplicate.Enable(active)
        self.txt_entry_section.Enable(active)
        self.txt_entry_name.Enable(active)
        self.txt_entry_thickness.Enable(active)
        self.txt_entry_note.Enable(active)
        self.combo_entry_type.Enable(active)
        self.btn_set.Enable(active)
        self.list_preview.Enable(active)
        self.fill_preview()

    def retrieve_material_list(
        self,
        filtername=None,
        filterlaser=None,
        filterthickness=None,
        reload=True,
        setter=None,
    ):
        if reload:
            self.material_list.clear()
            for section in self.op_data.section_set():
                if section == "previous":
                    continue
                count = 0
                secname = section
                secdesc = ""
                thick = ""
                ltype = 0  # All lasers
                note = ""
                for subsection in self.op_data.derivable(secname):
                    if subsection.endswith(" info"):
                        secdesc = self.op_data.read_persistent(
                            str, subsection, "name", secname
                        )
                        thick = self.op_data.read_persistent(
                            str, subsection, "thickness", ""
                        )
                        ltype = self.op_data.read_persistent(
                            int, subsection, "laser", 0
                        )
                        note = self.op_data.read_persistent(str, subsection, "note", "")
                    else:
                        count += 1

                entry = [secname, secdesc, count, ltype, thick, note]
                self.material_list[secname] = entry
        listidx = -1
        self.display_list.clear()
        display = []

        if self.categorisation == 1:
            # lasertype
            sort_key_primary = 3
            sort_key_secondary = 1
            sort_key_tertiary = 4
        elif self.categorisation == 2:
            # thickness
            sort_key_primary = 4
            sort_key_secondary = 1
            sort_key_tertiary = 3
        else:
            # material
            sort_key_primary = 1
            sort_key_secondary = 4
            sort_key_tertiary = 3
        for key, entry in self.material_list.items():
            listidx += 1
            display.append((entry[0], entry[1], entry[2], entry[3], entry[4], listidx))
        display.sort(
            key=lambda e: (
                e[sort_key_primary],
                e[sort_key_secondary],
                e[sort_key_tertiary],
            )
        )

        tree = self.tree_library
        tree.DeleteAllItems()
        tree_root = tree.AddRoot(_("Materials"))
        tree.SetItemData(tree_root, -1)
        idx_primary = 0
        idx_secondary = 0
        newvalue = None
        selected = None
        first_item = None
        selected_parent = None
        last_category_primary = None
        last_category_secondary = None
        tree_primary = tree_root
        tree_secondary = tree_root
        visible_count = [0, 0]  # All, subsections
        for entry in display:
            ltype = entry[3]
            if ltype is None:
                ltype = 0
            if 0 <= ltype < len(self.laser_choices):
                info = self.laser_choices[ltype]
            else:
                info = "???"
            if sort_key_primary == 3:  # laser
                this_category_primary = info
            else:
                this_category_primary = entry[sort_key_primary]
            if sort_key_secondary == 3:  # laser
                this_category_secondary = info
            else:
                this_category_secondary = entry[sort_key_secondary]
            key = entry[0]
            listidx = entry[5]
            if filtername is not None and filtername.lower() not in entry[1].lower():
                continue
            if filterthickness is not None and not entry[4].lower().startswith(
                filterthickness.lower()
            ):
                continue
            if filterlaser is not None:
                if filterlaser == 0 or filterlaser == entry[3]:
                    pass
                else:
                    continue
            self.display_list.append(entry)
            visible_count[0] += 1
            if last_category_primary != this_category_primary:
                # New item
                last_category_secondary = ""
                idx_primary += 1
                idx_secondary = 0
                tree_primary = tree.AppendItem(tree_root, this_category_primary)
                tree.SetItemData(tree_primary, -1)
                tree_secondary = tree_primary
            if last_category_secondary != this_category_secondary:
                # new subitem
                tree_secondary = tree.AppendItem(tree_primary, this_category_secondary)
                tree.SetItemData(tree_secondary, -1)
                visible_count[1] += 1
            idx_secondary += 1

            description = f"#{idx_primary}.{idx_secondary} - {entry[1]}, {entry[4]} ({info}, {entry[2]} ops)"
            tree_id = tree.AppendItem(tree_secondary, description)
            tree.SetItemData(tree_id, listidx)
            if first_item is None:
                first_item = tree_id
            if key == setter:
                newvalue = key
                selected = tree_id
                selected_parent = tree_primary

            last_category_primary = this_category_primary
            last_category_secondary = this_category_secondary

        self.active_material = newvalue
        tree.Expand(tree_root)
        # if visible_count[0] <= 10:
        #     tree.ExpandAllChildren(tree_root)
        if visible_count[1] == 1:
            tree.ExpandAllChildren(tree_root)
        elif visible_count[1] <= 10:
            child, cookie = tree.GetFirstChild(tree_root)
            while child.IsOk():
                tree.Expand(child)
                child, cookie = tree.GetNextChild(tree_root, cookie)

        if selected is None:
            if visible_count[0] == 1:  # Just one, why don't we select it
                self.tree_library.SelectItem(first_item)
        else:
            tree.ExpandAllChildren(selected_parent)
            self.tree_library.SelectItem(selected)

    @staticmethod
    def get_nth_dict_entry(dictionary: dict, n=0):
        if n < 0:
            n += len(dictionary)
        for i, key in enumerate(dictionary.keys()):
            if i == n:
                return key
        return None

    def get_nth_material(self, n=0):
        return self.get_nth_dict_entry(self.material_list, n)

    def get_nth_operation(self, n=0):
        return self.get_nth_dict_entry(self.operation_list, n)

    def on_share(self, event):
        if self.active_material is None:
            return

        self.context.setting(str, "author", "")
        last_author = self.context.author
        if last_author is None:
            last_author = ""
        dlg = wx.TextEntryDialog(
            self,
            _(
                "Thank you for your willingness to share your material setting with the MeerK40t community.\n"
                + "Please provide a name to honor your authorship."
            ),
            caption=_("Share material setting"),
            value=last_author,
        )
        dlg.SetValue(last_author)
        res = dlg.ShowModal()
        last_author = dlg.GetValue()
        dlg.Destroy()
        if res == wx.ID_CANCEL:
            return
        self.context.author = last_author
        # We will store the relevant section in a separate file
        oplist, opinfo = self.context.elements.load_persistent_op_list(
            self.active_material,
            use_settings=self.op_data,
        )
        if len(oplist) == 0:
            return
        opinfo["author"] = last_author
        directory = get_safe_path(self.context.kernel.name)
        local_file = os.path.join(directory, "op_export.cfg")
        if os.path.exists(local_file):
            try:
                os.remove(local_file)
            except (OSError, PermissionError):
                return
        settings = Settings(
            self.context.kernel.name, "op_export.cfg", ignore_settings=False
        )
        opsection = f"{self.active_material} info"
        for key, value in opinfo.items():
            settings.write_persistent(opsection, key, value)

        def _save_tree(name, op_list):
            for i, op in enumerate(op_list):
                if hasattr(op, "allow_save"):
                    if not op.allow_save():
                        continue
                if op.type == "reference":
                    # We do not save references.
                    continue
                section = f"{name} {i:06d}"
                settings.write_persistent(section, "type", op.type)
                op.save(settings, section)
                try:
                    _save_tree(section, op.children)
                except AttributeError:
                    pass

        _save_tree(opsection, oplist)
        settings.write_configuration()
        # print ("Sharing")
        try:
            with open(local_file, "r") as f:
                data = f.read()
        except:
            return
        self.send_data_to_developers(local_file, data)

    def send_data_to_developers(self, filename, data):
        """
        Sends crash log to a server using rfc1341 7.2 The multipart Content-Type
        https://www.w3.org/Protocols/rfc1341/7_2_Multipart.html

        @param filename: filename to use when sending file
        @param data: data to send
        @return:
        """
        import socket

        MEERK40T_HOST = "dev.meerk40t.com"

        host = MEERK40T_HOST  # Replace with the actual host
        port = 80  # Replace with the actual port

        # Construct the HTTP request
        boundary = "----------------meerk40t-material"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: text/plain\r\n"
            "\r\n"
            f"{data}\r\n"
            f"--{boundary}--\r\n"
        )

        headers = (
            f"POST /upload HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "User-Agent: meerk40t/1.0.0\r\n"
            f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "\r\n"
        )

        try:
            # Create a socket connection
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((host, port))

                # Send the request
                request = f"{headers}{body}"
                client_socket.sendall(request.encode())

                # Receive and print the response
                response = client_socket.recv(4096)
                response = response.decode("utf-8")
        except Exception:
            response = ""

        response_lines = response.split("\n")
        http_code = response_lines[0]

        # print(response)

        if http_code.startswith("HTTP/1.1 200 OK"):
            message = response_lines[-1]
            dlg = wx.MessageDialog(
                None,
                _("We got your file. Thank you for helping\n\n") + message,
                _("Thanks"),
                wx.OK,
            )
            dlg.ShowModal()
            dlg.Destroy()
        else:
            # print(response)
            dlg = wx.MessageDialog(
                None,
                _("We're sorry, that didn't work.\n\n") + "\n\n" + str(http_code),
                _("Thanks"),
                wx.OK,
            )
            dlg.ShowModal()
            dlg.Destroy()

    def on_duplicate(self, event):
        if self.active_material is None:
            return
        op_list, op_info = self.context.elements.load_persistent_op_list(
            self.active_material,
            use_settings=self.op_data,
        )
        if len(op_list) == 0:
            return
        oldsection = self.active_material
        if oldsection.endswith(")"):
            idx = oldsection.rfind("(")
            if idx >= 0:
                oldsection = oldsection[:idx]
                if oldsection.endswith("_"):
                    oldsection = oldsection[:-1]

        counter = 0
        while True:
            counter += 1
            newsection = f"{oldsection}_({counter})"
            if newsection not in self.material_list:
                break

        # print (f"Section={oldsection} -> {newsection}")

        oldname = oldsection
        if "name" in op_info:
            oldname = op_info["name"]
            if oldname.endswith(")"):
                idx = oldname.rfind("(")
                if idx >= 0:
                    oldname = oldname[:idx]
        newname = f"{oldname} ({counter})"
        op_info["name"] = newname
        self.context.elements.save_persistent_operations_list(
            newsection,
            oplist=op_list,
            opinfo=op_info,
            inform=False,
            use_settings=self.op_data,
        )
        self.retrieve_material_list(reload=True, setter=newsection)

    def on_delete(self, event):
        if self.active_material is None:
            return
        if self.context.kernel.yesno(
            _("Do you really want to delete this entry? This can't be undone.")
        ):
            self.context.elements.clear_persistent_operations(
                self.active_material,
                use_settings=self.op_data,
            )
            self.retrieve_material_list(reload=True)

    def on_delete_all(self, event):
        if self.context.kernel.yesno(
            _("Do you really want to delete all visible entries? This can't be undone.")
        ):
            for entry in self.display_list:
                material = entry[0]
                self.context.elements.clear_persistent_operations(
                    material,
                    use_settings=self.op_data,
                )
            self.on_reset(None)

    def invalid_file(self, filename):
        dlg = wx.MessageDialog(
            self,
            _("Unrecognized format in file {info}".format(info=filename)),
            _("Invalid file"),
            wx.OK | wx.ICON_WARNING,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def import_lightburn(self, filename):
        if not os.path.exists(filename):
            return False
        added = False
        try:
            tree = ET.parse(filename)
        except ET.ParseError:
            self.invalid_file(filename)
            return False

        root = tree.getroot()
        if root.tag.lower() != "lightburnlibrary":
            self.invalid_file(filename)
            return False

        # We need to have a new id...
        new_import_id = 0
        pattern = "import_"
        for section in self.op_data.section_set():
            if section.startswith(pattern):
                s = section[len(pattern) :]
                try:
                    number = int(s)
                except ValueError:
                    number = 0
                if number > new_import_id:
                    new_import_id = number

        # def traverse(node):
        #     print(f"Node: {node.tag}")
        #     for attr in node.attrib:
        #         print(f"Attribute: {attr} = {node.attrib[attr]}")
        #     for child in node:
        #         traverse(child)
        # traverse(root)

        for material_node in root:
            material = material_node.attrib["name"]
            for entry_node in material_node:
                thickness = entry_node.attrib.get("Thickness", "-1")
                try:
                    thickness_value = float(thickness)
                except ValueError:
                    thickness_value = -1
                if thickness_value < 0:
                    thickness = ""
                desc = entry_node.attrib.get("Desc", "")
                title = entry_node.attrib.get("NoThickTitle", "")
                new_import_id += 1
                sect_num = -1
                sect = f"{pattern}{new_import_id:0>4}"
                info_section_name = f"{sect} info"
                self.op_data.write_persistent(info_section_name, "name", material)
                self.op_data.write_persistent(info_section_name, "laser", 0)
                self.op_data.write_persistent(info_section_name, "thickness", thickness)
                note = f"{desc} - {title}"
                added = True
                for cutsetting_node in entry_node:
                    sect_num += 1
                    section_name = f"{sect} {sect_num:0>6}"
                    cut_type = cutsetting_node.attrib.get("type", "Scan")
                    if cut_type.lower() == "cut":
                        op_type = "op engrave"
                    elif cut_type.lower() == "scan":
                        op_type = "op raster"
                    else:
                        op_type = "op engrave"
                    self.op_data.write_persistent(section_name, "type", op_type)
                    self.op_data.write_persistent(
                        section_name, "label", f"{desc} - {title}"
                    )

                    for param_node in cutsetting_node:
                        param = param_node.tag.lower()
                        value = param_node.attrib.get("Value", "")
                        if not value:
                            continue
                        try:
                            numeric_value = float(value)
                        except ValueError:
                            continue

                        if param == "numpasses":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "passes", numeric_value
                                )
                        elif param == "speed":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "speed", numeric_value
                                )
                        elif param == "maxpower":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "power", numeric_value * 10
                                )
                        elif param == "frequency":
                            # khz
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "frequency", numeric_value / 1000.0
                                )
                        elif param == "jumpspeed":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "rapid_enabled", True
                                )
                                self.op_data.write_persistent(
                                    section_name, "rapid_speed", numeric_value
                                )
                        else:
                            note += f"\\n{param} = {numeric_value}"
                self.op_data.write_persistent(info_section_name, "note", note)

        return added

    def import_ezcad(self, filename):
        if not os.path.exists(filename):
            return False
        added = False
        # We can safely assume this a fibre laser...
        laser_type = 0
        for idx, desc in enumerate(self.laser_choices):
            if "fibre" in desc.lower():
                laser_type = idx
                break
        try:
            with open(filename, "r") as f:
                # We need to have a new id...
                new_import_id = 0
                pattern = "import_"
                for section in self.op_data.section_set():
                    if section.startswith(pattern):
                        s = section[len(pattern) :]
                        try:
                            number = int(s)
                        except ValueError:
                            number = 0
                        if number > new_import_id:
                            new_import_id = number
                section_name = ""
                info_section_name = ""
                info_box = ""
                while True:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line.startswith("[F "):
                        if info_box and info_section_name:
                            self.op_data.write_persistent(
                                info_section_name, "note", info_box
                            )
                        info_box = ""
                        new_import_id += 1
                        sect = f"{pattern}{new_import_id:0>4}"
                        info_section_name = f"{sect} info"
                        section_name = f"{sect} {0:0>6}"
                        matname = line[3:-1]
                        self.op_data.write_persistent(
                            info_section_name, "name", matname
                        )
                        self.op_data.write_persistent(
                            info_section_name, "laser", laser_type
                        )
                        self.op_data.write_persistent(
                            section_name, "type", "op engrave"
                        )
                        added = True
                    elif line.startswith("["):
                        if info_box and info_section_name:
                            self.op_data.write_persistent(
                                info_section_name, "note", info_box
                            )
                        # Anything else...
                        section_name = ""
                        info_section_name = ""
                        info_box = ""
                    else:
                        if not section_name:
                            continue
                        idx = line.find("=")
                        if idx <= 0:
                            continue
                        param = line[:idx].lower()
                        value = line[idx + 1 :]
                        try:
                            numeric_value = float(value)
                        except ValueError:
                            numeric_value = 0
                        if param == "loop":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "passes", numeric_value
                                )
                        elif param == "markspeed":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "speed", numeric_value
                                )
                        elif param == "powerratio":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "power", numeric_value * 10
                                )
                        elif param == "freq":
                            # khz
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "frequency", numeric_value / 1000.0
                                )
                        elif param == "jumpspeed":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "rapid_enabled", True
                                )
                                self.op_data.write_persistent(
                                    section_name, "rapid_speed", numeric_value
                                )
                        elif param == "starttc":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "timing_enabled", True
                                )
                                self.op_data.write_persistent(
                                    section_name, "delay_laser_on", numeric_value
                                )
                        elif param == "laserofftc":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "timing_enabled", True
                                )
                                self.op_data.write_persistent(
                                    section_name, "delay_laser_off", numeric_value
                                )
                        elif param == "polytc":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "timing_enabled", True
                                )
                                self.op_data.write_persistent(
                                    section_name, "delay_polygon", numeric_value
                                )
                        elif param == "qpulsewidth":
                            if numeric_value != 0:
                                self.op_data.write_persistent(
                                    section_name, "pulse_width_enabled", True
                                )
                                self.op_data.write_persistent(
                                    section_name, "pulse_width", numeric_value
                                )
                        else:
                            # Unknown / unsupported - a significant amount of the parameters
                            # would require the addition of different things like hatches,
                            # wobbles or device specific settings
                            if numeric_value != 0:
                                if info_box:
                                    info_box += "\\n"
                                info_box += f"{param} = {numeric_value}"
                # Residual information available?
                if info_box and info_section_name:
                    self.op_data.write_persistent(info_section_name, "note", info_box)

        except (OSError, RuntimeError, PermissionError, FileNotFoundError):
            return False
        if added:
            self.op_data.write_configuration()
        return added

    def on_import(self, event):
        #
        myfile = ""
        mydlg = wx.FileDialog(
            self,
            message=_("Choose a library-file"),
            wildcard="Supported files|*.lib;*.clb|EZcad files (*.lib)|*.lib|Lightburn files (*.clb)|*.clb|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW,
        )
        if mydlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            myfile = mydlg.GetPath()
        mydlg.Destroy()
        if myfile == "":
            return
        added = False
        if myfile.endswith(".clb"):
            added = self.import_lightburn(myfile)
        elif myfile.endswith(".lib"):
            added = self.import_ezcad(myfile)
        else:
            self.invalid_file(myfile)

        if added:
            self.on_reset(None)

    def on_apply_statusbar(self, event):
        if self.active_material is None:
            return
        op_list, op_info = self.context.elements.load_persistent_op_list(
            self.active_material,
            use_settings=self.op_data,
        )
        if len(op_list) == 0:
            return
        self.context.elements.default_operations = list(op_list)
        self.context.signal("default_operations")

    def on_apply_tree(self, event):
        if self.active_material is None:
            return
        op_list, op_info = self.context.elements.load_persistent_op_list(
            self.active_material,
            use_settings=self.op_data,
        )
        if len(op_list) == 0:
            return
        response = self.context.kernel.yesno(
            _(
                "Do you want to remove all existing operations before loaading this set?"
            ),
            caption=_("Clear Operation-List"),
        )
        self.context.elements.load_persistent_operations(
            self.active_material, clear=response
        )
        self.context.signal("rebuild_tree")

    def on_new(self, event):
        section = None
        op_info = None
        entry_txt = self.txt_material.GetValue()
        if entry_txt == "":
            entry_txt = "material"
        if entry_txt in self.material_list:
            idx = 0
            while True:
                idx += 1
                pattern = f"{entry_txt}_({idx})"
                if pattern not in self.material_list:
                    break
            entry_txt = pattern
        entry_type = self.combo_entry_type.GetSelection()
        if entry_type < 0:
            entry_type = 0
        # We need to create a new one...
        op_info = dict()
        op_info["name"] = "New material"
        op_info["laser"] = 0
        op_info["thickness"] = "4mm"
        op_info["note"] = "You can put additional operation instructions here."
        section = entry_txt

        if len(list(self.context.elements.ops())) == 0:
            op_list = self.context.elements.default_operations
            if len(op_list) == 0:
                return
            # op_list = None save op_branch
            self.context.elements.save_persistent_operations_list(
                section,
                oplist=op_list,
                opinfo=op_info,
                inform=False,
                use_settings=self.op_data,
            )
        else:
            # op_list = None save op_branch
            self.context.elements.save_persistent_operations_list(
                section,
                oplist=None,
                opinfo=op_info,
                inform=False,
                use_settings=self.op_data,
            )
        self.retrieve_material_list(reload=True, setter=section)

    def on_use_current(self, event):
        section = None
        op_info = None
        if self.active_material is not None:
            if self.context.kernel.yesno(
                _(
                    "Do you want to use the operations in the tree for the current entry?"
                )
            ):
                section = self.active_material
                op_info = self.context.elements.load_persistent_op_info(
                    self.active_material,
                    use_settings=self.op_data,
                )
                if "name" not in op_info:
                    op_info["name"] = "Operations List"
                if "laser" not in op_info:
                    op_info["laser"] = 0

        if section is None:
            entry_txt = self.txt_material.GetValue()
            if entry_txt == "":
                entry_txt = "material"
            if entry_txt in self.material_list:
                idx = 0
                while True:
                    idx += 1
                    pattern = f"{entry_txt}_({idx})"
                    if pattern not in self.material_list:
                        break
                entry_txt = pattern
            entry_type = self.combo_entry_type.GetSelection()
            if entry_type < 0:
                entry_type = 0
            # We need to create a new one...
            op_info = dict()
            op_info["name"] = "New material"
            op_info["laser"] = 0
            section = entry_txt

        # op_list = None save op_branch
        self.context.elements.save_persistent_operations_list(
            section,
            oplist=None,
            opinfo=op_info,
            inform=False,
            use_settings=self.op_data,
        )
        self.retrieve_material_list(reload=True, setter=section)

    def on_reset(self, event):
        self.no_reload = True
        self.txt_material.SetValue("")
        self.txt_thickness.SetValue("")
        self.combo_lasertype.SetSelection(0)
        self.no_reload = False
        self.update_list(reload=True)

    def update_list(self, *args, **kwargs):
        if self.no_reload:
            return
        filter_txt = self.txt_material.GetValue()
        filter_thickness = self.txt_thickness.GetValue()
        filter_type = self.combo_lasertype.GetSelection()
        if filter_txt == "":
            filter_txt = None
        if filter_thickness == "":
            filter_thickness = None
        if filter_type < 0:
            filter_type = None
        reload = False
        if "reload" in kwargs:
            reload = kwargs["reload"]
        self.retrieve_material_list(
            filtername=filter_txt,
            filterlaser=filter_type,
            filterthickness=filter_thickness,
            reload=reload,
            setter=self.active_material,
        )

    def update_lasertype_for_all(self, event):
        op_ltype = self.combo_entry_type.GetSelection()
        if op_ltype < 0:
            return
        for entry in self.display_list:
            material = entry[0]
            section = f"{material} info"
            self.op_data.write_persistent(section, "laser", op_ltype)
        self.on_reset(None)

    def update_entry(self, event):
        if self.active_material is None:
            return
        op_section = self.txt_entry_section.GetValue()
        op_name = self.txt_entry_name.GetValue()
        op_thickness = self.txt_entry_thickness.GetValue()
        op_ltype = self.combo_entry_type.GetSelection()
        op_note = self.txt_entry_note.GetValue()
        # Convert linebreaks
        op_note = op_note.replace("\n", "\\n")
        if op_ltype < 0:
            op_ltype = 0
        op_list, op_info = self.context.elements.load_persistent_op_list(
            self.active_material,
            use_settings=self.op_data,
        )
        if len(op_list) == 0:
            return
        stored_name = ""
        stored_note = ""
        stored_thickness = ""
        stored_ltype = 0
        if "name" in op_info:
            stored_name = op_info["name"]
        if "thickness" in op_info:
            stored_thickness = op_info["thickness"]
        if "note" in op_info:
            stored_note = op_info["note"]
        if "laser" in op_info:
            stored_ltype = op_info["laser"]
        if (
            stored_name != op_name
            or stored_thickness != op_thickness
            or stored_ltype != op_ltype
            or stored_note != op_note
            or op_section != self.active_material
        ):
            if self.active_material != op_section:
                self.context.elements.clear_persistent_operations(
                    self.active_material,
                    use_settings=self.op_data,
                )
                self.active_material = op_section
            op_info["laser"] = op_ltype
            op_info["name"] = op_name
            op_info["thickness"] = op_thickness
            op_info["note"] = op_note
            self.context.elements.save_persistent_operations_list(
                self.active_material,
                oplist=op_list,
                opinfo=op_info,
                inform=False,
                use_settings=self.op_data,
            )
            self.retrieve_material_list(reload=True, setter=self.active_material)

    def on_list_selection(self, event):
        try:
            item = event.GetItem()
            if item:
                listidx = self.tree_library.GetItemData(item)
                if listidx >= 0:
                    self.active_material = self.get_nth_material(listidx)
        except RuntimeError:
            return

    def fill_preview(self):
        self.list_preview.DeleteAllItems()
        self.operation_list.clear()
        secdesc = ""
        thickness = ""
        note = ""
        ltype = 0
        if self.active_material is not None:
            secdesc = self.active_material
            idx = 0
            for subsection in self.op_data.derivable(self.active_material):
                if subsection.endswith(" info"):
                    secdesc = self.op_data.read_persistent(
                        str, subsection, "name", secdesc
                    )
                    thickness = self.op_data.read_persistent(
                        str, subsection, "thickness", ""
                    )
                    ltype = self.op_data.read_persistent(int, subsection, "laser", 0)
                    note = self.op_data.read_persistent(str, subsection, "note", "")
                    # We need to replace stored linebreaks with real linebreaks
                    note = note.replace("\\n", "\n")
                    continue
                optype = self.op_data.read_persistent(str, subsection, "type", "")
                if optype is None or optype == "":
                    continue
                idx += 1
                opid = self.op_data.read_persistent(str, subsection, "id", "")
                oplabel = self.op_data.read_persistent(str, subsection, "label", "")
                speed = self.op_data.read_persistent(str, subsection, "speed", "")
                power = self.op_data.read_persistent(str, subsection, "power", "")
                if power == "" and optype.startswith("op "):
                    power = "1000"
                list_id = self.list_preview.InsertItem(
                    self.list_preview.GetItemCount(), f"#{idx}"
                )
                try:
                    info = self.opinfo[optype]
                except KeyError:
                    continue

                self.list_preview.SetItem(list_id, 1, info[0])
                self.list_preview.SetItem(list_id, 2, opid)
                self.list_preview.SetItem(list_id, 3, oplabel)
                self.list_preview.SetItem(list_id, 4, power)
                self.list_preview.SetItem(list_id, 5, speed)
                self.list_preview.SetItemImage(list_id, info[2])
                self.list_preview.SetItemData(list_id, idx - 1)
                self.operation_list[subsection] = (optype, opid, oplabel, power, speed)

        if self.active_material is None:
            actval = ""
        else:
            actval = self.active_material
        self.txt_entry_section.SetValue(actval)
        self.txt_entry_name.SetValue(secdesc)
        self.txt_entry_thickness.SetValue(thickness)
        self.txt_entry_note.SetValue(note)
        self.combo_entry_type.SetSelection(ltype)

    def on_preview_selection(self, event):
        pass

    def on_library_rightclick(self, event):
        event.Skip()
        menu = wx.Menu()
        item = menu.Append(wx.ID_ANY, _("Add new"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_new, item)

        item = menu.Append(wx.ID_ANY, _("Get current"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_use_current, item)

        item = menu.Append(wx.ID_ANY, _("Load into Tree"), "", wx.ITEM_NORMAL)
        menu.Enable(item.GetId(), bool(self.active_material is not None))
        self.Bind(wx.EVT_MENU, self.on_apply_tree, item)

        item = menu.Append(wx.ID_ANY, _("Use for statusbar"), "", wx.ITEM_NORMAL)
        menu.Enable(item.GetId(), bool(self.active_material is not None))
        self.Bind(wx.EVT_MENU, self.on_apply_statusbar, item)

        item = menu.Append(wx.ID_ANY, _("Duplicate"), "", wx.ITEM_NORMAL)
        menu.Enable(item.GetId(), bool(self.active_material is not None))
        self.Bind(wx.EVT_MENU, self.on_duplicate, item)

        item = menu.Append(wx.ID_ANY, _("Delete"), "", wx.ITEM_NORMAL)
        menu.Enable(item.GetId(), bool(self.active_material is not None))
        self.Bind(wx.EVT_MENU, self.on_delete, item)

        menu.AppendSeparator()

        item = menu.Append(wx.ID_ANY, _("Share"), "", wx.ITEM_NORMAL)
        menu.Enable(item.GetId(), bool(self.active_material is not None))
        self.Bind(wx.EVT_MENU, self.on_share, item)

        def create_minimal(event):
            section = "minimal"
            oplist = self.context.elements.create_minimal_op_list()
            opinfo = {"name": "Minimal list", "laser": 0}
            self.context.elements.save_persistent_operations_list(
                section,
                oplist,
                opinfo,
                False,
                use_settings=self.op_data,
            )
            self.retrieve_material_list(reload=True, setter=section)

        def create_basic(event):
            section = "basic"
            oplist = self.context.elements.create_basic_op_list()
            opinfo = {"name": "Basic list", "laser": 0}
            self.context.elements.save_persistent_operations_list(
                section,
                oplist,
                opinfo,
                False,
                use_settings=self.op_data,
            )
            self.retrieve_material_list(reload=True, setter=section)

        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY, _("Create minimal"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, create_minimal, item)
        item = menu.Append(wx.ID_ANY, _("Create basic"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, create_basic, item)
        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY, _("Delete all"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_delete_all, item)
        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY, _("Sort by..."), "", wx.ITEM_NORMAL)
        menu.Enable(item.GetId(), False)

        def set_sort_key(sortvalue):
            local_value = sortvalue

            def sort_handler(event):
                self.categorisation = local_value
                self.retrieve_material_list(reload=False, setter=self.active_material)

            return sort_handler

        item = menu.Append(wx.ID_ANY, _("Material"), "", wx.ITEM_RADIO)
        item.Check(bool(self.categorisation == 0))
        self.Bind(wx.EVT_MENU, set_sort_key(0), item)
        item = menu.Append(wx.ID_ANY, _("Laser"), "", wx.ITEM_RADIO)
        item.Check(bool(self.categorisation == 1))
        self.Bind(wx.EVT_MENU, set_sort_key(1), item)
        item = menu.Append(wx.ID_ANY, _("Thickness"), "", wx.ITEM_RADIO)
        item.Check(bool(self.categorisation == 2))
        self.Bind(wx.EVT_MENU, set_sort_key(2), item)
        menu.AppendSeparator()

        def on_expand(flag):
            def exp_handler(event):
                tree = self.tree_library
                tree_root = tree.GetRootItem()
                child, cookie = tree.GetFirstChild(tree_root)
                while child.IsOk():
                    if local_flag:
                        tree.ExpandAllChildren(child)
                    else:
                        tree.CollapseAllChildren(child)
                    child, cookie = tree.GetNextChild(tree_root, cookie)

            local_flag = flag
            return exp_handler

        item = menu.Append(wx.ID_ANY, _("Expand all"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, on_expand(True), item)
        item = menu.Append(wx.ID_ANY, _("Collapse all"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, on_expand(False), item)

        self.PopupMenu(menu)
        menu.Destroy()

    def on_preview_rightclick(self, event):
        event.Skip()
        if self.active_material is None:
            return
        listindex = event.Index
        index = self.list_preview.GetItemData(listindex)
        key = self.get_nth_operation(index)

        menu = wx.Menu()

        def on_menu_popup_delete(op_section):
            def remove_handler(*args):
                settings = self.op_data
                # print (f"Remove {sect}")
                settings.clear_persistent(sect)
                self.fill_preview()

            sect = op_section
            return remove_handler

        def on_menu_popup_apply_to_tree(op_section):
            def apply_to_tree_handler(*args):
                settings = self.op_data
                op_type = settings.read_persistent(str, sect, "type")
                try:
                    targetop = Node().create(type=op_type)
                except ValueError:
                    # Attempted to create a non-boostrapped node type.
                    return
                targetop.load(settings, sect)
                op_id = targetop.id
                if op_id is None:
                    # WTF, that should not be the case
                    op_list = [targetop]
                    self.context.elements.validate_ids(nodelist=op_list, generic=False)
                newone = True
                for op in self.context.elements.ops():
                    # Already existing?
                    if op.id == targetop.id:
                        newone = False
                        self.context.elements.op_branch.replace_node(targetop)
                        break
                if newone:
                    try:
                        self.context.elements.op_branch.add_node(targetop)
                    except ValueError:
                        # This happens when he have somehow lost sync with the node,
                        # and we try to add a node that is already added...
                        # In principle this should be covered by the check
                        # above, but you never know
                        pass
                self.context.signal("rebuild_tree")

            sect = op_section
            return apply_to_tree_handler

        def on_menu_popup_apply_to_statusbar(op_section):
            def apply_to_tree_handler(*args):
                settings = self.op_data
                op_type = settings.read_persistent(str, sect, "type")
                try:
                    targetop = Node().create(type=op_type)
                except ValueError:
                    # Attempted to create a non-boostrapped node type.
                    return
                targetop.load(settings, sect)
                op_id = targetop.id
                if op_id is None:
                    # WTF, that should not be the case
                    op_list = [targetop]
                    self.context.elements.validate_ids(nodelist=op_list, generic=False)
                newone = True
                for idx, op in enumerate(self.context.elements.default_operations):
                    # Already existing?
                    if op.id == targetop.id:
                        newone = False
                        self.context.elements.default_operations[idx] = targetop
                        break
                if newone:
                    self.context.elements.default_operations.append(targetop)
                self.context.signal("default_operations")

            sect = op_section
            return apply_to_tree_handler

        if key:
            item = menu.Append(wx.ID_ANY, _("Remove"), "", wx.ITEM_NORMAL)
            self.Bind(wx.EVT_MENU, on_menu_popup_delete(key), item)

            menu.AppendSeparator()

            item = menu.Append(wx.ID_ANY, _("Load into Tree"), "", wx.ITEM_NORMAL)
            self.Bind(wx.EVT_MENU, on_menu_popup_apply_to_tree(key), item)

            item = menu.Append(wx.ID_ANY, _("Use for statusbar"), "", wx.ITEM_NORMAL)
            menu.Enable(item.GetId(), bool(self.active_material is not None))
            self.Bind(wx.EVT_MENU, on_menu_popup_apply_to_statusbar(key), item)

        menu.AppendSeparator()

        def on_menu_popup_missing(*args):
            if self.active_material is None:
                return
            op_list, op_info = self.context.elements.load_persistent_op_list(
                self.active_material,
                use_settings=self.op_data,
            )
            if len(op_list) == 0:
                return
            changes = False
            # Which ones do we have already?
            uid = list()
            for op in enumerate(op_list):
                if hasattr(op, "id") and op.id is not None:
                    list.append(op.id)
            for op in op_list:
                if hasattr(op, "label") and op.label is None:
                    pattern = op.type
                    if pattern.startswith("op "):
                        pattern = pattern[3].upper() + pattern[4:]
                    info = False
                    s1 = ""
                    s2 = ""
                    if hasattr(op, "power"):
                        if op.power is None:
                            pwr = 1000
                        else:
                            pwr = op.power
                        s1 = f"{pwr/10.0:.0f}%"
                    if hasattr(op, "speed") and op.speed is not None:
                        s2 = f"{op.speed:.0f}mm/s"
                    if s1 or s2:
                        pattern += f" ({s1}{', ' if s1 and s2 else ''}{s2})"
                    op.label = pattern
                    changes = True
                if hasattr(op, "id") and op.id is None:
                    changes = True
                    if op.type.startswith("op "):
                        pattern = op.type[3].upper()
                    else:
                        pattern = op.type[0:1].upper()
                    idx = 1
                    while f"{pattern}{idx}" in uid:
                        idx += 1
                    op.id = f"{pattern}{idx}"
                    uid.append(op.id)

            if changes:
                self.context.elements.save_persistent_operations_list(
                    self.active_material,
                    op_list,
                    op_info,
                    flush=False,
                    use_settings=self.op_data,
                )
                self.fill_preview()

        item = menu.Append(wx.ID_ANY, _("Fill missing ids/label"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, on_menu_popup_missing, item)

        self.PopupMenu(menu)
        menu.Destroy()

    def on_resize(self, event):
        # Resize the columns in the listctrl
        size = self.list_preview.GetSize()
        if size[0] == 0 or size[1] == 0:
            return
        remaining = size[0]
        # 0 "#"
        # 1 "Operation"
        # 2 "Id"
        # 3 "Label"
        # 4 "Power"
        # 5 "Speed"

        self.list_preview.SetColumnWidth(0, int(0.10 * remaining))
        self.list_preview.SetColumnWidth(1, int(0.15 * remaining))
        self.list_preview.SetColumnWidth(2, int(0.15 * remaining))
        self.list_preview.SetColumnWidth(3, int(0.40 * remaining))
        self.list_preview.SetColumnWidth(4, int(0.10 * remaining))
        self.list_preview.SetColumnWidth(5, int(0.10 * remaining))

    def before_operation_update(self, event):
        list_id = event.GetIndex()  # Get the current row
        col_id = event.GetColumn()  # Get the current column
        if col_id in (2, 3, 4, 5):
            event.Allow()
        else:
            event.Veto()

    def on_operation_update(self, event):
        list_id = event.GetIndex()  # Get the current row
        col_id = event.GetColumn()  # Get the current column
        new_data = event.GetLabel()  # Get the changed data
        index = self.list_preview.GetItemData(list_id)
        key = self.get_nth_operation(index)

        if list_id >= 0 and col_id in (2, 3, 4, 5):
            if col_id == 2:
                # id
                self.op_data.write_persistent(key, "id", new_data)
            elif col_id == 3:
                # label
                self.op_data.write_persistent(key, "label", new_data)
            elif col_id == 4:
                # power
                self.op_data.write_persistent(key, "power", new_data)
            elif col_id == 5:
                # speed
                self.op_data.write_persistent(key, "speed", new_data)
            # Set the new data in the listctrl
            self.list_preview.SetItem(list_id, col_id, new_data)

    def set_parent(self, par_panel):
        self.parent_panel = par_panel

    def pane_show(self):
        self.update_list(reload=True)

    def pane_hide(self):
        pass


class ImportPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.parent_panel = None
        self.context = context
        self.library_entries = []
        self.visible_list = []
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        filter_box = StaticBoxSizer(
            self, wx.ID_ANY, _("Import Materials"), wx.HORIZONTAL
        )

        label_1 = wx.StaticText(self, wx.ID_ANY, _("Material"))
        filter_box.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_material = TextCtrl(self, wx.ID_ANY, "", limited=True)
        filter_box.Add(self.txt_material, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, _("Thickness"))
        filter_box.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_thickness = TextCtrl(self, wx.ID_ANY, "", limited=True)
        filter_box.Add(self.txt_thickness, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label_3 = wx.StaticText(self, wx.ID_ANY, _("Lasertype"))
        filter_box.Add(label_3, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.laser_choices = [
            _("<All Lasertypes>"),
        ]
        dev_infos = list(self.context.find("provider/friendly"))
        # Gets a list of tuples (description, key, path)
        # description is a tuple itself containing description and index
        dev_infos.sort(key=lambda e: e[0][1])
        for e in dev_infos:
            self.laser_choices.append(e[0][0])
        self.combo_lasertype = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.laser_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_lasertype.SetMaxSize(dip_size(self, 110, -1))
        filter_box.Add(self.combo_lasertype, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_reset = wx.Button(self, wx.ID_ANY, _("Reset Filter"))
        filter_box.Add(self.btn_reset, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_load = wx.Button(self, wx.ID_ANY, _("Load"))
        filter_box.Add(self.btn_load, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        main_sizer.Add(filter_box, 0, wx.EXPAND, 0)
        result_box = StaticBoxSizer(
            self, wx.ID_ANY, _("Matching library entries"), wx.VERTICAL
        )
        self.tree_library = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.tree_library.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.tree_library.AppendColumn(
            _("Material"),
            format=wx.LIST_FORMAT_LEFT,
            width=95,
        )
        self.tree_library.AppendColumn(
            _("Lasertype"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.tree_library.AppendColumn(
            _("Operations"), format=wx.LIST_FORMAT_LEFT, width=65
        )
        self.list_preview = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.list_preview.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_preview.AppendColumn(
            _("Operation"),
            format=wx.LIST_FORMAT_LEFT,
            width=95,
        )
        self.list_preview.AppendColumn(_("Id"), format=wx.LIST_FORMAT_LEFT, width=95)
        self.list_preview.AppendColumn(_("Label"), format=wx.LIST_FORMAT_LEFT, width=95)
        self.list_preview.AppendColumn(_("Power"), format=wx.LIST_FORMAT_LEFT, width=65)
        self.list_preview.AppendColumn(_("Speed"), format=wx.LIST_FORMAT_LEFT, width=65)

        result_box.Add(self.tree_library, 1, wx.EXPAND, 0)
        result_box.Add(self.list_preview, 1, wx.EXPAND, 0)
        self.btn_import = wx.Button(self, wx.ID_ANY, _("Import"))
        result_box.Add(self.btn_import, 0, wx.ALIGN_RIGHT, 0)

        main_sizer.Add(result_box, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.btn_load.Bind(wx.EVT_BUTTON, self.on_load)
        self.combo_lasertype.Bind(wx.EVT_COMBOBOX, self.update_list)
        self.txt_material.Bind(wx.EVT_TEXT, self.update_list)
        self.txt_thickness.Bind(wx.EVT_TEXT, self.update_list)
        self.tree_library.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection)
        ### TODO Look for locally cached entries...
        self.on_reset(None)
        self.enable_filter_controls()

    def on_import(self, event):
        idx = self.tree_library.GetFirstSelected()
        if idx >= 0:
            lib_idx = self.visible_list[idx]

    def on_reset(self, event):
        self.txt_material.SetValue("")
        self.txt_thickness.SetValue("")
        self.combo_lasertype.SetSelection(0)
        self.update_list()

    def enable_filter_controls(self):
        flag = len(self.library_entries) > 0
        self.txt_material.Enable(flag)
        self.txt_thickness.Enable(flag)
        self.combo_lasertype.Enable(flag)
        self.btn_reset.Enable(flag)

    def on_load(self, event):
        self.library_entries.clear()
        ### TODO: Load material database from internet

        self.enable_filter_controls()
        self.update_list()

    def update_list(self, *args):
        filter_txt = self.txt_material.GetValue()
        filter_thickness = self.txt_thickness.GetValue()
        filter_type = self.combo_lasertype.GetSelection()
        self.visible_list.clear()
        self.btn_import.Enable(False)
        self.tree_library.DeleteAllItems()
        for idx, entry in enumerate(self.library_entries):
            use_it = True
            if filter_txt and filter_txt not in entry[0]:
                use_it = False
            if filter_type > 0 and filter_type != entry[1]:
                use_it = False
            if use_it:
                try:
                    ltype = self.laser_choices[entry[1]]
                except IndexError:
                    # Invalid...
                    continue
                self.visible_list.append(idx)
                list_id = self.tree_library.InsertItem(idx, f"#{idx}")
                self.tree_library.SetItem(list_id, 1, entry[0])
                self.tree_library.SetItem(list_id, 2, ltype)
                self.tree_library.SetItem(list_id, 3, len(entry[2]))

        if len(self.visible_list):
            self.tree_library.Select(0)
        self.on_selection(None)

    def on_selection(self, event):
        self.btn_import.Enable(False)
        idx = self.tree_library.GetFirstSelected()
        self.list_preview.DeleteAllItems()
        if idx >= 0:
            self.btn_import.Enable(True)
            lib_idx = self.visible_list[idx]
            entry = self.library_entries[lib_idx]
            for idx, op in enumerate(entry[2]):
                list_id = self.list_preview.InsertItem(idx, f"#{idx}")
                self.list_preview.SetItem(list_id, 1, op.type)
                self.list_preview.SetItem(list_id, 2, op.label)
                if hasattr(op, "power"):
                    self.list_preview.SetItem(list_id, 3, op.power)
                if hasattr(op, "speed"):
                    self.list_preview.SetItem(list_id, 4, op.speed)

    def set_parent(self, par_panel):
        self.parent_panel = par_panel


class AboutPanel(wx.Panel):
    """
    Displays a how to summary
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        info_box = StaticBoxSizer(self, wx.ID_ANY, _("How to use..."), wx.VERTICAL)
        self.parent_panel = None
        s = self.context.asset("material_howto")
        info_label = wx.TextCtrl(
            self, wx.ID_ANY, value=s, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        info_label.SetFont(font)
        info_label.SetBackgroundColour(self.GetBackgroundColour())
        info_box.Add(info_label, 1, wx.EXPAND, 0)
        main_sizer.Add(info_box, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()

    def set_parent(self, par_panel):
        self.parent_panel = par_panel


class MaterialManager(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(860, 800, *args, **kwds)

        self.panel_library = MaterialPanel(self, wx.ID_ANY, context=self.context)
        # self.panel_import = ImportPanel(self, wx.ID_ANY, context=self.context)
        self.panel_about = AboutPanel(self, wx.ID_ANY, context=self.context)

        self.panel_library.set_parent(self)
        # self.panel_import.set_parent(self)
        self.panel_about.set_parent(self)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_library.GetBitmap())
        self.SetIcon(_icon)
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.notebook_main.AddPage(self.panel_library, _("Library"))
        # self.notebook_main.AddPage(self.panel_import, _("Import"))
        self.notebook_main.AddPage(self.panel_about, _("How to use"))
        # begin wxGlade: Keymap.__set_properties
        self.DragAcceptFiles(True)
        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)
        self.SetTitle(_("Material Library"))

    def on_drop_file(self, event):
        """
        Drop file handler
        Accepts only a single file drop.
        """
        for pathname in event.GetFiles():
            if self.panel_import.import_csv(pathname):
                break

    def delegates(self):
        yield self.panel_library
        yield self.panel_import
        yield self.panel_about

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/config/Material",
            {
                "label": _("Material Library"),
                "icon": icon_library,
                "tip": _("Manages Material Settings"),
                "help": "materialmanager",
                "action": lambda v: kernel.console("window toggle MatManager\n"),
            },
        )

    def window_open(self):
        pass

    def window_close(self):
        pass

    def edit_message(self, msg):
        self.panel_library.edit_message(msg)

    def populate_gui(self):
        self.panel_library.populate_gui()

    @staticmethod
    def submenu():
        # Suppress to avoid double menu-appearance
        return "", "Material Library", True
