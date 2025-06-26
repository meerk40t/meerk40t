"""
Fast Vectorizer Integration for MeerK40t
=======================================

Integration module that adds the fast vectorizer as an alternative to potrace
in the image vectorization panel.
"""

import time

import numpy as np
import wx
from PIL import Image

# Pillow resampling constants (using numeric values for compatibility)
RESAMPLE_LANCZOS = 1  # Image.LANCZOS
RESAMPLE_NEAREST = 0  # Image.NEAREST

try:
    from .fast_vectorize_optimized import (
        HAS_NUMBA,
        TURNPOLICY_BLACK,
        TURNPOLICY_LEFT,
        TURNPOLICY_MAJORITY,
        TURNPOLICY_MINORITY,
        TURNPOLICY_RANDOM,
        TURNPOLICY_RIGHT,
        TURNPOLICY_WHITE,
        FastVectorizer,
    )

    FAST_VECTORIZER_AVAILABLE = True
except ImportError:
    # Fallback to original implementation
    try:
        from .fast_vectorize import (
            HAS_NUMBA,
            TURNPOLICY_BLACK,
            TURNPOLICY_LEFT,
            TURNPOLICY_MAJORITY,
            TURNPOLICY_MINORITY,
            TURNPOLICY_RANDOM,
            TURNPOLICY_RIGHT,
            TURNPOLICY_WHITE,
            FastVectorizer,
        )

        FAST_VECTORIZER_AVAILABLE = True
    except ImportError:
        FAST_VECTORIZER_AVAILABLE = False
        HAS_NUMBA = False


class FastVectorizationPanel(wx.Panel):
    """
    Fast vectorization panel using the pure NumPy/Numba implementation.
    """

    def __init__(self, parent, context=None, node=None):
        super().__init__(parent)
        self.context = context
        self.node = node
        self._pane_is_active = False

        if not FAST_VECTORIZER_AVAILABLE:
            self._create_unavailable_ui()
            return

        self.vectorizer = FastVectorizer()
        self._create_ui()
        self._bind_events()

    def _create_unavailable_ui(self):
        """Create UI when fast vectorizer is not available."""
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="Fast vectorizer not available")
        sizer.Add(label, 0, wx.ALL, 10)
        self.SetSizer(sizer)

    def _create_ui(self):
        """Create the user interface."""
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Options panel
        options_sizer = wx.StaticBoxSizer(
            wx.VERTICAL, self, "Fast Vectorization Options"
        )

        # Turn policy
        turn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        turn_label = wx.StaticText(self, label="Turn Policy:")
        turn_label.SetMinSize((80, -1))
        turn_sizer.Add(turn_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.turn_choices = [
            "Black",
            "White",
            "Left",
            "Right",
            "Minority",
            "Majority",
            "Random",
        ]
        self.combo_turnpolicy = wx.ComboBox(
            self, choices=self.turn_choices, style=wx.CB_READONLY
        )
        self.combo_turnpolicy.SetSelection(4)  # Minority
        turn_sizer.Add(self.combo_turnpolicy, 1, wx.EXPAND | wx.LEFT, 5)
        options_sizer.Add(turn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Threshold
        threshold_sizer = wx.BoxSizer(wx.HORIZONTAL)
        threshold_label = wx.StaticText(self, label="Threshold:")
        threshold_label.SetMinSize((80, -1))
        threshold_sizer.Add(threshold_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.slider_threshold = wx.Slider(self, value=50, minValue=0, maxValue=100)
        self.slider_threshold.SetToolTip(
            "Brightness threshold for black/white conversion"
        )
        threshold_sizer.Add(self.slider_threshold, 1, wx.EXPAND | wx.LEFT, 5)
        options_sizer.Add(threshold_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Tolerance
        tolerance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        tolerance_label = wx.StaticText(self, label="Simplify:")
        tolerance_label.SetMinSize((80, -1))
        tolerance_sizer.Add(tolerance_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.slider_tolerance = wx.Slider(self, value=10, minValue=0, maxValue=50)
        self.slider_tolerance.SetToolTip("Polygon simplification tolerance")
        tolerance_sizer.Add(self.slider_tolerance, 1, wx.EXPAND | wx.LEFT, 5)
        options_sizer.Add(tolerance_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Min area
        minarea_sizer = wx.BoxSizer(wx.HORIZONTAL)
        minarea_label = wx.StaticText(self, label="Min Area:")
        minarea_label.SetMinSize((80, -1))
        minarea_sizer.Add(minarea_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.slider_minarea = wx.Slider(self, value=4, minValue=0, maxValue=50)
        self.slider_minarea.SetToolTip("Minimum contour area (despeckle)")
        minarea_sizer.Add(self.slider_minarea, 1, wx.EXPAND | wx.LEFT, 5)
        options_sizer.Add(minarea_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Status
        self.status_label = wx.StaticText(
            self, label=f"Numba: {'Available' if HAS_NUMBA else 'Not Available'}"
        )
        options_sizer.Add(self.status_label, 0, wx.ALL, 5)

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.button_preview = wx.Button(self, label="Preview")
        self.button_preview.SetToolTip("Generate preview of vectorization")
        button_sizer.Add(self.button_preview, 0, wx.ALL, 5)

        self.button_vectorize = wx.Button(self, label="Vectorize")
        self.button_vectorize.SetToolTip("Create vector paths from image")
        button_sizer.Add(self.button_vectorize, 0, wx.ALL, 5)

        options_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

        main_sizer.Add(options_sizer, 1, wx.EXPAND | wx.ALL, 5)

        # Preview panel
        preview_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, "Preview")

        self.bitmap_preview = wx.StaticBitmap(self, size=(300, 300))
        preview_sizer.Add(self.bitmap_preview, 1, wx.EXPAND | wx.ALL, 5)

        self.info_label = wx.StaticText(self, label="Ready")
        preview_sizer.Add(self.info_label, 0, wx.ALL, 5)

        main_sizer.Add(preview_sizer, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(main_sizer)

    def _bind_events(self):
        """Bind UI events."""
        self.button_preview.Bind(wx.EVT_BUTTON, self.on_preview)
        self.button_vectorize.Bind(wx.EVT_BUTTON, self.on_vectorize)

        # Auto-preview on slider changes
        self.slider_threshold.Bind(wx.EVT_SLIDER, self.on_slider_change)
        self.slider_tolerance.Bind(wx.EVT_SLIDER, self.on_slider_change)
        self.slider_minarea.Bind(wx.EVT_SLIDER, self.on_slider_change)
        self.combo_turnpolicy.Bind(wx.EVT_COMBOBOX, self.on_slider_change)

    def on_slider_change(self, event):
        """Handle slider/combo changes."""
        if hasattr(self, "_auto_preview_timer"):
            self._auto_preview_timer.Stop()

        # Delay preview update to avoid too many updates while dragging
        self._auto_preview_timer = wx.CallLater(500, self.on_preview)

    def _get_parameters(self):
        """Get current vectorization parameters."""
        turn_policy = self.combo_turnpolicy.GetSelection()
        threshold = self.slider_threshold.GetValue() / 100.0
        tolerance = self.slider_tolerance.GetValue() / 10.0
        min_area = float(self.slider_minarea.GetValue())

        return turn_policy, threshold, tolerance, min_area

    def _prepare_image(self, for_preview=False, max_preview_size=500):
        """Prepare image for vectorization.

        Args:
            for_preview: If True, downscale image for faster preview generation
            max_preview_size: Maximum dimension for preview images
        """
        if self.node is None or not hasattr(self.node, "active_image"):
            return None

        # Get the processed image
        pil_image = self.node.active_image
        if pil_image is None:
            return None

        # Convert to numpy array
        if pil_image.mode == "RGBA":
            # Handle transparency by compositing on white background
            background = Image.new("RGB", pil_image.size, (255, 255, 255))
            background.paste(pil_image, mask=pil_image.split()[-1])
            pil_image = background
        elif pil_image.mode == "P":
            pil_image = pil_image.convert("RGB")

        # For preview, downscale to reasonable size for speed
        if for_preview:
            w, h = pil_image.size
            if max(w, h) > max_preview_size:
                scale = max_preview_size / max(w, h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                # Use a compatible resize method
                pil_image = pil_image.resize((new_w, new_h), RESAMPLE_NEAREST)

        return np.array(pil_image)

    def on_preview(self, event=None):
        """Generate preview using downscaled image for speed."""
        if not FAST_VECTORIZER_AVAILABLE:
            return

        # Use downscaled image for preview
        image_array = self._prepare_image(for_preview=True, max_preview_size=500)
        if image_array is None:
            self.info_label.SetLabel("No image available")
            return

        # Get parameters
        turn_policy, threshold, tolerance, min_area = self._get_parameters()

        # Update vectorizer parameters
        self.vectorizer.set_parameters(
            turn_policy=turn_policy,
            threshold=threshold,
            tolerance=tolerance,
            min_area=min_area,
        )

        try:
            # Time the operation
            start_time = time.perf_counter()

            # Vectorize using downscaled image
            svg_path, contours = self.vectorizer.vectorize(image_array)

            end_time = time.perf_counter()
            duration = end_time - start_time

            # Update info with size information
            original_img = self._prepare_image(for_preview=False)
            if original_img is not None:
                orig_pixels = original_img.shape[0] * original_img.shape[1]
                preview_pixels = image_array.shape[0] * image_array.shape[1]
                scale_factor = orig_pixels / preview_pixels
                info_text = f"Found {len(contours)} contours in {duration:.3f}s"
                if scale_factor > 1.1:  # Only show if significantly downscaled
                    info_text += f" (preview {scale_factor:.1f}x smaller)"
                if HAS_NUMBA:
                    info_text += " (Numba)"
                self.info_label.SetLabel(info_text)
            else:
                info_text = (
                    f"Found {len(contours)} contours in {duration:.3f}s (preview)"
                )
                if HAS_NUMBA:
                    info_text += " (Numba)"
                self.info_label.SetLabel(info_text)

            # Create preview image
            self._create_preview_image(contours, image_array.shape[:2])

        except Exception as e:
            self.info_label.SetLabel(f"Error: {str(e)}")

    def _create_preview_image(self, contours, original_shape):
        """Create a preview image showing the contours."""
        if not contours:
            return

        # Create a white background
        h, w = original_shape
        preview_img = np.ones((h, w, 3), dtype=np.uint8) * 255

        # Draw contours in black
        for x_coords, y_coords in contours:
            for i in range(len(x_coords) - 1):
                x1, y1 = int(x_coords[i]), int(y_coords[i])
                x2, y2 = int(x_coords[i + 1]), int(y_coords[i + 1])

                # Simple line drawing (Bresenham's line algorithm would be better)
                if 0 <= x1 < w and 0 <= y1 < h:
                    preview_img[y1, x1] = [0, 0, 0]
                if 0 <= x2 < w and 0 <= y2 < h:
                    preview_img[y2, x2] = [0, 0, 0]

        # Convert to PIL and then to wxPython bitmap
        pil_img = Image.fromarray(preview_img)

        # Resize to fit preview area
        preview_size = self.bitmap_preview.GetSize()
        if preview_size.width > 0 and preview_size.height > 0:
            pil_img = pil_img.resize(
                (preview_size.width, preview_size.height), RESAMPLE_LANCZOS
            )

        # Convert to wx.Bitmap
        wx_img = wx.Image(pil_img.size[0], pil_img.size[1], pil_img.tobytes())
        bitmap = wx.Bitmap(wx_img)
        self.bitmap_preview.SetBitmap(bitmap)

    def on_vectorize(self, event):
        """Perform vectorization and create paths."""
        if not FAST_VECTORIZER_AVAILABLE:
            return

        # Use full-resolution image for final vectorization (not preview)
        image_array = self._prepare_image(for_preview=False)
        if image_array is None:
            wx.MessageBox(
                "No image available for vectorization", "Error", wx.OK | wx.ICON_ERROR
            )
            return

        # Get parameters
        turn_policy, threshold, tolerance, min_area = self._get_parameters()

        # Update vectorizer parameters
        self.vectorizer.set_parameters(
            turn_policy=turn_policy,
            threshold=threshold,
            tolerance=tolerance,
            min_area=min_area,
        )

        try:
            # Show busy cursor
            wx.BeginBusyCursor()

            # Vectorize
            start_time = time.perf_counter()
            svg_path, contours = self.vectorizer.vectorize(image_array)
            end_time = time.perf_counter()

            # Create command to add paths to MeerK40t
            if contours:
                # Build command to create path elements
                # This would need to be adapted to MeerK40t's specific path creation syntax
                commands = []
                for i, (x_coords, y_coords) in enumerate(contours):
                    if len(x_coords) >= 3:
                        # Create path command
                        path_data = f"M {x_coords[0]},{y_coords[0]}"
                        for j in range(1, len(x_coords)):
                            path_data += f" L {x_coords[j]},{y_coords[j]}"
                        path_data += " Z"

                        commands.append(f'path "{path_data}"')

                # Execute commands
                if self.context:
                    for cmd in commands:
                        self.context(cmd)

                # Show result
                duration = end_time - start_time
                wx.MessageBox(
                    f"Created {len(contours)} paths in {duration:.3f} seconds",
                    "Vectorization Complete",
                    wx.OK | wx.ICON_INFORMATION,
                )
            else:
                wx.MessageBox(
                    "No contours found", "Vectorization Result", wx.OK | wx.ICON_WARNING
                )

        except Exception as e:
            wx.MessageBox(
                f"Vectorization failed: {str(e)}", "Error", wx.OK | wx.ICON_ERROR
            )
        finally:
            wx.EndBusyCursor()

    def set_widgets(self, node):
        """Update the panel for a new node."""
        self.node = node
        if FAST_VECTORIZER_AVAILABLE:
            self.on_preview()

    def pane_active(self):
        """Called when the pane becomes active."""
        self._pane_is_active = True
        if FAST_VECTORIZER_AVAILABLE:
            self.on_preview()

    def pane_deactive(self):
        """Called when the pane becomes inactive."""
        self._pane_is_active = False

    @staticmethod
    def accepts(node):
        """Check if this panel can handle the given node."""
        return hasattr(node, "as_image") and FAST_VECTORIZER_AVAILABLE


def add_fast_vectorizer_to_meerk40t(context):
    """
    Function to register the fast vectorizer panel with MeerK40t.
    This should be called during plugin initialization.
    """
    try:
        # Register the panel with the property panel system
        # This would need to be adapted to MeerK40t's specific registration system
        context.register("property_panel", FastVectorizationPanel)
        return True
    except Exception as e:
        print(f"Failed to register fast vectorizer: {e}")
        return False
