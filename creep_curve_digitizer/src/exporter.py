"""
Data export functionality for CSV and JSON.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from .calibration import Calibration


class Exporter:
    """
    Handles export of curve data to CSV and calibration to JSON.
    """

    @staticmethod
    def export_curves_csv(
        output_dir: str,
        curves: Dict[int, List[Dict]],
        calibration: Calibration,
        metadata: Dict
    ) -> List[str]:
        """
        Export each curve to a separate CSV file.

        Args:
            output_dir: Output directory path
            curves: Dictionary of cluster_id -> list of points
            calibration: Calibration object for coordinate transformation
            metadata: Metadata dictionary

        Returns:
            List of created file paths
        """
        created_files = []

        for curve_id, points in curves.items():
            if not points:
                continue

            # Create filename
            base_name = metadata.get('material', 'curve').replace(' ', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{base_name}_curve{curve_id + 1}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)

            # Prepare data
            x_data = []
            y_data = []

            for point in points:
                px, py = point['cx'], point['cy']

                if calibration.is_calibrated():
                    rx, ry = calibration.pixel_to_real(px, py)
                    x_data.append(rx)
                    y_data.append(ry)
                else:
                    x_data.append(px)
                    y_data.append(py)

            # Create DataFrame
            df = pd.DataFrame({
                'time': x_data,
                'strain': y_data
            })

            # Sort by x (time)
            df = df.sort_values('time').reset_index(drop=True)

            # Write CSV with metadata header
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write metadata as comments
                f.write(f"# source: {metadata.get('source', '')}\n")
                f.write(f"# figure: {metadata.get('figure', '')}\n")
                f.write(f"# material: {metadata.get('material', '')}\n")
                f.write(f"# temperature_C: {metadata.get('temperature_C', '')}\n")
                f.write(f"# stress_MPa: {metadata.get('stress_MPa', '')}\n")
                f.write(f"# x_unit: {metadata.get('x_unit', '')}\n")
                f.write(f"# y_unit: {metadata.get('y_unit', '')}\n")
                f.write(f"# curve_id: {curve_id + 1}\n")
                f.write(f"# extraction_date: {metadata.get('extraction_date', '')}\n")
                f.write(f"# extraction_tool: {metadata.get('extraction_tool', '')}\n")
                if metadata.get('notes'):
                    # Handle multi-line notes
                    notes = metadata['notes'].replace('\n', ' ')
                    f.write(f"# notes: {notes}\n")

                # Write data
                df.to_csv(f, index=False)

            created_files.append(filepath)

        return created_files

    @staticmethod
    def save_calibration(
        filepath: str,
        image_file: str,
        roi: Optional[List[int]],
        calibration: Calibration,
        mode: str,
        parameters: Dict
    ) -> bool:
        """
        Save calibration data to JSON file.

        Args:
            filepath: Output JSON file path
            image_file: Path to the source image
            roi: ROI coordinates [x1, y1, x2, y2]
            calibration: Calibration object
            mode: Detection mode ('A', 'B1', or 'B3')
            parameters: Detection parameters

        Returns:
            True if successful
        """
        data = {
            'image_file': image_file,
            'roi': roi,
            'mode': mode,
            'parameters': parameters,
            'saved_at': datetime.now().isoformat()
        }

        # Add calibration data
        data.update(calibration.to_dict())

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving calibration: {e}")
            return False

    @staticmethod
    def load_calibration(filepath: str) -> Optional[Dict]:
        """
        Load calibration data from JSON file.

        Args:
            filepath: JSON file path

        Returns:
            Calibration dictionary or None if failed
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return None

    @staticmethod
    def export_all_curves_single_csv(
        filepath: str,
        curves: Dict[int, List[Dict]],
        calibration: Calibration,
        metadata: Dict
    ) -> bool:
        """
        Export all curves to a single CSV with curve_id column.

        Args:
            filepath: Output CSV file path
            curves: Dictionary of cluster_id -> list of points
            calibration: Calibration object
            metadata: Metadata dictionary

        Returns:
            True if successful
        """
        all_data = []

        for curve_id, points in curves.items():
            for point in points:
                px, py = point['cx'], point['cy']

                if calibration.is_calibrated():
                    rx, ry = calibration.pixel_to_real(px, py)
                else:
                    rx, ry = px, py

                all_data.append({
                    'curve_id': curve_id + 1,
                    'time': rx,
                    'strain': ry,
                    'pixel_x': px,
                    'pixel_y': py
                })

        if not all_data:
            return False

        df = pd.DataFrame(all_data)
        df = df.sort_values(['curve_id', 'time']).reset_index(drop=True)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write metadata
                for key, value in metadata.items():
                    if key != 'notes':
                        f.write(f"# {key}: {value}\n")
                if metadata.get('notes'):
                    notes = metadata['notes'].replace('\n', ' ')
                    f.write(f"# notes: {notes}\n")

                df.to_csv(f, index=False)
            return True
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False

    @staticmethod
    def export_raw_points(
        filepath: str,
        points: List[Dict],
        include_features: bool = False
    ) -> bool:
        """
        Export raw detected points with all features.

        Args:
            filepath: Output CSV file path
            points: List of point dictionaries
            include_features: Include shape features in output

        Returns:
            True if successful
        """
        if not points:
            return False

        if include_features:
            columns = [
                'cx', 'cy', 'area', 'circularity', 'solidity',
                'aspect_ratio', 'extent', 'cluster'
            ]
        else:
            columns = ['cx', 'cy', 'cluster']

        data = []
        for point in points:
            row = {col: point.get(col, '') for col in columns}
            data.append(row)

        df = pd.DataFrame(data)

        try:
            df.to_csv(filepath, index=False)
            return True
        except Exception as e:
            print(f"Error exporting raw points: {e}")
            return False
