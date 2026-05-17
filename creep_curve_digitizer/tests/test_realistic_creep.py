#!/usr/bin/env python3
"""
Test marker detection with the actual creep curve image pattern.
Compares different detection methods.
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.processing.preprocessing import preprocess_image
from src.processing.marker_detector import MarkerDetector
from src.processing.clustering import ShapeClusterer, CurveTracer


def create_realistic_creep_image():
    """
    Create a test image that closely matches the user's actual creep curve image.
    - 4 curves with different marker types (triangle, circle, square, diamond)
    - Lines connecting markers
    - Legend in upper right
    """
    h, w = 350, 450
    image = np.ones((h, w, 3), dtype=np.uint8) * 255

    # Draw axes
    margin_left, margin_bottom = 50, 50
    margin_right, margin_top = 80, 30

    # X-axis
    cv2.line(image, (margin_left, h - margin_bottom),
             (w - margin_right, h - margin_bottom), (0, 0, 0), 1)
    # Y-axis
    cv2.line(image, (margin_left, h - margin_bottom),
             (margin_left, margin_top), (0, 0, 0), 1)

    # Axis labels
    cv2.putText(image, "Creep time, h", (w//2 - 40, h - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    cv2.putText(image, "Creep strain, %", (5, h//2),
               cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)

    # Graph area bounds
    graph_left = margin_left
    graph_right = w - margin_right
    graph_top = margin_top
    graph_bottom = h - margin_bottom

    # Marker drawing functions (same as actual markers)
    def draw_triangle_up(img, p, size=5):
        pts = np.array([
            [p[0], p[1] - size],
            [p[0] - size, p[1] + size//2 + 2],
            [p[0] + size, p[1] + size//2 + 2]
        ], dtype=np.int32)
        cv2.fillPoly(img, [pts], (0, 0, 0))

    def draw_circle(img, p, size=4):
        cv2.circle(img, p, size, (0, 0, 0), -1)

    def draw_square(img, p, size=4):
        cv2.rectangle(img, (p[0]-size, p[1]-size), (p[0]+size, p[1]+size), (0, 0, 0), -1)

    def draw_diamond(img, p, size=5):
        pts = np.array([
            [p[0], p[1] - size],
            [p[0] + size, p[1]],
            [p[0], p[1] + size],
            [p[0] - size, p[1]]
        ], dtype=np.int32)
        cv2.fillPoly(img, [pts], (0, 0, 0))

    marker_funcs = [draw_triangle_up, draw_circle, draw_square, draw_diamond]
    marker_names = ["Triangle", "Circle", "Square", "Diamond"]

    # Define 4 creep curves (like the actual image)
    # Curve 1: 800°C-200MPa (fastest creep, steep rise)
    # Curve 2: 800°C-150MPa
    # Curve 3: 800°C-100MPa
    # Curve 4: 800°C-80MPa (slowest creep)

    def time_to_x(t, max_t=800):
        return int(graph_left + (t / max_t) * (graph_right - graph_left))

    def strain_to_y(s, max_s=25):
        return int(graph_bottom - (s / max_s) * (graph_bottom - graph_top))

    curves = [
        # Curve 1: Fast creep (200MPa) - fails around t=60
        [(0, 0), (5, 2), (10, 4), (20, 8), (30, 12), (40, 16), (50, 20), (55, 22)],
        # Curve 2: Medium-fast creep (150MPa) - fails around t=100
        [(0, 0), (10, 2), (20, 4), (40, 7), (60, 10), (80, 14), (90, 18), (95, 21)],
        # Curve 3: Medium creep (100MPa) - goes to ~500h
        [(0, 0), (50, 1), (100, 2), (200, 3), (300, 4), (400, 5), (500, 6)],
        # Curve 4: Slow creep (80MPa) - goes to ~700h
        [(0, 0), (100, 0.5), (200, 1), (400, 2), (600, 3), (700, 4)],
    ]

    print("Creating realistic creep curve test image...")
    print(f"Expected markers per curve: {[len(c) for c in curves]}")
    print(f"Total expected markers in graph: {sum(len(c) for c in curves)}")

    # Draw curves with markers
    for curve_idx, (curve_data, marker_func) in enumerate(zip(curves, marker_funcs)):
        prev_pt = None
        for t, s in curve_data:
            x = time_to_x(t)
            y = strain_to_y(s)
            pt = (x, y)

            # Draw connecting line first (so marker is on top)
            if prev_pt is not None:
                cv2.line(image, prev_pt, pt, (0, 0, 0), 1)

            # Draw marker
            marker_func(image, pt)
            prev_pt = pt

    # Draw legend (upper right)
    legend_x = w - 70
    legend_y_start = 30
    legend_labels = ["800°C-200MPa", "800°C-150MPa", "800°C-100MPa", "800°C-80MPa"]

    for i, (marker_func, label) in enumerate(zip(marker_funcs, legend_labels)):
        y = legend_y_start + i * 20
        # Draw marker
        marker_func(image, (legend_x - 30, y))
        # Draw line
        cv2.line(image, (legend_x - 20, y), (legend_x, y), (0, 0, 0), 1)
        # Draw label (small text)
        cv2.putText(image, label, (legend_x + 5, y + 3),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 0, 0), 1)

    return image, curves, marker_names


def test_detection_methods(image, expected_total, exclude_zone=None):
    """Test different detection methods."""
    results = {}

    # Preprocess
    binary = preprocess_image(image, kernel_size=5)

    # Method 1: Skeleton-based (new method)
    print("\n--- Method 1: Skeleton-based line removal ---")
    detector1 = MarkerDetector(min_area=20, max_area=400, kernel_size=5,
                               use_skeleton_removal=True)
    markers1 = detector1.detect(binary, image)

    if exclude_zone:
        markers1 = [m for m in markers1
                   if not (exclude_zone[0] <= m['cx'] <= exclude_zone[2] and
                          exclude_zone[1] <= m['cy'] <= exclude_zone[3])]

    print(f"Detected: {len(markers1)} markers (expected: {expected_total})")
    results['skeleton'] = markers1

    # Method 2: Traditional morphological opening
    print("\n--- Method 2: Morphological opening ---")
    detector2 = MarkerDetector(min_area=20, max_area=400, kernel_size=7,
                               use_skeleton_removal=False)
    markers2 = detector2.detect(binary, image)

    if exclude_zone:
        markers2 = [m for m in markers2
                   if not (exclude_zone[0] <= m['cx'] <= exclude_zone[2] and
                          exclude_zone[1] <= m['cy'] <= exclude_zone[3])]

    print(f"Detected: {len(markers2)} markers (expected: {expected_total})")
    results['morphology'] = markers2

    # Method 3: Distance transform peaks
    print("\n--- Method 3: Distance transform peaks ---")
    detector3 = MarkerDetector(min_area=20, max_area=400, kernel_size=5)
    markers3 = detector3.detect_by_distance_peaks(binary, min_distance=10, threshold=2.0)

    if exclude_zone:
        markers3 = [m for m in markers3
                   if not (exclude_zone[0] <= m['cx'] <= exclude_zone[2] and
                          exclude_zone[1] <= m['cy'] <= exclude_zone[3])]

    print(f"Detected: {len(markers3)} markers (expected: {expected_total})")
    results['distance_peaks'] = markers3

    # Method 4: Combined detection
    print("\n--- Method 4: Combined detection ---")
    detector4 = MarkerDetector(min_area=20, max_area=400, kernel_size=5,
                               use_skeleton_removal=False)
    markers4 = detector4.detect_combined(binary, image, min_marker_distance=10)

    if exclude_zone:
        markers4 = [m for m in markers4
                   if not (exclude_zone[0] <= m['cx'] <= exclude_zone[2] and
                          exclude_zone[1] <= m['cy'] <= exclude_zone[3])]

    print(f"Detected: {len(markers4)} markers (expected: {expected_total})")
    results['combined'] = markers4

    return results


def visualize_results(image, markers, output_path, title="Detection", use_curve_tracer=True):
    """Visualize detection results."""
    vis = image.copy()

    # Cluster markers - use CurveTracer for spatial grouping
    if len(markers) >= 4:
        if use_curve_tracer:
            tracer = CurveTracer(n_curves=4, max_gap_x=80, max_gap_y=40)
            clusters = tracer.trace_curves_by_y_bands(markers)
        else:
            clusterer = ShapeClusterer(n_clusters=4)
            clusters = clusterer.cluster(markers)
    else:
        clusters = {0: markers}

    colors = [(0, 0, 255), (0, 128, 0), (255, 0, 0), (0, 165, 255)]

    for cluster_id, points in clusters.items():
        color = colors[cluster_id % len(colors)]
        for p in points:
            cx, cy = int(p['cx']), int(p['cy'])
            cv2.circle(vis, (cx, cy), 8, color, 2)
            cv2.putText(vis, str(cluster_id), (cx + 10, cy),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    cv2.putText(vis, f"{title}: {len(markers)} markers, {len(clusters)} clusters",
               (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    cv2.imwrite(output_path, vis)
    print(f"Saved: {output_path}")

    return clusters


if __name__ == '__main__':
    # Create test image
    image, curves, marker_names = create_realistic_creep_image()

    # Save original
    test_dir = os.path.join(os.path.dirname(__file__), 'sample_images')
    os.makedirs(test_dir, exist_ok=True)

    original_path = os.path.join(test_dir, 'realistic_creep.png')
    cv2.imwrite(original_path, image)
    print(f"\nSaved test image: {original_path}")

    # Expected markers
    expected_graph = sum(len(c) for c in curves)  # In graph area
    expected_legend = 4  # In legend

    # Define exclude zone (legend area)
    h, w = image.shape[:2]
    exclude_zone = [w - 100, 0, w, 100]
    print(f"\nExclude zone (legend): {exclude_zone}")

    # Test detection
    results = test_detection_methods(image, expected_graph, exclude_zone)

    # Visualize best result
    for method_name, markers in results.items():
        output_path = os.path.join(test_dir, f'realistic_creep_{method_name}.png')
        clusters = visualize_results(image, markers, output_path, method_name)

        print(f"\n{method_name} clustering results:")
        for cid, pts in clusters.items():
            print(f"  Cluster {cid}: {len(pts)} points")

    # Check if we need alternative approach
    best_method = max(results.keys(), key=lambda k: len(results[k]))
    best_count = len(results[best_method])

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Expected markers in graph: {expected_graph}")
    print(f"Best detection ({best_method}): {best_count}")

    if best_count < expected_graph * 0.8:
        print("\n[WARNING] Detection count too low - alternative method needed")
    elif best_count > expected_graph * 1.2:
        print("\n[WARNING] Detection count too high - possible false positives")
    else:
        print("\n[OK] Detection count within acceptable range")
