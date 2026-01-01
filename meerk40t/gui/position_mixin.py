"""
Position/Dimension Mixin
Shared functionality for position and dimension editing panels.
"""

import wx


class PositionDimensionMixin:
    """
    Mixin providing common functionality for position/dimension panels.
    
    Provides:
    - 9-point reference grid icon generation
    - Offset position calculations
    - Reentry protection for update methods
    - Common position/dimension state management
    """

    # Class-level constants for the 9-point grid
    X_OFFSETS = (0, 0.5, 1, 0, 0.5, 1, 0, 0.5, 1)
    Y_OFFSETS = (0, 0, 0, 0.5, 0.5, 0.5, 1, 1, 1)

    def _init_position_state(self):
        """Initialize position/dimension state variables."""
        self.offset_index = 0  # 0 to 8: tl tc tr cl cc cr bl bc br
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_h = 0.0
        self.position_w = 0.0
        self.org_x = None
        self.org_y = None
        self.org_w = None
        self.org_h = None
        self._updating = False  # Reentry guard

    def calculate_position_icons(self, bmap_size):
        """
        Generate 9-point reference grid icons.
        
        Args:
            bmap_size: Size of the bitmap in pixels
            
        Returns:
            List of 9 wx.Bitmap objects representing the grid positions
        """
        result = []
        for y in range(3):
            for x in range(3):
                imgBit = wx.Bitmap(bmap_size, bmap_size)
                dc = wx.MemoryDC(imgBit)
                dc.SelectObject(imgBit)
                dc.SetBackground(wx.WHITE_BRUSH)
                dc.Clear()
                dc.SetPen(wx.BLACK_PEN)
                delta = (bmap_size - 1) / 3
                for xx in range(4):
                    dc.DrawLine(
                        int(delta * xx), 0, int(delta * xx), int(bmap_size - 1)
                    )
                    dc.DrawLine(
                        0, int(delta * xx), int(bmap_size - 1), int(delta * xx)
                    )
                # Fill the selected area
                dc.SetBrush(wx.BLACK_BRUSH)
                dc.DrawRectangle(
                    int(x * delta),
                    int(y * delta),
                    int(delta + 1),
                    int(delta + 1),
                )
                dc.SelectObject(wx.NullBitmap)
                result.append(imgBit)
        return result

    def set_reference_point(self, index):
        """
        Set the reference point for position/dimension operations.
        
        Args:
            index: Index 0-8 representing the 9-point grid position
        """
        if index < 0 or index > 8:
            index = 0
        self.offset_index = index
        self.offset_x = self.X_OFFSETS[index]
        self.offset_y = self.Y_OFFSETS[index]

    def handle_reference_click(self, event):
        """
        Handle click on reference point button.
        
        Args:
            event: wx.MouseEvent from button click
            
        Returns:
            The new offset index
        """
        pt_mouse = event.GetPosition()
        ob = event.GetEventObject()
        rect_ob = ob.GetRect()
        col = int(3 * pt_mouse[0] / rect_ob[2])
        row = int(3 * pt_mouse[1] / rect_ob[3])
        idx = 3 * row + col
        self.set_reference_point(idx)
        return self.offset_index

    def calculate_reference_position(self):
        """
        Calculate the position adjusted for the current reference point.
        
        Returns:
            Tuple of (pos_x, pos_y) adjusted for offset
        """
        pos_x = self.position_x + self.offset_x * self.position_w
        pos_y = self.position_y + self.offset_y * self.position_h
        return pos_x, pos_y

    def protected_update(self, update_func, *args, **kwargs):
        """
        Execute an update function with reentry protection.
        
        Args:
            update_func: Function to call with protection
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of update_func, or None if already updating
        """
        if self._updating:
            return None
        self._updating = True
        try:
            return update_func(*args, **kwargs)
        finally:
            self._updating = False
