"""
Custom QGraphicsView widget for image display with zoom, pan, and ROI selection.
"""

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QGraphicsEllipseItem, QRubberBand
)
from PyQt6.QtGui import (
    QPixmap, QPen, QBrush, QColor, QPainter, QImage
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QSize

import numpy as np


# Cluster colors for visualization
CLUSTER_COLORS = [
    QColor(255, 0, 0),      # Red
    QColor(0, 128, 0),      # Green
    QColor(0, 0, 255),      # Blue
    QColor(255, 165, 0),    # Orange
    QColor(128, 0, 128),    # Purple
    QColor(0, 255, 255),    # Cyan
    QColor(255, 0, 255),    # Magenta
    QColor(128, 128, 0),    # Olive
]


class ImageView(QGraphicsView):
    """
    Custom QGraphicsView for displaying images with zoom, pan, ROI selection,
    and overlay visualization of detected points.
    """

    # Signals
    roi_changed = pyqtSignal(list)  # [x1, y1, x2, y2]
    exclude_zone_changed = pyqtSignal(list)  # [x1, y1, x2, y2]
    point_clicked = pyqtSignal(dict)  # Point data
    color_picked = pyqtSignal(tuple)  # (R, G, B)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QBrush(QColor(50, 50, 50)))

        # Image item
        self.pixmap_item = None
        self.original_pixmap = None

        # ROI selection
        self.roi_rect = None
        self.roi_item = None
        self.is_drawing_roi = False
        self.roi_start = None

        # Calibration mode
        self.calibration_mode = False
        self.calibration_axis = None
        self.calibration_points = []
        self.calibration_markers = []

        # Detected points and overlays
        self.detected_points = []
        self.point_items = []
        self.selected_point_index = None

        # Color picking mode
        self.color_pick_mode = False

        # Exclude zone (for legend)
        self.exclude_zones = []  # List of [x1, y1, x2, y2]
        self.exclude_zone_items = []
        self.is_drawing_exclude = False
        self.exclude_start = None
        self.exclude_draw_mode = False

        # Zoom factor
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0

    def load_image(self, file_path: str) -> bool:
        """Load an image from file path."""
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            return False

        self.clear_all()
        self.original_pixmap = pixmap
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(QRectF(pixmap.rect()))
        self.fit_to_window()
        return True

    def clear_all(self):
        """Clear all scene items."""
        self.scene.clear()
        self.pixmap_item = None
        self.roi_item = None
        self.roi_rect = None
        self.point_items = []
        self.calibration_markers = []
        self.detected_points = []
        self.exclude_zones = []
        self.exclude_zone_items = []

    def clear_overlays(self):
        """Clear overlay items (points, ROI) but keep the image."""
        # Remove point items
        for item in self.point_items:
            if item.scene():
                self.scene.removeItem(item)
        self.point_items = []

        # Remove calibration markers
        for item in self.calibration_markers:
            if item.scene():
                self.scene.removeItem(item)
        self.calibration_markers = []

        self.detected_points = []
        self.selected_point_index = None

    def zoom_in(self):
        """Zoom in by a factor of 1.25."""
        self._zoom(1.25)

    def zoom_out(self):
        """Zoom out by a factor of 0.8."""
        self._zoom(0.8)

    def _zoom(self, factor: float):
        """Apply zoom factor."""
        new_zoom = self.zoom_factor * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.zoom_factor = new_zoom
            self.scale(factor, factor)

    def fit_to_window(self):
        """Fit the image to the viewport."""
        if self.pixmap_item:
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.zoom_factor = self.transform().m11()

    def reset_zoom(self):
        """Reset zoom to 100%."""
        self.resetTransform()
        self.zoom_factor = 1.0

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Zoom with Ctrl + Wheel
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom(1.1)
            else:
                self._zoom(0.9)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())

            if self.calibration_mode:
                self._add_calibration_point(scene_pos)
                event.accept()
                return

            if self.color_pick_mode:
                self._pick_color(scene_pos)
                event.accept()
                return

            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Click to add point
                self._add_manual_point(scene_pos)
                event.accept()
                return

            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                # Shift+Click to start ROI selection
                self.is_drawing_roi = True
                self.roi_start = scene_pos
                if self.roi_item:
                    self.scene.removeItem(self.roi_item)
                    self.roi_item = None
                event.accept()
                return

            if event.modifiers() == Qt.KeyboardModifier.AltModifier or self.exclude_draw_mode:
                # Alt+Click to start exclude zone drawing
                self.is_drawing_exclude = True
                self.exclude_start = scene_pos
                event.accept()
                return

            # Check if clicking on a point
            point_index = self._find_point_at(scene_pos)
            if point_index is not None:
                self._select_point(point_index)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self.is_drawing_roi and self.roi_start:
            scene_pos = self.mapToScene(event.pos())
            self._update_roi_rect(self.roi_start, scene_pos)
            event.accept()
            return
        if self.is_drawing_exclude and self.exclude_start:
            scene_pos = self.mapToScene(event.pos())
            self._update_exclude_rect(self.exclude_start, scene_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing_roi:
            self.is_drawing_roi = False
            if self.roi_rect:
                self.roi_changed.emit(self.roi_rect)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing_exclude:
            self.is_drawing_exclude = False
            if self.exclude_draw_mode:
                self.exclude_draw_mode = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _update_roi_rect(self, start: QPointF, end: QPointF):
        """Update the ROI rectangle during drawing."""
        x1, y1 = int(start.x()), int(start.y())
        x2, y2 = int(end.x()), int(end.y())

        # Ensure proper order
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        self.roi_rect = [x1, y1, x2, y2]

        # Draw/update ROI rectangle
        if self.roi_item:
            self.scene.removeItem(self.roi_item)

        pen = QPen(QColor(0, 255, 0), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.roi_item = QGraphicsRectItem(x1, y1, x2 - x1, y2 - y1)
        self.roi_item.setPen(pen)
        self.roi_item.setBrush(QBrush(QColor(0, 255, 0, 30)))
        self.scene.addItem(self.roi_item)

    def get_roi(self) -> list:
        """Get the current ROI coordinates."""
        return self.roi_rect

    def set_roi(self, roi: list):
        """Set the ROI from loaded calibration."""
        if roi and len(roi) == 4:
            self.roi_rect = roi
            x1, y1, x2, y2 = roi
            if self.roi_item:
                self.scene.removeItem(self.roi_item)

            pen = QPen(QColor(0, 255, 0), 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            self.roi_item = QGraphicsRectItem(x1, y1, x2 - x1, y2 - y1)
            self.roi_item.setPen(pen)
            self.roi_item.setBrush(QBrush(QColor(0, 255, 0, 30)))
            self.scene.addItem(self.roi_item)

    def set_exclude_draw_mode(self, enabled: bool):
        """Enable/disable exclude zone drawing mode."""
        self.exclude_draw_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _update_exclude_rect(self, start: QPointF, end: QPointF):
        """Update the exclude zone rectangle during drawing."""
        x1, y1 = int(start.x()), int(start.y())
        x2, y2 = int(end.x()), int(end.y())

        # Ensure proper order
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        exclude_rect = [x1, y1, x2, y2]

        # Store and draw exclude zone
        if exclude_rect not in self.exclude_zones:
            self.exclude_zones.append(exclude_rect)

            pen = QPen(QColor(255, 0, 0), 2)
            pen.setStyle(Qt.PenStyle.DashDotLine)
            item = QGraphicsRectItem(x1, y1, x2 - x1, y2 - y1)
            item.setPen(pen)
            item.setBrush(QBrush(QColor(255, 0, 0, 40)))
            self.scene.addItem(item)
            self.exclude_zone_items.append(item)

            self.exclude_zone_changed.emit(exclude_rect)
        else:
            # Update the last exclude zone being drawn
            if self.exclude_zone_items:
                last_item = self.exclude_zone_items[-1]
                last_item.setRect(x1, y1, x2 - x1, y2 - y1)
                self.exclude_zones[-1] = exclude_rect

    def get_exclude_zones(self) -> list:
        """Get all exclude zones."""
        return self.exclude_zones

    def set_exclude_zones(self, zones: list):
        """Set exclude zones from loaded data."""
        self.clear_exclude_zones()
        for zone in zones:
            if zone and len(zone) == 4:
                x1, y1, x2, y2 = zone
                self.exclude_zones.append(zone)

                pen = QPen(QColor(255, 0, 0), 2)
                pen.setStyle(Qt.PenStyle.DashDotLine)
                item = QGraphicsRectItem(x1, y1, x2 - x1, y2 - y1)
                item.setPen(pen)
                item.setBrush(QBrush(QColor(255, 0, 0, 40)))
                self.scene.addItem(item)
                self.exclude_zone_items.append(item)

    def clear_exclude_zones(self):
        """Clear all exclude zones."""
        for item in self.exclude_zone_items:
            if item.scene():
                self.scene.removeItem(item)
        self.exclude_zone_items = []
        self.exclude_zones = []

    def add_exclude_zone(self, zone: list):
        """Add a single exclude zone."""
        if zone and len(zone) == 4:
            x1, y1, x2, y2 = zone
            self.exclude_zones.append(zone)

            pen = QPen(QColor(255, 0, 0), 2)
            pen.setStyle(Qt.PenStyle.DashDotLine)
            item = QGraphicsRectItem(x1, y1, x2 - x1, y2 - y1)
            item.setPen(pen)
            item.setBrush(QBrush(QColor(255, 0, 0, 40)))
            self.scene.addItem(item)
            self.exclude_zone_items.append(item)

    def set_calibration_mode(self, enabled: bool, axis: str = None):
        """Enable/disable calibration mode."""
        self.calibration_mode = enabled
        self.calibration_axis = axis
        if enabled:
            self.calibration_points = []
            # Change cursor
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Clear calibration markers
            for item in self.calibration_markers:
                if item.scene():
                    self.scene.removeItem(item)
            self.calibration_markers = []

    def _add_calibration_point(self, pos: QPointF):
        """Add a calibration point."""
        if len(self.calibration_points) >= 2:
            # Remove oldest point and marker
            self.calibration_points.pop(0)
            if self.calibration_markers:
                old_marker = self.calibration_markers.pop(0)
                if old_marker.scene():
                    self.scene.removeItem(old_marker)

        self.calibration_points.append((pos.x(), pos.y()))

        # Draw marker
        marker = QGraphicsEllipseItem(pos.x() - 5, pos.y() - 5, 10, 10)
        marker.setPen(QPen(QColor(255, 255, 0), 2))
        marker.setBrush(QBrush(QColor(255, 255, 0, 100)))
        self.scene.addItem(marker)
        self.calibration_markers.append(marker)

    def get_calibration_points(self) -> list:
        """Get the calibration points."""
        return self.calibration_points

    def set_color_pick_mode(self, enabled: bool):
        """Enable/disable color picking mode."""
        self.color_pick_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _pick_color(self, pos: QPointF):
        """Pick color at the given position."""
        if self.original_pixmap:
            x, y = int(pos.x()), int(pos.y())
            if 0 <= x < self.original_pixmap.width() and 0 <= y < self.original_pixmap.height():
                image = self.original_pixmap.toImage()
                color = image.pixelColor(x, y)
                self.color_picked.emit((color.red(), color.green(), color.blue()))

    def set_detected_points(self, points: list):
        """Set detected points for visualization."""
        self.detected_points = points

    def set_curve_clusters(self, clusters: dict):
        """Set curve clusters and update visualization."""
        # Clear existing point items
        for item in self.point_items:
            if item.scene():
                self.scene.removeItem(item)
        self.point_items = []

        # Draw points for each cluster
        for cluster_id, points in clusters.items():
            color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]

            for point in points:
                cx, cy = point['cx'], point['cy']

                # Draw circle marker
                item = QGraphicsEllipseItem(cx - 4, cy - 4, 8, 8)
                item.setPen(QPen(color, 2))
                item.setBrush(QBrush(color.lighter(150)))
                item.setData(0, point)  # Store point data
                self.scene.addItem(item)
                self.point_items.append(item)

    def _find_point_at(self, pos: QPointF) -> int:
        """Find a point near the given position."""
        threshold = 10  # pixels
        for i, item in enumerate(self.point_items):
            rect = item.rect()
            center = rect.center()
            dist = ((pos.x() - center.x()) ** 2 + (pos.y() - center.y()) ** 2) ** 0.5
            if dist <= threshold:
                return i
        return None

    def _select_point(self, index: int):
        """Select a point for editing."""
        # Deselect previous
        if self.selected_point_index is not None and self.selected_point_index < len(self.point_items):
            prev_item = self.point_items[self.selected_point_index]
            prev_point = prev_item.data(0)
            if prev_point:
                cluster_id = prev_point.get('cluster', 0)
                color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]
                prev_item.setPen(QPen(color, 2))

        # Select new
        self.selected_point_index = index
        if index is not None and index < len(self.point_items):
            item = self.point_items[index]
            item.setPen(QPen(QColor(255, 255, 255), 3))
            point_data = item.data(0)
            if point_data:
                self.point_clicked.emit(point_data)

    def _add_manual_point(self, pos: QPointF):
        """Add a manual point (Ctrl+Click)."""
        # Default to cluster 0
        point = {
            'cx': pos.x(),
            'cy': pos.y(),
            'area': 0,
            'circularity': 0,
            'solidity': 0,
            'cluster': 0,
            'manual': True
        }
        self.detected_points.append(point)

        color = CLUSTER_COLORS[0]
        item = QGraphicsEllipseItem(pos.x() - 4, pos.y() - 4, 8, 8)
        item.setPen(QPen(color, 2))
        item.setBrush(QBrush(color.lighter(150)))
        item.setData(0, point)
        self.scene.addItem(item)
        self.point_items.append(item)

    def delete_selected_point(self):
        """Delete the currently selected point."""
        if self.selected_point_index is not None and self.selected_point_index < len(self.point_items):
            item = self.point_items[self.selected_point_index]
            point_data = item.data(0)

            # Remove from scene
            self.scene.removeItem(item)
            self.point_items.pop(self.selected_point_index)

            # Remove from detected points
            if point_data in self.detected_points:
                self.detected_points.remove(point_data)

            self.selected_point_index = None

    def reassign_selected_point(self, new_cluster: int):
        """Reassign the selected point to a new cluster."""
        if self.selected_point_index is not None and self.selected_point_index < len(self.point_items):
            item = self.point_items[self.selected_point_index]
            point_data = item.data(0)

            if point_data:
                point_data['cluster'] = new_cluster
                color = CLUSTER_COLORS[new_cluster % len(CLUSTER_COLORS)]
                item.setPen(QPen(color, 2))
                item.setBrush(QBrush(color.lighter(150)))

            self.selected_point_index = None

    def get_image_array(self) -> np.ndarray:
        """Get the current image as a numpy array."""
        if self.original_pixmap:
            image = self.original_pixmap.toImage()
            image = image.convertToFormat(QImage.Format.Format_RGB888)

            width = image.width()
            height = image.height()
            bytes_per_line = image.bytesPerLine()

            ptr = image.bits()
            ptr.setsize(height * bytes_per_line)
            arr = np.array(ptr).reshape(height, bytes_per_line)
            # Trim to actual width (remove padding)
            arr = arr[:, :width * 3].reshape(height, width, 3)
            return arr
        return None
