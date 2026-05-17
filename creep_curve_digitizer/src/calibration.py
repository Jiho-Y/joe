"""
Coordinate calibration and transformation.
"""

import numpy as np
from typing import Tuple, Optional


class Calibration:
    """
    Handles pixel-to-real coordinate transformation for both axes.
    Supports linear and logarithmic scales.
    """

    def __init__(self):
        """Initialize calibration with default (uncalibrated) state."""
        self._x_pixels = None
        self._x_values = None
        self._x_scale = 'linear'

        self._y_pixels = None
        self._y_values = None
        self._y_scale = 'linear'

    def set_x_calibration(
        self,
        pixels: list,
        values: list,
        scale: str = 'linear'
    ):
        """
        Set X-axis calibration.

        Args:
            pixels: List of two pixel x-coordinates
            values: List of two corresponding real values
            scale: 'linear' or 'logarithmic'
        """
        self._x_pixels = pixels
        self._x_values = values
        self._x_scale = scale

    def set_y_calibration(
        self,
        pixels: list,
        values: list,
        scale: str = 'linear'
    ):
        """
        Set Y-axis calibration.

        Args:
            pixels: List of two pixel y-coordinates
            values: List of two corresponding real values
            scale: 'linear' or 'logarithmic'
        """
        self._y_pixels = pixels
        self._y_values = values
        self._y_scale = scale

    def is_calibrated(self) -> bool:
        """Check if both axes are calibrated."""
        return (
            self._x_pixels is not None and
            self._y_pixels is not None
        )

    def is_x_calibrated(self) -> bool:
        """Check if X-axis is calibrated."""
        return self._x_pixels is not None

    def is_y_calibrated(self) -> bool:
        """Check if Y-axis is calibrated."""
        return self._y_pixels is not None

    def pixel_to_real(
        self,
        px: float,
        py: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Convert pixel coordinates to real coordinates.

        Args:
            px: Pixel x-coordinate
            py: Pixel y-coordinate

        Returns:
            Tuple of (real_x, real_y), with None for uncalibrated axes
        """
        real_x = self._transform_x(px) if self.is_x_calibrated() else None
        real_y = self._transform_y(py) if self.is_y_calibrated() else None
        return real_x, real_y

    def _transform_x(self, px: float) -> float:
        """Transform pixel x to real x value."""
        return self._transform(
            px,
            self._x_pixels,
            self._x_values,
            self._x_scale
        )

    def _transform_y(self, py: float) -> float:
        """Transform pixel y to real y value."""
        return self._transform(
            py,
            self._y_pixels,
            self._y_values,
            self._y_scale
        )

    def _transform(
        self,
        pixel: float,
        pixels: list,
        values: list,
        scale: str
    ) -> float:
        """
        Apply transformation for one axis.

        Args:
            pixel: Input pixel coordinate
            pixels: Two reference pixel coordinates
            values: Two reference real values
            scale: 'linear' or 'logarithmic'

        Returns:
            Transformed real value
        """
        p1, p2 = pixels
        v1, v2 = values

        if scale == 'logarithmic':
            # Log transformation
            if v1 <= 0 or v2 <= 0:
                # Fall back to linear if values are non-positive
                return self._linear_transform(pixel, p1, p2, v1, v2)

            log_v1 = np.log10(v1)
            log_v2 = np.log10(v2)

            # Linear interpolation in log space
            t = (pixel - p1) / (p2 - p1) if p2 != p1 else 0
            log_result = log_v1 + t * (log_v2 - log_v1)

            return 10 ** log_result
        else:
            return self._linear_transform(pixel, p1, p2, v1, v2)

    @staticmethod
    def _linear_transform(
        pixel: float,
        p1: float,
        p2: float,
        v1: float,
        v2: float
    ) -> float:
        """Apply linear transformation."""
        if p2 == p1:
            return v1

        # Linear interpolation
        t = (pixel - p1) / (p2 - p1)
        return v1 + t * (v2 - v1)

    def real_to_pixel(
        self,
        rx: float,
        ry: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Convert real coordinates to pixel coordinates (inverse transform).

        Args:
            rx: Real x value
            ry: Real y value

        Returns:
            Tuple of (pixel_x, pixel_y), with None for uncalibrated axes
        """
        px = self._inverse_transform_x(rx) if self.is_x_calibrated() else None
        py = self._inverse_transform_y(ry) if self.is_y_calibrated() else None
        return px, py

    def _inverse_transform_x(self, rx: float) -> float:
        """Transform real x to pixel x."""
        return self._inverse_transform(
            rx,
            self._x_pixels,
            self._x_values,
            self._x_scale
        )

    def _inverse_transform_y(self, ry: float) -> float:
        """Transform real y to pixel y."""
        return self._inverse_transform(
            ry,
            self._y_pixels,
            self._y_values,
            self._y_scale
        )

    def _inverse_transform(
        self,
        value: float,
        pixels: list,
        values: list,
        scale: str
    ) -> float:
        """Apply inverse transformation."""
        p1, p2 = pixels
        v1, v2 = values

        if scale == 'logarithmic':
            if v1 <= 0 or v2 <= 0 or value <= 0:
                return self._linear_inverse(value, p1, p2, v1, v2)

            log_v1 = np.log10(v1)
            log_v2 = np.log10(v2)
            log_value = np.log10(value)

            if log_v2 == log_v1:
                return p1

            t = (log_value - log_v1) / (log_v2 - log_v1)
            return p1 + t * (p2 - p1)
        else:
            return self._linear_inverse(value, p1, p2, v1, v2)

    @staticmethod
    def _linear_inverse(
        value: float,
        p1: float,
        p2: float,
        v1: float,
        v2: float
    ) -> float:
        """Apply inverse linear transformation."""
        if v2 == v1:
            return p1

        t = (value - v1) / (v2 - v1)
        return p1 + t * (p2 - p1)

    def to_dict(self) -> dict:
        """Serialize calibration to dictionary."""
        data = {}
        if self.is_x_calibrated():
            data['x_calib'] = {
                'pixel': self._x_pixels,
                'value': self._x_values,
                'scale': self._x_scale
            }
        if self.is_y_calibrated():
            data['y_calib'] = {
                'pixel': self._y_pixels,
                'value': self._y_values,
                'scale': self._y_scale
            }
        return data

    def from_dict(self, data: dict):
        """Load calibration from dictionary."""
        if 'x_calib' in data:
            self.set_x_calibration(
                data['x_calib']['pixel'],
                data['x_calib']['value'],
                data['x_calib'].get('scale', 'linear')
            )
        if 'y_calib' in data:
            self.set_y_calibration(
                data['y_calib']['pixel'],
                data['y_calib']['value'],
                data['y_calib'].get('scale', 'linear')
            )

    def clear(self):
        """Clear all calibration data."""
        self._x_pixels = None
        self._x_values = None
        self._x_scale = 'linear'
        self._y_pixels = None
        self._y_values = None
        self._y_scale = 'linear'
