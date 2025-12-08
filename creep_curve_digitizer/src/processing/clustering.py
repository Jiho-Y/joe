"""
Shape clustering for grouping markers by their visual appearance.
"""

import numpy as np
from typing import List, Dict, Optional
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster


class ShapeClusterer:
    """
    Clusters markers by their shape features to separate different
    curve markers (e.g., triangle, circle, square, diamond).
    """

    def __init__(
        self,
        n_clusters: int = 4,
        method: str = 'kmeans',
        feature_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize the clusterer.

        Args:
            n_clusters: Number of clusters (marker types)
            method: Clustering method ('kmeans' or 'hierarchical')
            feature_weights: Optional weights for features
        """
        self.n_clusters = n_clusters
        self.method = method
        self.feature_weights = feature_weights or {
            'circularity': 1.0,
            'solidity': 1.0,
            'hu0': 0.5,
            'hu1': 0.5
        }
        self.scaler = StandardScaler()
        self.model = None

    def cluster(self, markers: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Cluster markers by shape features.

        Args:
            markers: List of marker dictionaries with shape features

        Returns:
            Dictionary mapping cluster ID to list of markers
        """
        if not markers:
            return {}

        if len(markers) < self.n_clusters:
            # Not enough markers for requested clusters
            # Assign all to cluster 0
            for marker in markers:
                marker['cluster'] = 0
            return {0: markers}

        # Extract feature vectors
        features = self._extract_feature_vectors(markers)

        # Normalize features
        features_normalized = self.scaler.fit_transform(features)

        # Perform clustering
        if self.method == 'kmeans':
            labels = self._kmeans_cluster(features_normalized)
        else:
            labels = self._hierarchical_cluster(features_normalized)

        # Organize markers by cluster
        clusters = {}
        for i, marker in enumerate(markers):
            cluster_id = int(labels[i])
            marker['cluster'] = cluster_id

            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(marker)

        # Sort points within each cluster by x-coordinate
        for cluster_id in clusters:
            clusters[cluster_id] = sorted(
                clusters[cluster_id],
                key=lambda m: m['cx']
            )

        return clusters

    def _extract_feature_vectors(self, markers: List[Dict]) -> np.ndarray:
        """
        Extract feature vectors for clustering.

        Features used:
        - Circularity (1.0 for circle, less for other shapes)
        - Solidity (ratio of area to convex hull area)
        - First two Hu moments (shape descriptors)

        Args:
            markers: List of marker dictionaries

        Returns:
            Feature matrix (n_markers x n_features)
        """
        features = []
        for marker in markers:
            hu = marker.get('hu_moments', [0] * 7)
            feature_vec = [
                marker['circularity'] * self.feature_weights['circularity'],
                marker['solidity'] * self.feature_weights['solidity'],
                -np.sign(hu[0]) * np.log10(abs(hu[0]) + 1e-10) * self.feature_weights['hu0'],
                -np.sign(hu[1]) * np.log10(abs(hu[1]) + 1e-10) * self.feature_weights['hu1']
            ]
            features.append(feature_vec)

        return np.array(features)

    def _kmeans_cluster(self, features: np.ndarray) -> np.ndarray:
        """
        Perform K-means clustering.

        Args:
            features: Normalized feature matrix

        Returns:
            Cluster labels
        """
        self.model = KMeans(
            n_clusters=self.n_clusters,
            random_state=42,
            n_init=10
        )
        return self.model.fit_predict(features)

    def _hierarchical_cluster(self, features: np.ndarray) -> np.ndarray:
        """
        Perform hierarchical clustering.

        Args:
            features: Normalized feature matrix

        Returns:
            Cluster labels
        """
        self.model = AgglomerativeClustering(
            n_clusters=self.n_clusters,
            linkage='ward'
        )
        return self.model.fit_predict(features)

    def auto_determine_clusters(
        self,
        markers: List[Dict],
        max_clusters: int = 8
    ) -> int:
        """
        Automatically determine optimal number of clusters using
        hierarchical clustering and dendrogram analysis.

        Args:
            markers: List of marker dictionaries
            max_clusters: Maximum number of clusters to consider

        Returns:
            Suggested number of clusters
        """
        if len(markers) < 2:
            return 1

        features = self._extract_feature_vectors(markers)
        features_normalized = self.scaler.fit_transform(features)

        # Compute linkage matrix
        Z = linkage(features_normalized, method='ward')

        # Use inconsistency or gap statistic to find optimal k
        # Simple heuristic: look for large jumps in distance
        distances = Z[:, 2]
        if len(distances) > 1:
            diffs = np.diff(distances)
            # Find significant jumps
            threshold = np.mean(diffs) + np.std(diffs)
            jumps = np.where(diffs > threshold)[0]

            if len(jumps) > 0:
                # Number of clusters = n_samples - position of first big jump
                suggested_k = len(markers) - jumps[0] - 1
                return max(1, min(suggested_k, max_clusters))

        return min(4, len(markers))  # Default to 4 or fewer

    def get_cluster_statistics(
        self,
        clusters: Dict[int, List[Dict]]
    ) -> Dict[int, Dict]:
        """
        Compute statistics for each cluster.

        Args:
            clusters: Dictionary of clustered markers

        Returns:
            Statistics for each cluster
        """
        stats = {}
        for cluster_id, markers in clusters.items():
            if not markers:
                continue

            circularities = [m['circularity'] for m in markers]
            solidities = [m['solidity'] for m in markers]
            areas = [m['area'] for m in markers]

            stats[cluster_id] = {
                'count': len(markers),
                'mean_circularity': np.mean(circularities),
                'std_circularity': np.std(circularities),
                'mean_solidity': np.mean(solidities),
                'std_solidity': np.std(solidities),
                'mean_area': np.mean(areas),
                'std_area': np.std(areas),
                'x_range': (
                    min(m['cx'] for m in markers),
                    max(m['cx'] for m in markers)
                ),
                'y_range': (
                    min(m['cy'] for m in markers),
                    max(m['cy'] for m in markers)
                )
            }

        return stats

    @staticmethod
    def merge_clusters(
        clusters: Dict[int, List[Dict]],
        cluster_a: int,
        cluster_b: int
    ) -> Dict[int, List[Dict]]:
        """
        Merge two clusters into one.

        Args:
            clusters: Dictionary of clustered markers
            cluster_a: First cluster ID (will be kept)
            cluster_b: Second cluster ID (will be merged into first)

        Returns:
            Updated clusters dictionary
        """
        if cluster_a not in clusters or cluster_b not in clusters:
            return clusters

        # Merge cluster_b into cluster_a
        for marker in clusters[cluster_b]:
            marker['cluster'] = cluster_a
            clusters[cluster_a].append(marker)

        # Remove cluster_b
        del clusters[cluster_b]

        # Re-sort by x
        clusters[cluster_a] = sorted(
            clusters[cluster_a],
            key=lambda m: m['cx']
        )

        return clusters


class CurveTracer:
    """
    Groups markers into curves based on spatial continuity.
    Better for cases where shape features are unreliable due to line overlap.
    """

    def __init__(
        self,
        n_curves: int = 4,
        max_gap_x: float = 100,
        max_gap_y: float = 50
    ):
        """
        Initialize the curve tracer.

        Args:
            n_curves: Expected number of curves
            max_gap_x: Maximum horizontal gap between consecutive points
            max_gap_y: Maximum vertical gap to consider same curve
        """
        self.n_curves = n_curves
        self.max_gap_x = max_gap_x
        self.max_gap_y = max_gap_y

    def trace_curves(self, markers: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Group markers into curves by tracing spatial continuity.

        Algorithm:
        1. Sort all markers by x-coordinate
        2. At each x position, identify which curve each marker belongs to
        3. Track curves as they progress from left to right

        Args:
            markers: List of marker dictionaries

        Returns:
            Dictionary mapping curve ID to list of markers
        """
        if not markers:
            return {}

        # Sort by x-coordinate
        sorted_markers = sorted(markers, key=lambda m: m['cx'])

        # Initialize curves
        curves = {i: [] for i in range(self.n_curves)}
        unassigned = sorted_markers.copy()

        # Find starting points - leftmost markers
        leftmost_x = sorted_markers[0]['cx']
        start_markers = [m for m in sorted_markers if m['cx'] < leftmost_x + 20]

        # Sort starting markers by y (top to bottom)
        start_markers_sorted = sorted(start_markers, key=lambda m: m['cy'])

        # Assign starting points to curves
        for i, marker in enumerate(start_markers_sorted[:self.n_curves]):
            marker['cluster'] = i
            curves[i].append(marker)
            if marker in unassigned:
                unassigned.remove(marker)

        # Trace each curve
        for marker in sorted_markers:
            if marker not in unassigned:
                continue

            best_curve = None
            min_distance = float('inf')

            for curve_id, curve_points in curves.items():
                if not curve_points:
                    continue

                last_point = curve_points[-1]
                dx = marker['cx'] - last_point['cx']
                dy = abs(marker['cy'] - last_point['cy'])

                if dx > self.max_gap_x or dx < 0:
                    continue
                if dy > self.max_gap_y:
                    continue

                distance = dy + dx * 0.1

                if distance < min_distance:
                    min_distance = distance
                    best_curve = curve_id

            if best_curve is not None:
                marker['cluster'] = best_curve
                curves[best_curve].append(marker)
                unassigned.remove(marker)

        # Handle remaining unassigned
        for marker in unassigned:
            best_curve = 0
            min_y_dist = float('inf')

            for curve_id, curve_points in curves.items():
                if not curve_points:
                    continue
                nearest = min(curve_points, key=lambda p: abs(p['cx'] - marker['cx']))
                y_dist = abs(marker['cy'] - nearest['cy'])

                if y_dist < min_y_dist:
                    min_y_dist = y_dist
                    best_curve = curve_id

            marker['cluster'] = best_curve
            curves[best_curve].append(marker)

        # Sort each curve by x
        for curve_id in curves:
            curves[curve_id] = sorted(curves[curve_id], key=lambda m: m['cx'])

        curves = {k: v for k, v in curves.items() if v}
        return curves

    def trace_curves_by_y_bands(self, markers: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Group markers by Y-coordinate clustering.
        Works well when curves are vertically separated.
        """
        if not markers:
            return {}

        y_coords = [m['cy'] for m in markers]
        y_min, y_max = min(y_coords), max(y_coords)

        if y_max - y_min < 10:
            for m in markers:
                m['cluster'] = 0
            return {0: sorted(markers, key=lambda m: m['cx'])}

        from sklearn.cluster import KMeans

        y_array = np.array(y_coords).reshape(-1, 1)
        n_clusters = min(self.n_curves, len(set(y_coords)))

        if n_clusters < 2:
            for m in markers:
                m['cluster'] = 0
            return {0: sorted(markers, key=lambda m: m['cx'])}

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(y_array)

        curves = {i: [] for i in range(n_clusters)}
        for marker, label in zip(markers, labels):
            marker['cluster'] = int(label)
            curves[int(label)].append(marker)

        # Reorder by y mean (top to bottom)
        curve_y_means = {
            cid: np.mean([m['cy'] for m in pts])
            for cid, pts in curves.items() if pts
        }
        sorted_ids = sorted(curve_y_means.keys(), key=lambda k: curve_y_means[k])

        new_curves = {}
        for new_id, old_id in enumerate(sorted_ids):
            for m in curves[old_id]:
                m['cluster'] = new_id
            new_curves[new_id] = sorted(curves[old_id], key=lambda m: m['cx'])

        return new_curves
