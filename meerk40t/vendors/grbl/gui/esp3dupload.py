"""
ESP3D upload filename dialog for GRBL GUI toolbar.
"""
import wx

from ..esp3d_upload import (
    normalize_8_3_filename,
    suggest_esp3d_filename,
    validate_filename_8_3,
)

_ = wx.GetTranslation


def default_esp3d_filename_for_device(service):
    """Build default SD filename from project label and last upload."""
    project_label = None
    root = service.kernel.root
    gui = getattr(root, "gui", None)
    if gui and getattr(gui, "working_files", None):
        if len(gui.working_files) == 1:
            project_label = gui.working_files[0]
    last = getattr(service, "esp3d_last_filename", None)
    return suggest_esp3d_filename(project_label, last=last)


def prompt_esp3d_upload_filename(default_name):
    """
    Ask the user for an 8.3 SD filename.

    Returns the normalized filename, or None if cancelled / invalid.
    """
    message = _(
        "SD card filename (8.3 format).\n"
        "Use up to 8 characters before .gc — e.g. logo01.gc, cut001.gc.\n"
        "Same name overwrites the previous file on the card (easy rerun)."
    )
    with wx.TextEntryDialog(
        None,
        message,
        _("ESP3D upload filename"),
        default_name,
    ) as dlg:
        if dlg.ShowModal() != wx.ID_OK:
            return None
        raw = dlg.GetValue()
    normalized = normalize_8_3_filename(raw)
    if not normalized or not validate_filename_8_3(normalized):
        wx.MessageBox(
            _(
                "Invalid filename.\n\n"
                "Use up to 8 letters/numbers, then .gc\n"
                "(example: mycut01.gc)."
            ),
            _("ESP3D upload"),
            wx.OK | wx.ICON_WARNING,
        )
        return None
    return normalized


def run_esp3d_upload_with_prompt(service, execute=False):
    """Show filename dialog, then run esp3d_upload_run with -f."""
    default_name = default_esp3d_filename_for_device(service)
    filename = prompt_esp3d_upload_filename(default_name)
    if not filename:
        return
    cmd = f'esp3d_upload_run -f {filename}'
    if execute:
        cmd += " -e"
    service(f"{cmd}\n")
