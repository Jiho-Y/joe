"""
Tests for marker detection and clustering.
"""

import unittest
import numpy as np
import cv2
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.processing.preprocessing import preprocess_image, remove_lines
from src.processing.marker_detector import MarkerDetector
from src.processing.clustering import ShapeClusterer
from src.calibration import Calibration


class TestPreprocessing(unittest.TestCase):
    """Tests for preprocessing functions."""

    def test_preprocess_image(self):
        """Test basic preprocessing."""
        # Create a simple test image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        # Add a black line
        cv2.line(image, (10, 50), (90, 50), (0, 0, 0), 2)
        # Add a marker (circle)
        cv2.circle(image, (50, 50), 8, (0, 0, 0), -1)

        binary = preprocess_image(image)

        self.assertEqual(binary.shape, (100, 100))
        self.assertEqual(binary.dtype, np.uint8)
        # Check that there are white pixels (foreground)
        self.assertTrue(np.any(binary > 0))

    def test_remove_lines(self):
        """Test line removal."""
        # Create binary image with line and circle
        binary = np.zeros((100, 100), dtype=np.uint8)
        # Thin line
        cv2.line(binary, (10, 50), (90, 50), 255, 1)
        # Filled circle
        cv2.circle(binary, (50, 30), 10, 255, -1)

        result = remove_lines(binary, kernel_size=5)

        # Circle should remain (mostly)
        self.assertTrue(np.any(result > 0))


class TestMarkerDetector(unittest.TestCase):
    """Tests for MarkerDetector."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = MarkerDetector(
            min_area=30,
            max_area=500,
            kernel_size=5
        )

    def test_detect_circles(self):
        """Test detection of circular markers."""
        # Create image with circles
        image = np.ones((200, 200, 3), dtype=np.uint8) * 255

        # Add several circles at different positions
        cv2.circle(image, (50, 50), 8, (0, 0, 0), -1)
        cv2.circle(image, (100, 80), 8, (0, 0, 0), -1)
        cv2.circle(image, (150, 100), 8, (0, 0, 0), -1)

        binary = preprocess_image(image)
        markers = self.detector.detect(binary, image)

        # Should detect 3 markers
        self.assertEqual(len(markers), 3)

        # Check circularity is high for circles
        for marker in markers:
            self.assertGreater(marker['circularity'], 0.7)

    def test_detect_squares(self):
        """Test detection of square markers."""
        image = np.ones((200, 200, 3), dtype=np.uint8) * 255

        # Add squares
        cv2.rectangle(image, (40, 40), (60, 60), (0, 0, 0), -1)
        cv2.rectangle(image, (90, 70), (110, 90), (0, 0, 0), -1)

        binary = preprocess_image(image)
        markers = self.detector.detect(binary, image)

        self.assertEqual(len(markers), 2)

        # Squares have lower circularity than circles
        for marker in markers:
            self.assertLess(marker['circularity'], 0.9)

    def test_filter_by_area(self):
        """Test area filtering."""
        image = np.ones((200, 200, 3), dtype=np.uint8) * 255

        # Small marker (should be filtered)
        cv2.circle(image, (50, 50), 2, (0, 0, 0), -1)
        # Normal marker
        cv2.circle(image, (100, 50), 8, (0, 0, 0), -1)
        # Large marker (should be filtered)
        cv2.circle(image, (150, 50), 30, (0, 0, 0), -1)

        binary = preprocess_image(image)
        markers = self.detector.detect(binary, image)

        # Only middle-sized marker should be detected
        self.assertEqual(len(markers), 1)


class TestShapeClusterer(unittest.TestCase):
    """Tests for ShapeClusterer."""

    def test_cluster_different_shapes(self):
        """Test clustering of different marker shapes."""
        # Create markers with different shape features
        markers = [
            # Circles (high circularity)
            {'cx': 10, 'cy': 10, 'circularity': 0.95, 'solidity': 0.98,
             'area': 100, 'hu_moments': [0.16, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
            {'cx': 20, 'cy': 10, 'circularity': 0.93, 'solidity': 0.97,
             'area': 105, 'hu_moments': [0.16, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
            # Squares (medium circularity)
            {'cx': 30, 'cy': 10, 'circularity': 0.78, 'solidity': 0.99,
             'area': 100, 'hu_moments': [0.17, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
            {'cx': 40, 'cy': 10, 'circularity': 0.76, 'solidity': 0.98,
             'area': 98, 'hu_moments': [0.17, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
        ]

        clusterer = ShapeClusterer(n_clusters=2)
        clusters = clusterer.cluster(markers)

        # Should have 2 clusters
        self.assertEqual(len(clusters), 2)

        # Each cluster should have 2 markers
        for cluster_id, points in clusters.items():
            self.assertEqual(len(points), 2)

    def test_cluster_statistics(self):
        """Test cluster statistics computation."""
        markers = [
            {'cx': 10, 'cy': 10, 'circularity': 0.9, 'solidity': 0.95,
             'area': 100, 'hu_moments': [0.16, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
             'cluster': 0},
            {'cx': 20, 'cy': 15, 'circularity': 0.92, 'solidity': 0.96,
             'area': 110, 'hu_moments': [0.16, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
             'cluster': 0},
        ]

        clusters = {0: markers}
        clusterer = ShapeClusterer()
        stats = clusterer.get_cluster_statistics(clusters)

        self.assertIn(0, stats)
        self.assertEqual(stats[0]['count'], 2)
        self.assertAlmostEqual(stats[0]['mean_circularity'], 0.91, places=2)


class TestCalibration(unittest.TestCase):
    """Tests for Calibration."""

    def setUp(self):
        """Set up test fixtures."""
        self.calib = Calibration()

    def test_linear_calibration(self):
        """Test linear coordinate transformation."""
        # Set up calibration: pixels 0->100 maps to values 0->800
        self.calib.set_x_calibration([0, 100], [0, 800], 'linear')
        self.calib.set_y_calibration([100, 0], [0, 25], 'linear')  # Y inverted

        # Test transformation
        rx, ry = self.calib.pixel_to_real(50, 50)

        self.assertAlmostEqual(rx, 400, places=1)
        self.assertAlmostEqual(ry, 12.5, places=1)

    def test_log_calibration(self):
        """Test logarithmic coordinate transformation."""
        # Log scale: pixels 0->100 maps to values 1->1000
        self.calib.set_x_calibration([0, 100], [1, 1000], 'logarithmic')

        rx, _ = self.calib.pixel_to_real(50, 0)

        # At 50%, should be sqrt(1*1000) ≈ 31.6
        self.assertAlmostEqual(rx, 31.62, places=1)

    def test_uncalibrated(self):
        """Test behavior when uncalibrated."""
        self.assertFalse(self.calib.is_calibrated())

        rx, ry = self.calib.pixel_to_real(100, 100)
        self.assertIsNone(rx)
        self.assertIsNone(ry)

    def test_inverse_transform(self):
        """Test inverse transformation (real to pixel)."""
        self.calib.set_x_calibration([0, 100], [0, 800], 'linear')

        px, _ = self.calib.real_to_pixel(400, 0)
        self.assertAlmostEqual(px, 50, places=1)


def create_sample_creep_image():
    """
    Create a sample creep curve image for testing.

    Creates an image with:
    - 4 curves with different marker types
    - X axis: 0-800 hours
    - Y axis: 0-25 % strain
    """
    width, height = 800, 600
    margin = 80

    # Create white background
    image = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Draw axes
    cv2.line(image, (margin, height - margin), (width - margin, height - margin), (0, 0, 0), 2)
    cv2.line(image, (margin, height - margin), (margin, margin), (0, 0, 0), 2)

    # Add axis labels
    cv2.putText(image, "Time (h)", (width // 2 - 30, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(image, "Strain (%)", (10, height // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    # X-axis ticks
    for i, val in enumerate([0, 200, 400, 600, 800]):
        x = margin + int((width - 2 * margin) * i / 4)
        cv2.line(image, (x, height - margin), (x, height - margin + 5), (0, 0, 0), 1)
        cv2.putText(image, str(val), (x - 15, height - margin + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # Y-axis ticks
    for i, val in enumerate([0, 5, 10, 15, 20, 25]):
        y = height - margin - int((height - 2 * margin) * i / 5)
        cv2.line(image, (margin - 5, y), (margin, y), (0, 0, 0), 1)
        cv2.putText(image, str(val), (margin - 30, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # Define creep curves (time, strain pairs)
    # 4 different curves with typical creep behavior
    curves = [
        # Curve 1: Fast initial creep, then steady
        [(0, 0), (50, 3), (100, 5), (200, 8), (400, 12), (600, 15), (800, 18)],
        # Curve 2: Moderate creep
        [(0, 0), (50, 2), (100, 3.5), (200, 5.5), (400, 8), (600, 10), (800, 12)],
        # Curve 3: Slow creep
        [(0, 0), (50, 1), (100, 2), (200, 3.5), (400, 5), (600, 6.5), (800, 8)],
        # Curve 4: Very slow creep
        [(0, 0), (50, 0.5), (100, 1), (200, 2), (400, 3), (600, 4), (800, 5)],
    ]

    # Convert to pixel coordinates
    def to_pixel(time, strain):
        x = margin + int((time / 800) * (width - 2 * margin))
        y = height - margin - int((strain / 25) * (height - 2 * margin))
        return x, y

    # Draw markers for each curve
    marker_funcs = [
        # Triangle (pointing up)
        lambda img, p: cv2.drawContours(img, [np.array([
            [p[0], p[1] - 6], [p[0] - 6, p[1] + 4], [p[0] + 6, p[1] + 4]
        ])], 0, (0, 0, 0), -1),
        # Circle
        lambda img, p: cv2.circle(img, p, 5, (0, 0, 0), -1),
        # Square
        lambda img, p: cv2.rectangle(img, (p[0] - 5, p[1] - 5), (p[0] + 5, p[1] + 5), (0, 0, 0), -1),
        # Diamond
        lambda img, p: cv2.drawContours(img, [np.array([
            [p[0], p[1] - 6], [p[0] + 6, p[1]], [p[0], p[1] + 6], [p[0] - 6, p[1]]
        ])], 0, (0, 0, 0), -1),
    ]

    for curve_idx, curve in enumerate(curves):
        marker_func = marker_funcs[curve_idx]
        prev_point = None

        for time, strain in curve:
            px, py = to_pixel(time, strain)

            # Draw connecting line
            if prev_point is not None:
                cv2.line(image, prev_point, (px, py), (0, 0, 0), 1)

            # Draw marker
            marker_func(image, (px, py))
            prev_point = (px, py)

    return image


if __name__ == '__main__':
    # Create and save sample image
    sample_dir = os.path.dirname(os.path.abspath(__file__))
    sample_path = os.path.join(sample_dir, 'sample_images', 'creep_sample.png')

    os.makedirs(os.path.dirname(sample_path), exist_ok=True)

    image = create_sample_creep_image()
    cv2.imwrite(sample_path, image)
    print(f"Sample image saved to: {sample_path}")

    # Run tests
    unittest.main(verbosity=2)
