"""
Marker detection for Mode B3 (Line + Marker).
"""

import cv2
import numpy as np
from typing import List, Dict, Optional
from skimage.morphology import skeletonize


class MarkerDetector:
    """
    Detects markers in graphs after line removal.
    Handles cases where lines overlap with markers.
    """

    def __init__(
        self,
        min_area: int = 30,
        max_area: int = 500,
        kernel_size: int = 5,
        use_skeleton_removal: bool = True
    ):
        """
        Initialize the marker detector.

        Args:
            min_area: Minimum contour area to consider as marker
            max_area: Maximum contour area to consider as marker
            kernel_size: Kernel size for morphological operations
            use_skeleton_removal: Use skeleton-based line removal (better for overlapping)
        """
        self.min_area = min_area
        self.max_area = max_area
        self.kernel_size = kernel_size
        self.use_skeleton_removal = use_skeleton_removal

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
        if self.use_skeleton_removal:
            # Method 1: Skeleton-based line removal (better for line+marker overlap)
            marker_mask = self._remove_lines_skeleton(binary)
        else:
            # Method 2: Traditional morphological opening
            marker_mask = self._remove_lines_morphology(binary)

        # Find contours
        contours, _ = cv2.findContours(
            marker_mask,
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

            # Extract shape features using convex hull for normalization
            features = self._extract_features(contour, use_hull_normalization=True)
            if features:
                markers.append(features)

        return markers

    def _remove_lines_skeleton(self, binary: np.ndarray) -> np.ndarray:
        """
        Remove lines using skeleton-based approach.
        This method better handles markers that overlap with lines.

        Steps:
        1. Extract skeleton (1-pixel wide lines)
        2. Dilate skeleton to create line mask
        3. Find regions that are NOT part of lines (markers)
        4. Clean up with morphological operations
        """
        # Normalize binary image
        binary_norm = (binary > 0).astype(np.uint8)

        # Extract skeleton
        skeleton = skeletonize(binary_norm).astype(np.uint8) * 255

        # Dilate skeleton to cover line width
        line_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        line_mask = cv2.dilate(skeleton, line_kernel, iterations=2)

        # Find blob regions (potential markers) using distance from skeleton
        # Markers have larger distance from skeleton than line pixels
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

        # Threshold distance - pixels far from skeleton are likely markers
        # Adaptive threshold based on average distance
        mean_dist = np.mean(dist_transform[binary > 0])
        marker_threshold = max(3, mean_dist * 0.8)

        # Initial marker candidates
        marker_candidates = (dist_transform > marker_threshold).astype(np.uint8) * 255

        # Dilate to recover marker shape
        marker_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.kernel_size, self.kernel_size)
        )
        marker_mask = cv2.dilate(marker_candidates, marker_kernel, iterations=1)

        # Intersect with original binary to limit to actual pixels
        marker_mask = cv2.bitwise_and(marker_mask, binary)

        # Clean up small noise
        marker_mask = cv2.morphologyEx(
            marker_mask, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        )

        return marker_mask

    def _remove_lines_morphology(self, binary: np.ndarray) -> np.ndarray:
        """
        Remove lines using traditional morphological opening.
        """
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.kernel_size, self.kernel_size)
        )
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        return opened

    def _remove_lines_directional(self, binary: np.ndarray) -> np.ndarray:
        """
        Remove lines using directional morphological operations.
        Removes both horizontal and vertical/diagonal lines.
        """
        result = binary.copy()

        # Remove horizontal lines
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        result = cv2.subtract(result, h_lines)

        # Remove vertical lines
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
        result = cv2.subtract(result, v_lines)

        # Remove diagonal lines (45 degrees)
        d1_kernel = np.eye(15, dtype=np.uint8)
        d1_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, d1_kernel)
        result = cv2.subtract(result, d1_lines)

        # Remove diagonal lines (-45 degrees)
        d2_kernel = np.fliplr(np.eye(15, dtype=np.uint8))
        d2_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, d2_kernel)
        result = cv2.subtract(result, d2_lines)

        # Clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)

        return result

    def _extract_features(
        self,
        contour: np.ndarray,
        use_hull_normalization: bool = False
    ) -> Optional[Dict]:
        """
        Extract shape features from a contour.

        Args:
            contour: OpenCV contour
            use_hull_normalization: If True, use convex hull for shape features
                                   (helps normalize markers with attached line segments)

        Returns:
            Dictionary with shape features or None if invalid
        """
        # Get convex hull for normalization
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area == 0:
            return None

        # Use hull for shape analysis if enabled (normalizes markers with line attachments)
        shape_contour = hull if use_hull_normalization else contour

        # Calculate moments
        moments = cv2.moments(shape_contour)
        if moments['m00'] == 0:
            return None

        # Centroid (always from original contour for accurate position)
        orig_moments = cv2.moments(contour)
        if orig_moments['m00'] == 0:
            return None
        cx = orig_moments['m10'] / orig_moments['m00']
        cy = orig_moments['m01'] / orig_moments['m00']

        # Area (from shape contour)
        area = cv2.contourArea(shape_contour)

        # Perimeter (from shape contour)
        perimeter = cv2.arcLength(shape_contour, True)
        if perimeter == 0:
            return None

        # Circularity: 4 * pi * Area / Perimeter^2
        # Perfect circle = 1.0
        circularity = 4 * np.pi * area / (perimeter ** 2)

        # Solidity (original contour area / hull area)
        orig_area = cv2.contourArea(contour)
        solidity = orig_area / hull_area

        # Hu moments (rotation-invariant shape descriptors) from shape contour
        hu_moments = cv2.HuMoments(moments).flatten()

        # Bounding box from shape contour
        x, y, w, h = cv2.boundingRect(shape_contour)
        aspect_ratio = float(w) / h if h > 0 else 1.0

        # Extent: object area / bounding box area
        rect_area = w * h
        extent = area / rect_area if rect_area > 0 else 0

        # Number of vertices (useful for distinguishing shapes)
        # Approximate contour to polygon
        epsilon = 0.04 * perimeter
        approx = cv2.approxPolyDP(shape_contour, epsilon, True)
        num_vertices = len(approx)

        # Minimum enclosing circle ratio
        (_, _), radius = cv2.minEnclosingCircle(shape_contour)
        circle_area = np.pi * radius * radius
        circle_ratio = area / circle_area if circle_area > 0 else 0

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
            'num_vertices': num_vertices,
            'circle_ratio': float(circle_ratio),
            'contour': contour,
            'hull': hull,
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

    def detect_by_distance_peaks(
        self,
        binary: np.ndarray,
        min_distance: int = 12,
        threshold: float = 2.5
    ) -> List[Dict]:
        """
        Detect markers using distance transform local maxima.
        Markers create local peaks in the distance transform.

        Args:
            binary: Binary image
            min_distance: Minimum distance between detected points
            threshold: Minimum distance transform value

        Returns:
            List of marker dictionaries
        """
        from skimage.feature import peak_local_max

        # Distance transform
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

        # Find local maxima
        local_max = peak_local_max(
            dist_transform,
            min_distance=min_distance,
            threshold_abs=threshold,
            exclude_border=False
        )

        markers = []
        for y, x in local_max:
            dist_val = dist_transform[y, x]
            if dist_val >= threshold:
                markers.append({
                    'cx': float(x),
                    'cy': float(y),
                    'area': float(np.pi * dist_val**2),
                    'circularity': 0.8,
                    'solidity': 0.9,
                    'aspect_ratio': 1.0,
                    'extent': 0.7,
                    'hu_moments': [0.16] * 7,
                    'num_vertices': 4,
                    'circle_ratio': 0.7,
                    'detection_method': 'distance_peak',
                    'distance_value': float(dist_val)
                })

        return markers

    def detect_combined(
        self,
        binary: np.ndarray,
        original: Optional[np.ndarray] = None,
        min_marker_distance: int = 10
    ) -> List[Dict]:
        """
        Combined detection using multiple methods for better accuracy.
        Best for images where markers overlap with lines.

        Combines:
        1. Morphological blob detection
        2. Distance transform peaks
        3. Filters by minimum distance to avoid duplicates

        Args:
            binary: Binary image
            original: Original color image (optional)
            min_marker_distance: Minimum distance between markers

        Returns:
            List of marker dictionaries
        """
        all_markers = []

        # Method 1: Standard blob detection
        blob_markers = self.detect(binary, original)
        for m in blob_markers:
            m['detection_method'] = 'blob'
        all_markers.extend(blob_markers)

        # Method 2: Distance transform peaks
        dist_markers = self.detect_by_distance_peaks(
            binary,
            min_distance=min_marker_distance,
            threshold=2.0
        )

        # Add distance markers that aren't duplicates
        for dm in dist_markers:
            is_duplicate = False
            for m in all_markers:
                dist = np.sqrt((dm['cx'] - m['cx'])**2 + (dm['cy'] - m['cy'])**2)
                if dist < min_marker_distance:
                    is_duplicate = True
                    break
            if not is_duplicate:
                all_markers.append(dm)

        # Final deduplication
        filtered_markers = []
        for m in all_markers:
            is_duplicate = False
            for fm in filtered_markers:
                dist = np.sqrt((m['cx'] - fm['cx'])**2 + (m['cy'] - fm['cy'])**2)
                if dist < min_marker_distance:
                    # Keep the one detected by blob method (more reliable shape info)
                    if m.get('detection_method') == 'blob' and fm.get('detection_method') != 'blob':
                        filtered_markers.remove(fm)
                        filtered_markers.append(m)
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_markers.append(m)

        return filtered_markers

    @staticmethod
    def sort_by_x(markers: List[Dict]) -> List[Dict]:
        """Sort markers by x-coordinate (centroid)."""
        return sorted(markers, key=lambda m: m['cx'])

    @staticmethod
    def sort_by_y(markers: List[Dict]) -> List[Dict]:
        """Sort markers by y-coordinate (centroid)."""
        return sorted(markers, key=lambda m: m['cy'])
