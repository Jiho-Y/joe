#!/usr/bin/env python3
"""
Detection test script for creep curve images.
Tests marker detection and identifies potential issues like legend detection.
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.processing.preprocessing import preprocess_image
from src.processing.marker_detector import MarkerDetector
from src.processing.clustering import ShapeClusterer


def analyze_image(image_path: str, params: dict = None):
    """
    Analyze an image and report detected markers.
    """
    params = params or {
        'kernel_size': 5,
        'min_area': 30,
        'max_area': 500,
        'n_clusters': 4
    }

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return None

    print(f"Image size: {image.shape[1]} x {image.shape[0]}")

    # Preprocess
    binary = preprocess_image(image, params['kernel_size'])

    # Detect markers
    detector = MarkerDetector(
        min_area=params['min_area'],
        max_area=params['max_area'],
        kernel_size=params['kernel_size']
    )
    markers = detector.detect(binary, image)

    print(f"\nTotal markers detected: {len(markers)}")

    if not markers:
        return None

    # Analyze marker positions
    print("\n=== Marker Position Analysis ===")

    # Group by quadrant
    h, w = image.shape[:2]
    quadrants = {'TL': [], 'TR': [], 'BL': [], 'BR': []}

    for m in markers:
        cx, cy = m['cx'], m['cy']
        if cx < w/2 and cy < h/2:
            quadrants['TL'].append(m)
        elif cx >= w/2 and cy < h/2:
            quadrants['TR'].append(m)
        elif cx < w/2 and cy >= h/2:
            quadrants['BL'].append(m)
        else:
            quadrants['BR'].append(m)

    for q, pts in quadrants.items():
        print(f"  {q} (top-left/right, bottom-left/right): {len(pts)} markers")

    # Check for vertically aligned markers (legend pattern)
    print("\n=== Legend Detection Analysis ===")

    # Find markers with similar x-coordinates (potential legend)
    x_coords = np.array([m['cx'] for m in markers])

    # Check right side of image for vertically aligned markers
    right_threshold = w * 0.7  # Right 30% of image
    right_markers = [m for m in markers if m['cx'] > right_threshold]

    if right_markers:
        print(f"  Markers in right 30% of image: {len(right_markers)}")

        # Check vertical alignment
        right_x = [m['cx'] for m in right_markers]
        right_y = [m['cy'] for m in right_markers]

        if len(right_markers) >= 3:
            x_std = np.std(right_x)
            print(f"  X-coordinate std dev: {x_std:.2f} (low = vertically aligned)")

            if x_std < 20:  # Very aligned = likely legend
                print("  WARNING: Possible legend markers detected!")
                print(f"  Legend marker positions (y): {sorted(right_y)}")

    # Cluster markers
    print("\n=== Clustering Results ===")
    clusterer = ShapeClusterer(n_clusters=params['n_clusters'])
    clusters = clusterer.cluster(markers)

    for cluster_id, points in clusters.items():
        circs = [p['circularity'] for p in points]
        sols = [p['solidity'] for p in points]
        print(f"  Cluster {cluster_id}: {len(points)} markers")
        print(f"    Circularity: mean={np.mean(circs):.3f}, std={np.std(circs):.3f}")
        print(f"    Solidity: mean={np.mean(sols):.3f}, std={np.std(sols):.3f}")

        # Check if cluster might be legend
        cluster_x = [p['cx'] for p in points]
        if np.mean(cluster_x) > right_threshold and np.std(cluster_x) < 30:
            print(f"    NOTE: This cluster may contain legend markers")

    # Create visualization
    vis_image = image.copy()
    colors = [
        (0, 0, 255),    # Red
        (0, 128, 0),    # Green
        (255, 0, 0),    # Blue
        (0, 165, 255),  # Orange
    ]

    for cluster_id, points in clusters.items():
        color = colors[cluster_id % len(colors)]
        for p in points:
            cx, cy = int(p['cx']), int(p['cy'])
            cv2.circle(vis_image, (cx, cy), 8, color, 2)
            cv2.putText(vis_image, str(cluster_id), (cx+10, cy),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # Draw legend boundary suggestion
    cv2.rectangle(vis_image, (int(w*0.7), 0), (w, int(h*0.4)), (128, 128, 128), 2)
    cv2.putText(vis_image, "Legend?", (int(w*0.72), 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)

    # Save visualization
    output_path = image_path.replace('.png', '_detected.png').replace('.jpg', '_detected.jpg')
    cv2.imwrite(output_path, vis_image)
    print(f"\nVisualization saved to: {output_path}")

    return clusters


def suggest_roi_for_legend_exclusion(image_path: str):
    """
    Suggest ROI coordinates to exclude legend area.
    """
    image = cv2.imread(image_path)
    if image is None:
        return None

    h, w = image.shape[:2]

    # Typical legend position is upper right
    # Suggest ROI that excludes right 25% and top 35%
    suggestions = [
        {
            'name': 'Exclude legend (conservative)',
            'roi': [0, int(h*0.1), int(w*0.75), h],
            'description': 'Excludes right 25% and top 10%'
        },
        {
            'name': 'Graph area only',
            'roi': [int(w*0.1), int(h*0.1), int(w*0.70), int(h*0.85)],
            'description': 'Tight crop around typical graph area'
        }
    ]

    print("\n=== Suggested ROI to exclude legend ===")
    for s in suggestions:
        print(f"  {s['name']}: {s['roi']}")
        print(f"    {s['description']}")

    return suggestions


if __name__ == '__main__':
    # Create a synthetic test image with legend-like pattern
    print("Creating synthetic test image with legend...")

    # Create test image
    h, w = 400, 500
    image = np.ones((h, w, 3), dtype=np.uint8) * 255

    # Draw axes
    margin = 60
    cv2.line(image, (margin, h-margin), (w-80, h-margin), (0, 0, 0), 2)
    cv2.line(image, (margin, h-margin), (margin, margin), (0, 0, 0), 2)

    # Draw 4 curves with different markers
    curves_data = [
        [(70, 350), (120, 300), (180, 200), (250, 120), (320, 80)],    # Steep curve
        [(70, 350), (140, 320), (220, 280), (300, 250), (380, 230)],   # Moderate curve
        [(70, 350), (160, 340), (260, 320), (360, 300)],               # Slow curve
        [(70, 350), (180, 345), (300, 335), (400, 320)],               # Very slow curve
    ]

    # Marker drawing functions
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

    # Draw curves
    for i, (curve, marker_func) in enumerate(zip(curves_data, marker_funcs)):
        prev = None
        for pt in curve:
            if prev:
                cv2.line(image, prev, pt, (0, 0, 0), 1)
            marker_func(image, pt)
            prev = pt

    # Draw legend (upper right) - THIS IS THE KEY TEST
    legend_x = w - 70
    legend_y_start = 40
    legend_spacing = 25

    for i, marker_func in enumerate(marker_funcs):
        y = legend_y_start + i * legend_spacing
        marker_func(image, (legend_x, y))
        cv2.line(image, (legend_x + 10, y), (legend_x + 40, y), (0, 0, 0), 1)

    # Add text labels
    cv2.putText(image, "800C-200MPa", (legend_x-55, legend_y_start+5),
               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
    cv2.putText(image, "800C-150MPa", (legend_x-55, legend_y_start+30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

    # Save test image
    test_path = os.path.join(os.path.dirname(__file__), 'sample_images', 'legend_test.png')
    cv2.imwrite(test_path, image)
    print(f"Test image saved to: {test_path}")

    # Run analysis
    print("\n" + "="*60)
    print("ANALYSIS RESULTS")
    print("="*60)

    analyze_image(test_path)
    suggest_roi_for_legend_exclusion(test_path)
