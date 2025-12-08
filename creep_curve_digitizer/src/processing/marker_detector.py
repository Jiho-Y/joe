"""
Marker detection for Mode B3 (Line + Marker).
"""

import cv2
import numpy as np
from typing import List, Dict, Optional


class MarkerDetector:
    """
    Detects markers in graphs after line removal.
    """

    def __init__(
        self,
        min_area: int = 30,
        max_area: int = 500,
        kernel_size: int = 5
    ):
        """
        Initialize the marker detector.

        Args:
            min_area: Minimum contour area to consider as marker
            max_area: Maximum contour area to consider as marker
            kernel_size: Kernel size for morphological operations
        """
        self.min_area = min_area
        self.max_area = max_area
        self.kernel_size = kernel_size

    def detect(
        self,
        binary: np.ndarray,
        original: Optional[np.ndarray] = None
    ) -> List[Dict]:
        """
        Detect markers in the binary image.

        Args:
            binary: Binary image (from preprocessing)
            original: Original color image (for color analysis, optional)

        Returns:
            List of marker dictionaries with shape features
        """
        # Remove lines using morphological opening
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.kernel_size, self.kernel_size)
        )
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(
            opened,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        markers = []
        for contour in contours:
            # Calculate area
            area = cv2.contourArea(contour)

            # Filter by area
            if area < self.min_area or area > self.max_area:
                continue

            # Extract shape features
            features = self._extract_features(contour)
            if features:
                markers.append(features)

        return markers

    def _extract_features(self, contour: np.ndarray) -> Optional[Dict]:
        """
        Extract shape features from a contour.

        Args:
            contour: OpenCV contour

        Returns:
            Dictionary with shape features or None if invalid
        """
        # Calculate moments
        moments = cv2.moments(contour)
        if moments['m00'] == 0:
            return None

        # Centroid
        cx = moments['m10'] / moments['m00']
        cy = moments['m01'] / moments['m00']

        # Area
        area = cv2.contourArea(contour)

        # Perimeter
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return None

        # Circularity: 4 * pi * Area / Perimeter^2
        # Perfect circle = 1.0
        circularity = 4 * np.pi * area / (perimeter ** 2)

        # Convex hull and solidity
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area == 0:
            return None
        solidity = area / hull_area

        # Hu moments (rotation-invariant shape descriptors)
        hu_moments = cv2.HuMoments(moments).flatten()

        # Bounding box
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w) / h if h > 0 else 1.0

        # Extent: object area / bounding box area
        rect_area = w * h
        extent = area / rect_area if rect_area > 0 else 0

        return {
            'cx': float(cx),
            'cy': float(cy),
            'area': float(area),
            'perimeter': float(perimeter),
            'circularity': float(circularity),
            'solidity': float(solidity),
            'aspect_ratio': float(aspect_ratio),
            'extent': float(extent),
            'hu_moments': hu_moments.tolist(),
            'contour': contour,
            'bbox': (x, y, w, h)
        }

    def filter_by_shape(
        self,
        markers: List[Dict],
        min_circularity: float = 0.0,
        max_circularity: float = 1.0,
        min_solidity: float = 0.0,
        max_solidity: float = 1.0
    ) -> List[Dict]:
        """
        Filter markers by shape criteria.

        Args:
            markers: List of marker dictionaries
            min_circularity: Minimum circularity threshold
            max_circularity: Maximum circularity threshold
            min_solidity: Minimum solidity threshold
            max_solidity: Maximum solidity threshold

        Returns:
            Filtered list of markers
        """
        filtered = []
        for marker in markers:
            circ = marker['circularity']
            sol = marker['solidity']

            if (min_circularity <= circ <= max_circularity and
                    min_solidity <= sol <= max_solidity):
                filtered.append(marker)

        return filtered

    @staticmethod
    def sort_by_x(markers: List[Dict]) -> List[Dict]:
        """Sort markers by x-coordinate (centroid)."""
        return sorted(markers, key=lambda m: m['cx'])

    @staticmethod
    def sort_by_y(markers: List[Dict]) -> List[Dict]:
        """Sort markers by y-coordinate (centroid)."""
        return sorted(markers, key=lambda m: m['cy'])
