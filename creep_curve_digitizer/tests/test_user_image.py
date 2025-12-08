#!/usr/bin/env python3
"""
Test script for user-provided creep curve image.
Processes the image and exports results to CSV.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import pandas as pd
from src.processing.marker_detector import MarkerDetector
from src.processing.clustering import ShapeClusterer, CurveTracer


def process_creep_image(image_path, output_csv='creep_results.csv'):
    """
    Process a creep curve image and export marker positions to CSV.

    Args:
        image_path: Path to the creep curve image
        output_csv: Output CSV file path
    """
    print(f"Loading image: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load image from {image_path}")
        return None

    print(f"Image size: {img.shape[1]}x{img.shape[0]}")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Define ROI (graph area) - exclude axes labels and legend
    # For this image: approximately exclude left 50px (y-axis), bottom 30px (x-axis), top 60px (title/legend)
    h, w = gray.shape
    roi_x1, roi_y1 = int(w * 0.12), int(h * 0.15)  # Start after axis labels
    roi_x2, roi_y2 = int(w * 0.95), int(h * 0.85)  # End before axis labels

    print(f"ROI: ({roi_x1}, {roi_y1}) to ({roi_x2}, {roi_y2})")

    # Extract ROI
    roi_gray = gray[roi_y1:roi_y2, roi_x1:roi_x2]
    roi_color = img[roi_y1:roi_y2, roi_x1:roi_x2]

    # Threshold to binary (markers and lines are dark on light background)
    _, binary = cv2.threshold(roi_gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Also try adaptive threshold for better results
    binary_adaptive = cv2.adaptiveThreshold(
        roi_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # Use the cleaner binary
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((2,2), np.uint8))

    # Detect markers using combined method
    detector = MarkerDetector(
        min_area=20,
        max_area=400,
        kernel_size=5,
        use_skeleton_removal=True
    )

    print("\n--- Running Combined Detection ---")
    markers = detector.detect_combined(binary, roi_color, min_marker_distance=8)
    print(f"Detected {len(markers)} markers")

    if not markers:
        print("No markers detected. Trying with different threshold...")
        _, binary = cv2.threshold(roi_gray, 180, 255, cv2.THRESH_BINARY_INV)
        markers = detector.detect_combined(binary, roi_color, min_marker_distance=8)
        print(f"Detected {len(markers)} markers with adjusted threshold")

    if not markers:
        print("Still no markers. Trying adaptive threshold...")
        markers = detector.detect_combined(binary_adaptive, roi_color, min_marker_distance=8)
        print(f"Detected {len(markers)} markers with adaptive threshold")

    # Cluster markers into curves
    # For Inconel 718 image: 3 curves (625, 700, 750 MPa)
    n_curves = 3

    print(f"\n--- Clustering into {n_curves} curves ---")

    # Try Y-band clustering (more reliable for this type of chart)
    tracer = CurveTracer(n_curves=n_curves, max_gap_x=50, max_gap_y=30)
    clusters = tracer.trace_curves_by_y_bands(markers)

    print("Clustering results:")
    for cid, pts in sorted(clusters.items()):
        print(f"  Curve {cid}: {len(pts)} points")

    # Prepare data for CSV
    # Assuming calibration: image shows time 0-18h, strain 0.00-0.10
    # ROI pixel coordinates need to be mapped to real values
    roi_w = roi_x2 - roi_x1
    roi_h = roi_y2 - roi_y1

    # Calibration (approximate from image labels)
    time_min, time_max = 0, 18  # hours
    strain_min, strain_max = 0.00, 0.10  # mm/mm

    data_rows = []
    curve_names = {0: '625 MPa', 1: '700 MPa', 2: '750 MPa'}

    for curve_id, curve_markers in sorted(clusters.items()):
        curve_name = curve_names.get(curve_id, f'Curve {curve_id}')

        for m in curve_markers:
            # Convert pixel to real coordinates
            # X: pixel 0 -> time_min, pixel roi_w -> time_max
            # Y: pixel 0 -> strain_max (top), pixel roi_h -> strain_min (bottom)
            time_h = time_min + (m['cx'] / roi_w) * (time_max - time_min)
            strain = strain_max - (m['cy'] / roi_h) * (strain_max - strain_min)

            data_rows.append({
                'Curve': curve_name,
                'Curve_ID': curve_id,
                'Time_h': round(time_h, 2),
                'Strain_mm_mm': round(strain, 5),
                'Pixel_X': round(m['cx'] + roi_x1, 1),
                'Pixel_Y': round(m['cy'] + roi_y1, 1)
            })

    # Create DataFrame and sort
    df = pd.DataFrame(data_rows)
    df = df.sort_values(['Curve_ID', 'Time_h'])

    # Save to CSV
    df.to_csv(output_csv, index=False)
    print(f"\n--- Results saved to {output_csv} ---")
    print(f"Total data points: {len(df)}")

    # Also print summary
    print("\n" + "="*60)
    print("CSV PREVIEW:")
    print("="*60)
    print(df.to_string(index=False))

    # Create visualization
    vis_img = roi_color.copy()
    colors = [(0, 255, 0), (0, 0, 255), (0, 0, 0)]  # Green, Red, Black for 625, 700, 750 MPa

    for curve_id, curve_markers in clusters.items():
        color = colors[curve_id % len(colors)]
        for m in curve_markers:
            cx, cy = int(m['cx']), int(m['cy'])
            cv2.circle(vis_img, (cx, cy), 8, color, 2)
            cv2.putText(vis_img, str(curve_id), (cx-3, cy+3),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)

    vis_path = output_csv.replace('.csv', '_visualization.png')
    cv2.imwrite(vis_path, vis_img)
    print(f"\nVisualization saved to: {vis_path}")

    return df


def process_from_color_separation(image_path, output_csv='creep_results_color.csv'):
    """
    Alternative method: Detect markers by color separation.
    The image has green (625 MPa), red (700 MPa), and black (750 MPa) markers.
    """
    print(f"\n{'='*60}")
    print("COLOR-BASED DETECTION")
    print('='*60)

    img = cv2.imread(image_path)
    if img is None:
        return None

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    h, w = img.shape[:2]
    roi_x1, roi_y1 = int(w * 0.12), int(h * 0.15)
    roi_x2, roi_y2 = int(w * 0.95), int(h * 0.85)

    hsv_roi = hsv[roi_y1:roi_y2, roi_x1:roi_x2]
    img_roi = img[roi_y1:roi_y2, roi_x1:roi_x2]

    roi_w = roi_x2 - roi_x1
    roi_h = roi_y2 - roi_y1

    # Define color ranges
    color_ranges = {
        '625 MPa (Green)': {
            'lower': np.array([35, 50, 50]),
            'upper': np.array([85, 255, 255])
        },
        '700 MPa (Red)': {
            'lower': np.array([0, 100, 100]),
            'upper': np.array([10, 255, 255])
        },
        '750 MPa (Black)': {
            'lower': np.array([0, 0, 0]),
            'upper': np.array([180, 255, 50])
        }
    }

    detector = MarkerDetector(min_area=15, max_area=300, kernel_size=3)

    data_rows = []
    time_min, time_max = 0, 18
    strain_min, strain_max = 0.00, 0.10

    curve_id = 0
    for curve_name, ranges in color_ranges.items():
        mask = cv2.inRange(hsv_roi, ranges['lower'], ranges['upper'])
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8))

        markers = detector.detect_by_distance_peaks(mask, min_distance=8, threshold=1.5)

        print(f"{curve_name}: {len(markers)} markers detected")

        for m in markers:
            time_h = time_min + (m['cx'] / roi_w) * (time_max - time_min)
            strain = strain_max - (m['cy'] / roi_h) * (strain_max - strain_min)

            data_rows.append({
                'Curve': curve_name.split(' (')[0],
                'Curve_ID': curve_id,
                'Time_h': round(time_h, 2),
                'Strain_mm_mm': round(strain, 5),
                'Pixel_X': round(m['cx'] + roi_x1, 1),
                'Pixel_Y': round(m['cy'] + roi_y1, 1)
            })

        curve_id += 1

    df = pd.DataFrame(data_rows)
    df = df.sort_values(['Curve_ID', 'Time_h'])
    df.to_csv(output_csv, index=False)

    print(f"\nColor-based results saved to {output_csv}")
    print(f"Total data points: {len(df)}")

    return df


if __name__ == '__main__':
    # Check for command line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Default test image path
        image_path = os.path.join(
            os.path.dirname(__file__),
            'sample_images',
            'inconel718_creep.png'
        )

    output_dir = os.path.dirname(os.path.abspath(__file__))

    # Method 1: Combined detection with clustering
    csv_path = os.path.join(output_dir, 'inconel718_results.csv')
    df1 = process_creep_image(image_path, csv_path)

    # Method 2: Color-based separation
    csv_color_path = os.path.join(output_dir, 'inconel718_results_color.csv')
    df2 = process_from_color_separation(image_path, csv_color_path)

    print("\n" + "="*60)
    print("DONE")
    print("="*60)
