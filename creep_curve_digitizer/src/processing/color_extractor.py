"""
Color-based curve extraction for Mode A (Multi-color graphs).
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple


class ColorExtractor:
    """
    Extracts curves based on color selection.
    Used for Mode A (Multi-color graphs).
    """

    def __init__(self, tolerance: int = 15):
        """
        Initialize the color extractor.

        Args:
            tolerance: HSV tolerance for color matching
        """
        self.tolerance = tolerance
        self.extracted_curves = []

    def extract_by_color(
        self,
        image: np.ndarray,
        target_color: Tuple[int, int, int],
        roi: List[int] = None
    ) -> List[Dict]:
        """
        Extract curve points based on a target color.

        Args:
            image: Input BGR image
            target_color: Target BGR color (B, G, R)
            roi: Optional ROI [x1, y1, x2, y2]

        Returns:
            List of point dictionaries with coordinates
        """
        if roi:
            x1, y1, x2, y2 = roi
            img_region = image[y1:y2, x1:x2]
        else:
            img_region = image
            x1, y1 = 0, 0

        # Create color mask
        mask = self._create_color_mask(img_region, target_color)

        # Apply skeletonization to get center line
        skeleton = self._skeletonize(mask)

        # Extract point coordinates from skeleton
        points = self._extract_skeleton_points(skeleton, x1, y1)

        # Sort by x-coordinate
        points = sorted(points, key=lambda p: p['cx'])

        return points

    def _create_color_mask(
        self,
        image: np.ndarray,
        target_color: Tuple[int, int, int]
    ) -> np.ndarray:
        """
        Create a binary mask for the target color.

        Args:
            image: Input BGR image
            target_color: Target BGR color

        Returns:
            Binary mask
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Convert target color to HSV
        target_bgr = np.uint8([[target_color]])
        target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]

        h, s, v = target_hsv

        # Create range with tolerance
        lower = np.array([
            max(0, h - self.tolerance),
            max(0, s - 50),
            max(0, v - 50)
        ])
        upper = np.array([
            min(179, h + self.tolerance),
            min(255, s + 50),
            min(255, v + 50)
        ])

        # Handle hue wraparound for red
        if h < self.tolerance:
            mask1 = cv2.inRange(hsv, np.array([0, lower[1], lower[2]]), upper)
            mask2 = cv2.inRange(
                hsv,
                np.array([179 - (self.tolerance - h), lower[1], lower[2]]),
                np.array([179, upper[1], upper[2]])
            )
            mask = cv2.bitwise_or(mask1, mask2)
        elif h > 179 - self.tolerance:
            mask1 = cv2.inRange(hsv, lower, np.array([179, upper[1], upper[2]]))
            mask2 = cv2.inRange(
                hsv,
                np.array([0, lower[1], lower[2]]),
                np.array([self.tolerance - (179 - h), upper[1], upper[2]])
            )
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = cv2.inRange(hsv, lower, upper)

        # Clean up mask
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        return mask

    def _skeletonize(self, mask: np.ndarray) -> np.ndarray:
        """
        Apply skeletonization to get 1-pixel wide lines.

        Args:
            mask: Binary mask

        Returns:
            Skeleton image
        """
        from skimage.morphology import skeletonize

        # Normalize to 0-1
        binary = (mask > 0).astype(np.uint8)

        # Skeletonize
        skeleton = skeletonize(binary)

        return (skeleton * 255).astype(np.uint8)

    def _extract_skeleton_points(
        self,
        skeleton: np.ndarray,
        x_offset: int = 0,
        y_offset: int = 0
    ) -> List[Dict]:
        """
        Extract point coordinates from skeleton.

        For each unique x-coordinate, take the mean y-coordinate
        of all skeleton pixels at that x.

        Args:
            skeleton: Skeleton image
            x_offset: X offset to add (if ROI was used)
            y_offset: Y offset to add (if ROI was used)

        Returns:
            List of point dictionaries
        """
        # Get all skeleton pixel coordinates
        y_coords, x_coords = np.where(skeleton > 0)

        if len(x_coords) == 0:
            return []

        # Group by x and average y
        points = []
        unique_x = np.unique(x_coords)

        for x in unique_x:
            y_at_x = y_coords[x_coords == x]
            mean_y = np.mean(y_at_x)

            points.append({
                'cx': float(x + x_offset),
                'cy': float(mean_y + y_offset),
                'area': 0,
                'circularity': 0,
                'solidity': 0,
                'color_based': True
            })

        return points

    def get_dominant_colors(
        self,
        image: np.ndarray,
        n_colors: int = 5,
        roi: List[int] = None
    ) -> List[Tuple[int, int, int]]:
        """
        Get dominant colors in the image for user reference.

        Args:
            image: Input BGR image
            n_colors: Number of colors to return
            roi: Optional ROI

        Returns:
            List of BGR color tuples
        """
        if roi:
            x1, y1, x2, y2 = roi
            img_region = image[y1:y2, x1:x2]
        else:
            img_region = image

        # Reshape for k-means
        pixels = img_region.reshape(-1, 3).astype(np.float32)

        # Apply k-means
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )

        # Convert to int tuples
        colors = [tuple(map(int, c)) for c in centers]

        return colors
