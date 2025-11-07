"""
Cylinder modifier for coordinate transformation.

This module provides a CylinderModifier class that wraps a balor-device instance
to apply cylindrical coordinate transformations for laser engraving on
cylindrical surfaces.
"""

import math
from functools import lru_cache
from typing import Any, Tuple

BALOR_CENTER: int = 0X8000 # center of the balor coordinate system

class CylinderModifier:
    """
    A wrapper class that modifies coordinates for cylindrical surfaces.

    This class applies cylindrical projection transformations to coordinates
    before passing them to the wrapped device instance. It's designed for
    laser engraving systems that need to correct for cylindrical distortion.

    Attributes:
        _wrapped_instance (Any): The balor-device instance being wrapped
        service (Any): The service providing cylinder configuration
        mirror_distance (float): Mirror distance setting (currently unused)
        x_axis (float): X axis position (currently unused)
        y_axis (float): Y axis position (currently unused)
        x_axis_length (float): Cylinder X diameter
        y_axis_length (float): Cylinder Y diameter
        x_concave (bool): X concavity setting (currently unused)
        y_concave (bool): Y concavity setting (currently unused)
        r_x (float): Computed X radius for transformations
        r_y (float): Computed Y radius for transformations
        l_x (float): Last transformed X position
        l_y (float): Last transformed Y position
    """

    def __init__(self, wrapped_instance: Any, service: Any) -> None:
        """
        Initialize the CylinderModifier.

        Args:
            wrapped_instance: The device instance to wrap (e.g., laser driver)
            service: Service object providing cylinder configuration parameters
        """
        self._wrapped_instance = wrapped_instance
        self.service = service

        self.mirror_distance = service.cylinder_mirror_distance
        self.x_axis = service.cylinder_x_axis
        self.x_axis_length = service.cylinder_x_diameter
        self.x_concave = service.cylinder_x_concave

        self.y_axis = service.cylinder_y_axis
        self.y_axis_length = service.cylinder_y_diameter
        self.y_concave = service.cylinder_y_concave

        dx, dy = self.service.view.position(self.x_axis_length, 0, vector=True)
        self.r_x = abs(complex(dx, dy))
        dx, dy = self.service.view.position(0, self.y_axis_length, vector=True)
        self.r_y = abs(complex(dx, dy))
        self.l_x = BALOR_CENTER
        self.l_y = BALOR_CENTER

    @lru_cache(maxsize=1024)
    def convert(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert 2D coordinates for cylindrical projection.

        Applies cylindrical transformation: x' = r * sin((x - center) / r)
        This corrects for distortion when engraving on cylindrical surfaces.

        Args:
            x, y: Input coordinates (typically 0-65535 range)

        Returns:
            tuple: Transformed (x', y') coordinates
        """
        a = x - BALOR_CENTER
        r = self.r_x
        x_prime = a if r == 0 else r * math.sin(a / r)
        a = y - BALOR_CENTER
        r = self.r_y
        y_prime = a if r == 0 else r * math.sin(a / r)
        return x_prime + BALOR_CENTER, y_prime + BALOR_CENTER

    def mark(self, x: float, y: float, **kwargs) -> Any:
        """
        Mark a point with cylindrical coordinate transformation.

        Args:
            x, y: Coordinates to mark
            **kwargs: Additional arguments passed to wrapped instance

        Returns:
            Result from wrapped instance method
        """
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "mark")(x, y, **kwargs)

    def goto(self, x: float, y: float, **kwargs) -> Any:
        """
        Move to a point with cylindrical coordinate transformation.

        Args:
            x, y: Coordinates to move to
            **kwargs: Additional arguments passed to wrapped instance

        Returns:
            Result from wrapped instance method
        """
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "goto")(x, y, **kwargs)

    def light(self, x: float, y: float, **kwargs) -> Any:
        """
        Turn on laser at point with cylindrical coordinate transformation.

        Args:
            x, y: Coordinates for laser activation
            **kwargs: Additional arguments passed to wrapped instance

        Returns:
            Result from wrapped instance method
        """
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "light")(x, y, **kwargs)

    def dark(self, x: float, y: float, **kwargs) -> Any:
        """
        Turn off laser at point with cylindrical coordinate transformation.

        Args:
            x, y: Coordinates for laser deactivation
            **kwargs: Additional arguments passed to wrapped instance

        Returns:
            Result from wrapped instance method
        """
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "dark")(x, y, **kwargs)

    def set_xy(self, x: float, y: float, **kwargs) -> Any:
        """
        Set current position with cylindrical coordinate transformation.

        Args:
            x, y: Coordinates to set as current position
            **kwargs: Additional arguments passed to wrapped instance

        Returns:
            Result from wrapped instance method
        """
        x, y = self.convert(x, y)
        self.l_x, self.l_y = x, y
        return getattr(self._wrapped_instance, "set_xy")(x, y, **kwargs)

    def get_last_xy(self, **kwargs) -> Tuple[float, float]:
        """
        Get the last transformed position.

        Returns:
            tuple: Last (x, y) coordinates after transformation
        """
        return self.l_x, self.l_y

    def __getattr__(self, attr: str) -> Any:
        """
        Delegate attribute access to wrapped instance.

        Args:
            attr: Attribute name

        Returns:
            Attribute from wrapped instance
        """
        return getattr(self._wrapped_instance, attr)
