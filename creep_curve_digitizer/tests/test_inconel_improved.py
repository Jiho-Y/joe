#!/usr/bin/env python3
"""
Improved Inconel 718 creep curve detection with better curve tracing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import pandas as pd
from src.processing.marker_detector import MarkerDetector


def trace_curves_by_continuity(markers, n_curves=3, max_y_gap=50):
    """
    Trace curves by following spatial continuity from left to right.
    Better handles curves that overlap in Y-space at the beginning.
    """
    if not markers:
        return {}

    # Sort all markers by X coordinate
    sorted_markers = sorted(markers, key=lambda m: m['cx'])

    # Find the rightmost X where we expect curves to be well-separated
    # For creep curves, they diverge over time
    x_coords = [m['cx'] for m in sorted_markers]
    x_max = max(x_coords)

    # Find markers in the rightmost region (last 20% of X range)
    x_range = x_max - min(x_coords)
    right_threshold = x_max - 0.2 * x_range

    right_markers = [m for m in sorted_markers if m['cx'] >= right_threshold]

    if len(right_markers) < n_curves:
        right_markers = sorted_markers[-n_curves:] if len(sorted_markers) >= n_curves else sorted_markers

    # Cluster right markers by Y to establish curve bands
    right_markers_sorted_y = sorted(right_markers, key=lambda m: m['cy'])

    # K-means on right markers to find Y bands
    if len(right_markers) >= n_curves:
        from sklearn.cluster import KMeans
        y_coords = np.array([m['cy'] for m in right_markers]).reshape(-1, 1)
        kmeans = KMeans(n_clusters=n_curves, random_state=42, n_init=10)
        kmeans.fit(y_coords)
        cluster_centers = sorted(kmeans.cluster_centers_.flatten())
    else:
        # Fallback: divide Y range evenly
        y_coords = [m['cy'] for m in sorted_markers]
        y_min, y_max = min(y_coords), max(y_coords)
        step = (y_max - y_min) / n_curves
        cluster_centers = [y_min + (i + 0.5) * step for i in range(n_curves)]

    # Initialize curves
    curves = {i: [] for i in range(n_curves)}

    # Process markers from right to left (reverse order)
    # This helps establish curve identity from the well-separated end
    for marker in reversed(sorted_markers):
        # Find nearest curve by Y-distance to curve's expected position
        best_curve = None
        min_dist = float('inf')

        for curve_id in range(n_curves):
            if curves[curve_id]:
                # Use the rightmost point in this curve for reference
                ref_point = min(curves[curve_id], key=lambda m: abs(m['cx'] - marker['cx']))
                y_expected = ref_point['cy']
            else:
                # Use cluster center
                y_expected = cluster_centers[curve_id]

            y_dist = abs(marker['cy'] - y_expected)
            if y_dist < min_dist and y_dist < max_y_gap:
                min_dist = y_dist
                best_curve = curve_id

        if best_curve is not None:
            marker['cluster'] = best_curve
            curves[best_curve].append(marker)

    # Sort each curve by X
    for cid in curves:
        curves[cid] = sorted(curves[cid], key=lambda m: m['cx'])

    # Reorder curves by average Y (top to bottom in image = higher to lower strain)
    curve_y_means = {}
    for cid, pts in curves.items():
        if pts:
            curve_y_means[cid] = np.mean([m['cy'] for m in pts])

    sorted_ids = sorted(curve_y_means.keys(), key=lambda k: curve_y_means[k])

    # Remap to new IDs
    new_curves = {}
    for new_id, old_id in enumerate(sorted_ids):
        for m in curves[old_id]:
            m['cluster'] = new_id
        new_curves[new_id] = curves[old_id]

    return new_curves


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    test_image_path = os.path.join(output_dir, 'sample_images', 'inconel718_synthetic.png')

    print("="*60)
    print("INCONEL 718 CREEP CURVE DIGITIZATION")
    print("="*60)

    # Load and process image
    img = cv2.imread(test_image_path)
    if img is None:
        print("Error: Image not found. Running create_inconel_test.py first...")
        os.system(f"python {os.path.join(output_dir, 'create_inconel_test.py')}")
        img = cv2.imread(test_image_path)

    h, w = img.shape[:2]
    print(f"Image: {test_image_path}")
    print(f"Size: {w}x{h}")

    # ROI
    roi_x1, roi_y1 = 55, 60
    roi_x2, roi_y2 = w - 20, h - 45
    roi_w = roi_x2 - roi_x1
    roi_h = roi_y2 - roi_y1

    roi_gray = cv2.cvtColor(img[roi_y1:roi_y2, roi_x1:roi_x2], cv2.COLOR_BGR2GRAY)
    roi_color = img[roi_y1:roi_y2, roi_x1:roi_x2].copy()

    # Binary threshold
    _, binary = cv2.threshold(roi_gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Detect markers
    detector = MarkerDetector(min_area=20, max_area=400, kernel_size=5, use_skeleton_removal=True)
    markers = detector.detect_combined(binary, roi_color, min_marker_distance=8)

    print(f"\nTotal markers detected: {len(markers)}")

    # Filter legend zone
    legend_zone = (0, 0, 80, 50)
    filtered = [m for m in markers if not (legend_zone[0] <= m['cx'] <= legend_zone[2] and
                                           legend_zone[1] <= m['cy'] <= legend_zone[3])]
    print(f"After legend filtering: {len(filtered)}")

    # Improved curve tracing
    curves = trace_curves_by_continuity(filtered, n_curves=3, max_y_gap=60)

    print("\nCurve detection results:")
    for cid, pts in sorted(curves.items()):
        print(f"  Curve {cid}: {len(pts)} points")

    # Calibration (from image)
    time_max = 18.0  # hours
    strain_max = 0.10  # mm/mm

    # Map curve IDs to stress levels
    # In the image: higher stress = faster creep = curve reaches higher strain first
    # Curve 0 (lowest Y mean) = highest strain region = 750 MPa
    # Curve 2 (highest Y mean) = lowest strain region = 625 MPa
    stress_labels = {0: '750 MPa', 1: '700 MPa', 2: '625 MPa'}

    # Build CSV data
    data_rows = []
    for cid, pts in curves.items():
        stress = stress_labels.get(cid, f'Curve {cid}')
        for m in pts:
            time_h = (m['cx'] / roi_w) * time_max
            strain = strain_max - (m['cy'] / roi_h) * strain_max

            data_rows.append({
                'Stress_MPa': stress,
                'Time_h': round(time_h, 2),
                'Strain_mm/mm': round(strain, 5),
                'Pixel_X': round(m['cx'] + roi_x1, 1),
                'Pixel_Y': round(m['cy'] + roi_y1, 1)
            })

    # Create DataFrame
    df = pd.DataFrame(data_rows)
    df = df.sort_values(['Stress_MPa', 'Time_h'])

    # Save to CSV
    csv_path = os.path.join(output_dir, 'inconel718_creep_data.csv')
    df.to_csv(csv_path, index=False)

    print("\n" + "="*60)
    print(f"CSV OUTPUT: {csv_path}")
    print("="*60)
    print(df.to_string(index=False))

    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY BY CURVE")
    print("="*60)
    for stress in ['750 MPa', '700 MPa', '625 MPa']:
        curve_data = df[df['Stress_MPa'] == stress]
        if len(curve_data) > 0:
            print(f"\n{stress}:")
            print(f"  Points: {len(curve_data)}")
            print(f"  Time range: {curve_data['Time_h'].min():.2f} - {curve_data['Time_h'].max():.2f} h")
            print(f"  Strain range: {curve_data['Strain_mm/mm'].min():.5f} - {curve_data['Strain_mm/mm'].max():.5f}")

    # Visualization
    colors = [(0, 0, 0), (0, 0, 255), (0, 200, 0)]  # Black, Red, Green
    for cid, pts in curves.items():
        color = colors[cid % 3]
        for m in pts:
            cx, cy = int(m['cx']), int(m['cy'])
            cv2.circle(roi_color, (cx, cy), 8, color, 2)
            cv2.circle(roi_color, (cx, cy), 8, (255, 255, 255), 1)

    vis_path = os.path.join(output_dir, 'sample_images', 'inconel718_final_result.png')
    cv2.imwrite(vis_path, roi_color)
    print(f"\nVisualization: {vis_path}")

    print("\n" + "="*60)
    print("DONE")
    print("="*60)

    return df


if __name__ == '__main__':
    main()
