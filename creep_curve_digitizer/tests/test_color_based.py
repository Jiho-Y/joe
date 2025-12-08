#!/usr/bin/env python3
"""
Color-based creep curve detection for Inconel 718 image.
Separates curves by marker color: Green (625 MPa), Red (700 MPa), Black (750 MPa)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import pandas as pd
from src.processing.marker_detector import MarkerDetector


def detect_by_color(image_path, output_csv):
    """
    Detect markers by color separation.
    """
    print("="*60)
    print("COLOR-BASED CREEP CURVE DETECTION")
    print("="*60)

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load {image_path}")
        return None

    h, w = img.shape[:2]
    print(f"Image: {w}x{h}")

    # Convert to HSV for color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Define ROI (graph area)
    roi_x1, roi_y1 = 55, 60
    roi_x2, roi_y2 = w - 20, h - 45
    roi_w = roi_x2 - roi_x1
    roi_h = roi_y2 - roi_y1

    hsv_roi = hsv[roi_y1:roi_y2, roi_x1:roi_x2]
    img_roi = img[roi_y1:roi_y2, roi_x1:roi_x2].copy()

    # Color ranges in HSV
    # Green: Hue ~60 (H: 35-85)
    # Red: Hue ~0 or ~180 (H: 0-10 or 170-180)
    # Black: Low Value (V: 0-50)
    color_configs = {
        '625 MPa': {
            'ranges': [
                {'lower': np.array([35, 80, 80]), 'upper': np.array([85, 255, 255])}  # Green
            ],
            'color_bgr': (0, 200, 0)
        },
        '700 MPa': {
            'ranges': [
                {'lower': np.array([0, 100, 100]), 'upper': np.array([10, 255, 255])},   # Red low
                {'lower': np.array([170, 100, 100]), 'upper': np.array([180, 255, 255])}  # Red high
            ],
            'color_bgr': (0, 0, 255)
        },
        '750 MPa': {
            'ranges': [
                {'lower': np.array([0, 0, 0]), 'upper': np.array([180, 100, 80])}  # Dark/Black
            ],
            'color_bgr': (0, 0, 0)
        }
    }

    detector = MarkerDetector(min_area=15, max_area=400, kernel_size=3)

    # Calibration
    time_max = 18.0
    strain_max = 0.10

    all_data = []
    vis_img = img_roi.copy()

    for stress_label, config in color_configs.items():
        # Create combined mask for this color
        combined_mask = np.zeros(hsv_roi.shape[:2], dtype=np.uint8)
        for r in config['ranges']:
            mask = cv2.inRange(hsv_roi, r['lower'], r['upper'])
            combined_mask = cv2.bitwise_or(combined_mask, mask)

        # Clean up mask
        kernel = np.ones((3, 3), np.uint8)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)

        # Detect markers using distance peaks (works well for filled circles)
        markers = detector.detect_by_distance_peaks(combined_mask, min_distance=8, threshold=2.0)

        # Also try blob detection
        blob_markers = detector.detect(combined_mask, img_roi)

        # Merge results
        all_markers = markers.copy()
        for bm in blob_markers:
            is_dup = False
            for m in all_markers:
                if np.sqrt((bm['cx'] - m['cx'])**2 + (bm['cy'] - m['cy'])**2) < 10:
                    is_dup = True
                    break
            if not is_dup:
                all_markers.append(bm)

        print(f"\n{stress_label}: {len(all_markers)} markers detected")

        # Sort by X coordinate
        all_markers = sorted(all_markers, key=lambda m: m['cx'])

        # Convert to real coordinates and add to data
        for m in all_markers:
            time_h = (m['cx'] / roi_w) * time_max
            strain = strain_max - (m['cy'] / roi_h) * strain_max

            all_data.append({
                'Stress_MPa': stress_label,
                'Time_h': round(time_h, 2),
                'Strain_mm/mm': round(strain, 5),
                'Pixel_X': round(m['cx'] + roi_x1, 1),
                'Pixel_Y': round(m['cy'] + roi_y1, 1)
            })

            # Draw on visualization
            cx, cy = int(m['cx']), int(m['cy'])
            cv2.circle(vis_img, (cx, cy), 8, config['color_bgr'], 2)
            cv2.circle(vis_img, (cx, cy), 8, (255, 255, 255), 1)

    # Create DataFrame
    df = pd.DataFrame(all_data)
    df = df.sort_values(['Stress_MPa', 'Time_h'])

    # Save CSV
    df.to_csv(output_csv, index=False)
    print(f"\n{'='*60}")
    print(f"CSV saved: {output_csv}")
    print("="*60)

    # Print CSV content
    print(df.to_string(index=False))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    for stress in ['750 MPa', '700 MPa', '625 MPa']:
        curve = df[df['Stress_MPa'] == stress]
        if len(curve) > 0:
            print(f"\n{stress}:")
            print(f"  Data points: {len(curve)}")
            print(f"  Time: {curve['Time_h'].min():.2f} - {curve['Time_h'].max():.2f} h")
            print(f"  Strain: {curve['Strain_mm/mm'].min():.5f} - {curve['Strain_mm/mm'].max():.5f}")

    # Save visualization
    vis_path = output_csv.replace('.csv', '_visualization.png')
    cv2.imwrite(vis_path, vis_img)
    print(f"\nVisualization: {vis_path}")

    return df


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    test_image = os.path.join(output_dir, 'sample_images', 'inconel718_synthetic.png')
    output_csv = os.path.join(output_dir, 'inconel718_color_detection.csv')

    if not os.path.exists(test_image):
        print("Creating test image first...")
        from create_inconel_test import create_inconel718_image
        create_inconel718_image(test_image)

    df = detect_by_color(test_image, output_csv)

    print("\n" + "="*60)
    print("COMPLETE - CSV READY FOR EXCEL")
    print("="*60)


if __name__ == '__main__':
    main()
