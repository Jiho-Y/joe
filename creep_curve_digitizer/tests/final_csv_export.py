#!/usr/bin/env python3
"""
Final CSV export with data cleaning for Inconel 718 creep curves.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import pandas as pd
from src.processing.marker_detector import MarkerDetector


def clean_creep_data(df):
    """
    Clean creep curve data by removing outliers.
    Creep curves should show monotonically increasing strain over time.
    """
    cleaned_rows = []

    for stress in df['Stress_MPa'].unique():
        curve = df[df['Stress_MPa'] == stress].sort_values('Time_h')

        # Filter: strain should generally increase with time (allow small decreases for noise)
        prev_strain = 0
        prev_time = -1

        for _, row in curve.iterrows():
            # Skip if time is basically same as previous (duplicate)
            if abs(row['Time_h'] - prev_time) < 0.3:
                continue

            # For early points, strain should be low
            if row['Time_h'] < 1.0 and row['Strain_mm/mm'] > 0.05:
                continue  # Skip outlier

            # Strain should not decrease significantly
            if row['Strain_mm/mm'] < prev_strain - 0.01:
                continue

            cleaned_rows.append(row)
            prev_strain = row['Strain_mm/mm']
            prev_time = row['Time_h']

    return pd.DataFrame(cleaned_rows)


def process_and_export():
    """Main processing function."""
    print("="*60)
    print("INCONEL 718 CREEP CURVE DATA EXTRACTION")
    print("="*60)

    output_dir = os.path.dirname(os.path.abspath(__file__))
    test_image = os.path.join(output_dir, 'sample_images', 'inconel718_synthetic.png')

    if not os.path.exists(test_image):
        print("Creating test image...")
        from create_inconel_test import create_inconel718_image
        create_inconel718_image(test_image)

    img = cv2.imread(test_image)
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ROI
    roi_x1, roi_y1 = 55, 60
    roi_x2, roi_y2 = w - 20, h - 45
    roi_w = roi_x2 - roi_x1
    roi_h = roi_y2 - roi_y1

    hsv_roi = hsv[roi_y1:roi_y2, roi_x1:roi_x2]
    img_roi = img[roi_y1:roi_y2, roi_x1:roi_x2].copy()

    # Calibration
    time_max = 18.0
    strain_max = 0.10

    # Color definitions for each stress level
    colors = {
        '625 MPa': {'h_range': (35, 85), 's_min': 80, 'v_min': 80},  # Green
        '700 MPa': {'h_range': [(0, 10), (170, 180)], 's_min': 100, 'v_min': 100},  # Red
        '750 MPa': {'h_range': (0, 180), 's_max': 100, 'v_max': 80}  # Black
    }

    detector = MarkerDetector(min_area=20, max_area=350, kernel_size=3)
    all_data = []

    for stress, params in colors.items():
        # Create mask based on color parameters
        if stress == '625 MPa':
            # Green
            mask = cv2.inRange(hsv_roi,
                              np.array([params['h_range'][0], params['s_min'], params['v_min']]),
                              np.array([params['h_range'][1], 255, 255]))
        elif stress == '700 MPa':
            # Red (two ranges)
            mask1 = cv2.inRange(hsv_roi,
                               np.array([params['h_range'][0][0], params['s_min'], params['v_min']]),
                               np.array([params['h_range'][0][1], 255, 255]))
            mask2 = cv2.inRange(hsv_roi,
                               np.array([params['h_range'][1][0], params['s_min'], params['v_min']]),
                               np.array([params['h_range'][1][1], 255, 255]))
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            # Black
            mask = cv2.inRange(hsv_roi,
                              np.array([0, 0, 0]),
                              np.array([180, params['s_max'], params['v_max']]))

        # Clean mask
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Detect markers
        markers = detector.detect_by_distance_peaks(mask, min_distance=10, threshold=2.5)

        for m in markers:
            time_h = (m['cx'] / roi_w) * time_max
            strain = strain_max - (m['cy'] / roi_h) * strain_max

            all_data.append({
                'Stress_MPa': stress,
                'Time_h': round(time_h, 2),
                'Strain_mm/mm': round(strain, 5)
            })

    # Create DataFrame and clean
    df = pd.DataFrame(all_data)
    df = clean_creep_data(df)
    df = df.sort_values(['Stress_MPa', 'Time_h']).reset_index(drop=True)

    # Export to CSV
    csv_path = os.path.join(output_dir, 'Inconel718_CreepData.csv')
    df.to_csv(csv_path, index=False)

    print(f"\n{'='*60}")
    print("FINAL CSV OUTPUT")
    print(f"File: {csv_path}")
    print("="*60)
    print(df.to_string(index=False))

    # Summary table
    print(f"\n{'='*60}")
    print("DATA SUMMARY")
    print("="*60)
    print(f"{'Stress':<12} {'Points':<8} {'Time Range (h)':<18} {'Strain Range':<20}")
    print("-"*60)

    for stress in ['750 MPa', '700 MPa', '625 MPa']:
        curve = df[df['Stress_MPa'] == stress]
        if len(curve) > 0:
            time_range = f"{curve['Time_h'].min():.1f} - {curve['Time_h'].max():.1f}"
            strain_range = f"{curve['Strain_mm/mm'].min():.4f} - {curve['Strain_mm/mm'].max():.4f}"
            print(f"{stress:<12} {len(curve):<8} {time_range:<18} {strain_range:<20}")

    print(f"\nTotal data points: {len(df)}")

    return df, csv_path


if __name__ == '__main__':
    df, csv_path = process_and_export()
    print(f"\n✓ CSV ready: {csv_path}")
