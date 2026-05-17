"""
Line extraction for Mode B1 (Line only - distinguishing by line style).
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.signal import find_peaks


class LineExtractor:
    """
    Extracts curves based on line style (solid, dashed, dotted).
    Used for Mode B1 (Line only graphs).
    """

    def __init__(self):
        """Initialize the line extractor."""
        self.templates = {}  # Style name -> gap pattern

    def add_template(
        self,
        style_name: str,
        binary_region: np.ndarray,
        direction: str = 'horizontal'
    ):
        """
        Add a line style template from a user-selected region.

        Args:
            style_name: Name for this line style (e.g., 'solid', 'dashed')
            binary_region: Binary image of the template region
            direction: 'horizontal' or 'vertical'
        """
        # Extract gap pattern
        pattern = self._extract_gap_pattern(binary_region, direction)
        self.templates[style_name] = {
            'pattern': pattern,
            'direction': direction
        }

    def _extract_gap_pattern(
        self,
        binary: np.ndarray,
        direction: str
    ) -> List[int]:
        """
        Extract gap pattern from a line segment.

        Args:
            binary: Binary image of line segment
            direction: Line direction

        Returns:
            List of gap lengths (0 for solid line)
        """
        if direction == 'horizontal':
            # Sum along y-axis to get 1D profile
            profile = np.sum(binary, axis=0)
        else:
            # Sum along x-axis
            profile = np.sum(binary, axis=1)

        # Threshold to get binary profile
        threshold = np.max(profile) * 0.5
        binary_profile = (profile > threshold).astype(int)

        # Find transitions
        transitions = np.diff(binary_profile)
        rising = np.where(transitions == 1)[0]
        falling = np.where(transitions == -1)[0]

        if len(falling) == 0 or len(rising) == 0:
            return [0]  # Solid line

        # Calculate gap lengths
        gaps = []
        for i, fall in enumerate(falling):
            # Find next rise after this fall
            next_rises = rising[rising > fall]
            if len(next_rises) > 0:
                gap = next_rises[0] - fall
                gaps.append(gap)

        return gaps if gaps else [0]

    def extract_curves(
        self,
        binary: np.ndarray,
        roi: List[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        Extract curves and group by line style.

        Args:
            binary: Binary image
            roi: Optional ROI [x1, y1, x2, y2]

        Returns:
            Dictionary mapping style name to list of points
        """
        if not self.templates:
            # No templates defined, return all as one curve
            return {'default': self._extract_all_points(binary, roi)}

        # Skeletonize
        skeleton = self._skeletonize(binary)

        # For each template, find matching segments
        curves = {}
        for style_name, template in self.templates.items():
            points = self._match_style(skeleton, template, roi)
            if points:
                curves[style_name] = points

        return curves

    def _skeletonize(self, binary: np.ndarray) -> np.ndarray:
        """Apply skeletonization."""
        from skimage.morphology import skeletonize

        binary_norm = (binary > 0).astype(np.uint8)
        skeleton = skeletonize(binary_norm)
        return (skeleton * 255).astype(np.uint8)

    def _extract_all_points(
        self,
        binary: np.ndarray,
        roi: List[int] = None
    ) -> List[Dict]:
        """Extract all skeleton points without style matching."""
        skeleton = self._skeletonize(binary)

        y_coords, x_coords = np.where(skeleton > 0)

        if len(x_coords) == 0:
            return []

        x_offset = roi[0] if roi else 0
        y_offset = roi[1] if roi else 0

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
                'solidity': 0
            })

        return sorted(points, key=lambda p: p['cx'])

    def _match_style(
        self,
        skeleton: np.ndarray,
        template: Dict,
        roi: List[int] = None
    ) -> List[Dict]:
        """
        Match skeleton segments to a line style template.

        This is a simplified implementation. A full implementation
        would use more sophisticated pattern matching.
        """
        pattern = template['pattern']

        if pattern == [0]:
            # Solid line - match continuous segments
            return self._extract_continuous_segments(skeleton, roi)
        else:
            # Dashed/dotted - match by gap pattern
            return self._extract_patterned_segments(skeleton, pattern, roi)

    def _extract_continuous_segments(
        self,
        skeleton: np.ndarray,
        roi: List[int] = None
    ) -> List[Dict]:
        """Extract continuous (solid) line segments."""
        # Find connected components
        num_labels, labels = cv2.connectedComponents(skeleton)

        x_offset = roi[0] if roi else 0
        y_offset = roi[1] if roi else 0

        all_points = []
        for label in range(1, num_labels):
            mask = (labels == label).astype(np.uint8)
            y_coords, x_coords = np.where(mask > 0)

            if len(x_coords) < 10:  # Skip small segments
                continue

            # Check if this is a continuous segment (low gap ratio)
            profile = np.sum(mask, axis=0)
            nonzero = np.count_nonzero(profile)
            total_range = np.max(x_coords) - np.min(x_coords) + 1

            if nonzero / total_range > 0.8:  # 80% continuous
                for x in np.unique(x_coords):
                    y_at_x = y_coords[x_coords == x]
                    mean_y = np.mean(y_at_x)
                    all_points.append({
                        'cx': float(x + x_offset),
                        'cy': float(mean_y + y_offset),
                        'area': 0,
                        'circularity': 0,
                        'solidity': 0
                    })

        return sorted(all_points, key=lambda p: p['cx'])

    def _extract_patterned_segments(
        self,
        skeleton: np.ndarray,
        pattern: List[int],
        roi: List[int] = None
    ) -> List[Dict]:
        """Extract segments matching a gap pattern."""
        # Simplified: just extract non-continuous segments
        num_labels, labels = cv2.connectedComponents(skeleton)

        x_offset = roi[0] if roi else 0
        y_offset = roi[1] if roi else 0

        all_points = []
        avg_pattern_gap = np.mean(pattern) if pattern else 0

        for label in range(1, num_labels):
            mask = (labels == label).astype(np.uint8)
            y_coords, x_coords = np.where(mask > 0)

            if len(x_coords) < 5:
                continue

            # Calculate gap statistics for this segment
            profile = np.sum(mask, axis=0)
            gaps = self._measure_gaps(profile)

            if gaps:
                avg_gap = np.mean(gaps)
                # Match if gap size is similar to pattern
                if abs(avg_gap - avg_pattern_gap) < avg_pattern_gap * 0.5:
                    for x in np.unique(x_coords):
                        y_at_x = y_coords[x_coords == x]
                        mean_y = np.mean(y_at_x)
                        all_points.append({
                            'cx': float(x + x_offset),
                            'cy': float(mean_y + y_offset),
                            'area': 0,
                            'circularity': 0,
                            'solidity': 0
                        })

        return sorted(all_points, key=lambda p: p['cx'])

    def _measure_gaps(self, profile: np.ndarray) -> List[int]:
        """Measure gaps in a 1D profile."""
        binary = (profile > 0).astype(int)
        transitions = np.diff(binary)

        falling = np.where(transitions == -1)[0]
        rising = np.where(transitions == 1)[0]

        gaps = []
        for fall in falling:
            next_rises = rising[rising > fall]
            if len(next_rises) > 0:
                gaps.append(next_rises[0] - fall)

        return gaps
