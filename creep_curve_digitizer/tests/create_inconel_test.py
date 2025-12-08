#!/usr/bin/env python3
"""
Create a synthetic Inconel 718 creep curve image matching the user's sample,
then process it and export results to CSV.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import pandas as pd
from src.processing.marker_detector import MarkerDetector
from src.processing.clustering import CurveTracer


def create_inconel718_image(output_path):
    """
    Create a synthetic image matching the Inconel 718 creep curves.
    Based on the image provided:
    - 700°C temperature
    - 3 stress levels: 625 MPa (green), 700 MPa (red), 750 MPa (black)
    - Time range: 0-18 hours
    - Strain range: 0.00-0.10 mm/mm
    """
    # Image dimensions
    width, height = 450, 350
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Graph area
    margin_left = 55
    margin_right = 20
    margin_top = 60
    margin_bottom = 45

    graph_x1 = margin_left
    graph_y1 = margin_top
    graph_x2 = width - margin_right
    graph_y2 = height - margin_bottom

    graph_w = graph_x2 - graph_x1
    graph_h = graph_y2 - graph_y1

    # Draw axes
    cv2.rectangle(img, (graph_x1, graph_y1), (graph_x2, graph_y2), (0, 0, 0), 1)

    # Calibration
    time_max = 18.0  # hours
    strain_max = 0.10  # mm/mm

    def to_pixel(time_h, strain):
        px = graph_x1 + (time_h / time_max) * graph_w
        py = graph_y2 - (strain / strain_max) * graph_h
        return int(px), int(py)

    # Title
    cv2.putText(img, "Inconel 718", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "700 C", (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # Axis labels
    cv2.putText(img, "time [h]", (width//2 - 30, height - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    # Y-axis label (rotated would need special handling, simplified here)
    cv2.putText(img, "strain", (5, height//2 - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
    cv2.putText(img, "[mm/mm]", (2, height//2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

    # X-axis tick marks and labels
    for t in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]:
        px, _ = to_pixel(t, 0)
        cv2.line(img, (px, graph_y2), (px, graph_y2 + 5), (0, 0, 0), 1)
        cv2.putText(img, str(t), (px - 5, graph_y2 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

    # Y-axis tick marks and labels
    for s in [0.00, 0.02, 0.04, 0.06, 0.08, 0.10]:
        _, py = to_pixel(0, s)
        cv2.line(img, (graph_x1 - 5, py), (graph_x1, py), (0, 0, 0), 1)
        cv2.putText(img, f"{s:.2f}", (graph_x1 - 35, py + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

    # Creep curve data (realistic approximation based on typical Inconel 718 behavior)
    # Primary creep (rapid initial), secondary (steady-state), tertiary (accelerating to failure)

    curves_data = {
        '625 MPa': {
            'color': (0, 200, 0),  # Green
            'times': [0, 0.5, 1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18],
            'strains': [0.002, 0.004, 0.005, 0.007, 0.008, 0.009, 0.011, 0.013, 0.015, 0.017, 0.019, 0.021, 0.024]
        },
        '700 MPa': {
            'color': (0, 0, 200),  # Red
            'times': [0, 0.3, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5],
            'strains': [0.003, 0.008, 0.012, 0.020, 0.028, 0.035, 0.043, 0.052, 0.062, 0.074, 0.088, 0.100]
        },
        '750 MPa': {
            'color': (0, 0, 0),  # Black
            'times': [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6],
            'strains': [0.004, 0.012, 0.022, 0.034, 0.048, 0.064, 0.078, 0.092, 0.100]
        }
    }

    # Store ground truth data
    ground_truth = []

    # Draw legend
    legend_y = margin_top + 5
    for i, (name, data) in enumerate(curves_data.items()):
        # Legend marker
        lx = graph_x1 + 10
        ly = legend_y + i * 15
        cv2.circle(img, (lx, ly), 4, data['color'], -1)
        cv2.putText(img, name, (lx + 10, ly + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

    # Draw curves and markers
    for curve_name, data in curves_data.items():
        color = data['color']
        times = data['times']
        strains = data['strains']

        # Draw connecting lines
        pts = [to_pixel(t, s) for t, s in zip(times, strains)]
        for i in range(len(pts) - 1):
            cv2.line(img, pts[i], pts[i+1], color, 1)

        # Draw markers (circles)
        for t, s in zip(times, strains):
            px, py = to_pixel(t, s)
            cv2.circle(img, (px, py), 5, color, -1)
            cv2.circle(img, (px, py), 5, (0, 0, 0), 1)

            ground_truth.append({
                'Curve': curve_name,
                'Time_h': t,
                'Strain_mm_mm': s,
                'Pixel_X': px,
                'Pixel_Y': py
            })

    cv2.imwrite(output_path, img)
    print(f"Created test image: {output_path}")

    return img, ground_truth, (graph_x1, graph_y1, graph_x2, graph_y2)


def process_and_export(image_path, output_csv):
    """Process the creep image and export to CSV."""
    print(f"\n{'='*60}")
    print("MARKER DETECTION AND CSV EXPORT")
    print('='*60)

    img = cv2.imread(image_path)
    if img is None:
        print("Error loading image")
        return None

    h, w = img.shape[:2]
    print(f"Image size: {w}x{h}")

    # ROI (graph area) - adjust based on image
    roi_x1, roi_y1 = 55, 60
    roi_x2, roi_y2 = w - 20, h - 45

    roi_gray = cv2.cvtColor(img[roi_y1:roi_y2, roi_x1:roi_x2], cv2.COLOR_BGR2GRAY)
    roi_color = img[roi_y1:roi_y2, roi_x1:roi_x2]

    # Binary threshold
    _, binary = cv2.threshold(roi_gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Detect markers
    detector = MarkerDetector(min_area=20, max_area=400, kernel_size=5, use_skeleton_removal=True)
    markers = detector.detect_combined(binary, roi_color, min_marker_distance=8)

    print(f"\nDetected {len(markers)} markers")

    # Exclude legend zone (top-left of graph)
    legend_zone = (0, 0, 80, 50)  # x1, y1, x2, y2 in ROI coordinates
    filtered_markers = []
    for m in markers:
        if not (legend_zone[0] <= m['cx'] <= legend_zone[2] and
                legend_zone[1] <= m['cy'] <= legend_zone[3]):
            filtered_markers.append(m)

    print(f"After legend filtering: {len(filtered_markers)} markers")

    # Cluster into 3 curves
    tracer = CurveTracer(n_curves=3, max_gap_x=80, max_gap_y=40)
    clusters = tracer.trace_curves_by_y_bands(filtered_markers)

    # Calibration
    roi_w = roi_x2 - roi_x1
    roi_h = roi_y2 - roi_y1
    time_max = 18.0
    strain_max = 0.10

    # Map clusters to stress levels (by average Y position - higher stress = faster creep = higher strain at same time)
    cluster_y_means = {}
    for cid, pts in clusters.items():
        if pts:
            cluster_y_means[cid] = np.mean([m['cy'] for m in pts])

    # Sort by Y mean (lower Y = higher strain at chart = higher stress)
    sorted_clusters = sorted(cluster_y_means.keys(), key=lambda k: cluster_y_means[k])
    stress_map = {sorted_clusters[i]: ['750 MPa', '700 MPa', '625 MPa'][i] if i < 3 else f'Curve {i}'
                  for i in range(len(sorted_clusters))}

    data_rows = []
    for cid, pts in clusters.items():
        curve_name = stress_map.get(cid, f'Curve {cid}')
        for m in pts:
            time_h = (m['cx'] / roi_w) * time_max
            strain = strain_max - (m['cy'] / roi_h) * strain_max

            data_rows.append({
                'Curve': curve_name,
                'Curve_ID': cid,
                'Time_h': round(time_h, 2),
                'Strain_mm_mm': round(strain, 5),
                'Pixel_X': round(m['cx'] + roi_x1, 1),
                'Pixel_Y': round(m['cy'] + roi_y1, 1)
            })

    df = pd.DataFrame(data_rows)
    df = df.sort_values(['Curve', 'Time_h'])
    df.to_csv(output_csv, index=False)

    print(f"\nResults saved to: {output_csv}")
    print(f"Total data points: {len(df)}")

    return df, clusters, roi_color


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))

    # Create synthetic test image
    test_image_path = os.path.join(output_dir, 'sample_images', 'inconel718_synthetic.png')
    os.makedirs(os.path.dirname(test_image_path), exist_ok=True)

    print("Creating synthetic Inconel 718 creep curve image...")
    img, ground_truth, roi_bounds = create_inconel718_image(test_image_path)

    # Save ground truth
    gt_df = pd.DataFrame(ground_truth)
    gt_csv = os.path.join(output_dir, 'inconel718_ground_truth.csv')
    gt_df.to_csv(gt_csv, index=False)
    print(f"Ground truth saved: {gt_csv}")

    # Process the image
    output_csv = os.path.join(output_dir, 'inconel718_detected.csv')
    df, clusters, roi_color = process_and_export(test_image_path, output_csv)

    # Print comparison
    print("\n" + "="*60)
    print("GROUND TRUTH DATA")
    print("="*60)
    print(gt_df.to_string(index=False))

    print("\n" + "="*60)
    print("DETECTED DATA")
    print("="*60)
    print(df.to_string(index=False))

    # Create visualization
    vis_img = roi_color.copy()
    colors_vis = [(0, 0, 0), (0, 0, 255), (0, 200, 0)]  # Black, Red, Green for 750, 700, 625

    for cid, pts in clusters.items():
        color = colors_vis[cid % len(colors_vis)]
        for m in pts:
            cx, cy = int(m['cx']), int(m['cy'])
            cv2.circle(vis_img, (cx, cy), 10, color, 2)

    vis_path = os.path.join(output_dir, 'sample_images', 'inconel718_detection_result.png')
    cv2.imwrite(vis_path, vis_img)
    print(f"\nVisualization saved: {vis_path}")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()
