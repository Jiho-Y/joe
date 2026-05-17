#!/usr/bin/env python3
"""
Test exclude zone functionality for legend filtering.
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.processing.preprocessing import preprocess_image
from src.processing.marker_detector import MarkerDetector
from src.processing.clustering import ShapeClusterer


def is_point_in_exclude_zone(cx, cy, exclude_zones):
    """Check if point is in any exclude zone."""
    for zone in exclude_zones:
        x1, y1, x2, y2 = zone
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            return True
    return False


def test_with_exclude_zone():
    """Test detection with exclude zone filtering."""
    # Create test image with legend
    h, w = 400, 500
    image = np.ones((h, w, 3), dtype=np.uint8) * 255

    # Draw axes
    margin = 60
    cv2.line(image, (margin, h-margin), (w-80, h-margin), (0, 0, 0), 2)
    cv2.line(image, (margin, h-margin), (margin, margin), (0, 0, 0), 2)

    # Draw curves with markers
    def draw_triangle(img, p):
        pts = np.array([[p[0], p[1]-6], [p[0]-6, p[1]+4], [p[0]+6, p[1]+4]])
        cv2.fillPoly(img, [pts], (0, 0, 0))

    def draw_circle(img, p):
        cv2.circle(img, p, 5, (0, 0, 0), -1)

    def draw_square(img, p):
        cv2.rectangle(img, (p[0]-5, p[1]-5), (p[0]+5, p[1]+5), (0, 0, 0), -1)

    def draw_diamond(img, p):
        pts = np.array([[p[0], p[1]-6], [p[0]+6, p[1]], [p[0], p[1]+6], [p[0]-6, p[1]]])
        cv2.fillPoly(img, [pts], (0, 0, 0))

    marker_funcs = [draw_triangle, draw_circle, draw_square, draw_diamond]

    # Curves in graph area
    curves_data = [
        [(70, 350), (120, 300), (180, 200), (250, 120)],
        [(70, 350), (140, 320), (220, 280), (300, 250)],
        [(70, 350), (160, 340), (260, 320), (360, 300)],
        [(70, 350), (180, 345), (300, 335), (400, 320)],
    ]

    for i, (curve, marker_func) in enumerate(zip(curves_data, marker_funcs)):
        prev = None
        for pt in curve:
            if prev:
                cv2.line(image, prev, pt, (0, 0, 0), 1)
            marker_func(image, pt)
            prev = pt

    # Legend markers (upper right)
    legend_x = w - 70
    for i, marker_func in enumerate(marker_funcs):
        y = 40 + i * 25
        marker_func(image, (legend_x, y))
        cv2.line(image, (legend_x + 10, y), (legend_x + 40, y), (0, 0, 0), 1)

    # Run detection WITHOUT exclude zone
    print("="*60)
    print("TEST 1: Detection WITHOUT exclude zone")
    print("="*60)

    binary = preprocess_image(image, kernel_size=5)
    detector = MarkerDetector(min_area=30, max_area=500, kernel_size=5)
    markers = detector.detect(binary, image)

    print(f"Total markers detected: {len(markers)}")

    # Count markers by region
    graph_markers = [m for m in markers if m['cx'] < w * 0.7]
    legend_markers = [m for m in markers if m['cx'] >= w * 0.7]
    print(f"  - Graph area markers: {len(graph_markers)}")
    print(f"  - Legend area markers: {len(legend_markers)}")

    # Run detection WITH exclude zone
    print("\n" + "="*60)
    print("TEST 2: Detection WITH exclude zone")
    print("="*60)

    # Define exclude zone (legend area)
    exclude_zones = [[int(w * 0.7), 0, w, int(h * 0.5)]]
    print(f"Exclude zone: {exclude_zones[0]}")

    # Filter markers
    filtered_markers = [
        m for m in markers
        if not is_point_in_exclude_zone(m['cx'], m['cy'], exclude_zones)
    ]

    excluded_count = len(markers) - len(filtered_markers)
    print(f"Markers after filtering: {len(filtered_markers)}")
    print(f"Excluded markers: {excluded_count}")

    # Cluster filtered markers
    clusterer = ShapeClusterer(n_clusters=4)
    clusters = clusterer.cluster(filtered_markers)

    print(f"\nClusters after filtering:")
    for cluster_id, points in clusters.items():
        print(f"  Cluster {cluster_id}: {len(points)} points")

    # Verify results
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)

    expected_curve_markers = sum(len(curve) for curve in curves_data)
    expected_legend_markers = len(marker_funcs)

    print(f"Expected curve markers: {expected_curve_markers}")
    print(f"Expected legend markers: {expected_legend_markers}")
    print(f"Detected after filtering: {len(filtered_markers)}")

    if len(filtered_markers) >= expected_curve_markers * 0.8:
        print("\n[PASS] Most curve markers detected")
    else:
        print("\n[FAIL] Too few curve markers detected")

    if excluded_count >= expected_legend_markers * 0.8:
        print("[PASS] Legend markers filtered out")
    else:
        print("[FAIL] Legend markers not properly filtered")

    # Save visualization
    vis_image = image.copy()
    colors = [(0, 0, 255), (0, 128, 0), (255, 0, 0), (0, 165, 255)]

    for cluster_id, points in clusters.items():
        color = colors[cluster_id % len(colors)]
        for p in points:
            cv2.circle(vis_image, (int(p['cx']), int(p['cy'])), 10, color, 2)

    # Draw exclude zone
    x1, y1, x2, y2 = exclude_zones[0]
    cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.putText(vis_image, "EXCLUDE", (x1+5, y1+20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    output_path = os.path.join(
        os.path.dirname(__file__),
        'sample_images',
        'exclude_zone_test.png'
    )
    cv2.imwrite(output_path, vis_image)
    print(f"\nVisualization saved to: {output_path}")

    return len(filtered_markers), excluded_count


if __name__ == '__main__':
    test_with_exclude_zone()
