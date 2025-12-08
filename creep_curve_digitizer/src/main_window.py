"""
Main Window implementation for Creep Curve Digitizer.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QSplitter
)
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtCore import Qt, QSize

from .image_view import ImageView
from .control_panel import ControlPanel
from .dialogs import CalibrationDialog, MetadataDialog
from .calibration import Calibration
from .exporter import Exporter


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Creep Curve Digitizer v0.1")
        self.setMinimumSize(1200, 800)

        # Data storage
        self.current_image_path = None
        self.calibration = Calibration()
        self.detected_points = []  # List of detected marker points
        self.curve_clusters = {}   # Cluster ID -> list of points

        self._setup_ui()
        self._create_menus()
        self._create_toolbar()
        self._create_statusbar()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Control panel (left side)
        self.control_panel = ControlPanel()
        self.control_panel.setFixedWidth(250)
        splitter.addWidget(self.control_panel)

        # Image view (right side)
        self.image_view = ImageView()
        splitter.addWidget(self.image_view)

        # Set stretch factors
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _create_menus(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open Image...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_image)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_calib_action = QAction("Save &Calibration...", self)
        save_calib_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_calib_action.triggered.connect(self._save_calibration)
        file_menu.addAction(save_calib_action)

        load_calib_action = QAction("&Load Calibration...", self)
        load_calib_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        load_calib_action.triggered.connect(self._load_calibration)
        file_menu.addAction(load_calib_action)

        file_menu.addSeparator()

        export_action = QAction("&Export CSV...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        clear_action = QAction("&Clear All", self)
        clear_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        clear_action.triggered.connect(self._clear_all)
        edit_menu.addAction(clear_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.image_view.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.image_view.zoom_out)
        view_menu.addAction(zoom_out_action)

        fit_action = QAction("&Fit to Window", self)
        fit_action.setShortcut(QKeySequence("Ctrl+0"))
        fit_action.triggered.connect(self.image_view.fit_to_window)
        view_menu.addAction(fit_action)

        reset_zoom_action = QAction("&Reset Zoom", self)
        reset_zoom_action.setShortcut(QKeySequence("Ctrl+1"))
        reset_zoom_action.triggered.connect(self.image_view.reset_zoom)
        view_menu.addAction(reset_zoom_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """Create the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Open button
        open_btn = QAction("Open", self)
        open_btn.setToolTip("Open Image (Ctrl+O)")
        open_btn.triggered.connect(self._open_image)
        toolbar.addAction(open_btn)

        toolbar.addSeparator()

        # Zoom buttons
        zoom_in_btn = QAction("Zoom+", self)
        zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        zoom_in_btn.triggered.connect(self.image_view.zoom_in)
        toolbar.addAction(zoom_in_btn)

        zoom_out_btn = QAction("Zoom-", self)
        zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        zoom_out_btn.triggered.connect(self.image_view.zoom_out)
        toolbar.addAction(zoom_out_btn)

        fit_btn = QAction("Fit", self)
        fit_btn.setToolTip("Fit to Window (Ctrl+0)")
        fit_btn.triggered.connect(self.image_view.fit_to_window)
        toolbar.addAction(fit_btn)

        toolbar.addSeparator()

        # Export button
        export_btn = QAction("Export", self)
        export_btn.setToolTip("Export CSV (Ctrl+E)")
        export_btn.triggered.connect(self._export_csv)
        toolbar.addAction(export_btn)

    def _create_statusbar(self):
        """Create the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self._update_status("Ready")

    def _connect_signals(self):
        """Connect signals between components."""
        # Control panel signals
        self.control_panel.detect_clicked.connect(self._run_detection)
        self.control_panel.clear_clicked.connect(self._clear_all)
        self.control_panel.export_clicked.connect(self._export_csv)
        self.control_panel.set_x_axis_clicked.connect(self._set_x_axis)
        self.control_panel.set_y_axis_clicked.connect(self._set_y_axis)

        # Image view signals
        self.image_view.roi_changed.connect(self._on_roi_changed)
        self.image_view.point_clicked.connect(self._on_point_clicked)
        self.image_view.color_picked.connect(self._on_color_picked)

    def _update_status(self, message: str, points: int = 0, curves: int = 0):
        """Update the status bar."""
        status = f"{message} | Points: {points} | Curves: {curves}"
        self.statusbar.showMessage(status)

    def _open_image(self):
        """Open an image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;All Files (*)"
        )
        if file_path:
            self.current_image_path = file_path
            self.image_view.load_image(file_path)
            self._clear_all()
            self._update_status(f"Loaded: {file_path}")

    def _save_calibration(self):
        """Save calibration data to JSON."""
        if not self.current_image_path:
            QMessageBox.warning(self, "Warning", "No image loaded.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Calibration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            params = self.control_panel.get_parameters()
            Exporter.save_calibration(
                file_path,
                self.current_image_path,
                self.image_view.get_roi(),
                self.calibration,
                self.control_panel.get_current_mode(),
                params
            )
            self._update_status(f"Calibration saved to: {file_path}")

    def _load_calibration(self):
        """Load calibration data from JSON."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Calibration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            data = Exporter.load_calibration(file_path)
            if data:
                # Apply loaded calibration
                if 'roi' in data and data['roi']:
                    self.image_view.set_roi(data['roi'])
                if 'x_calib' in data:
                    self.calibration.set_x_calibration(
                        data['x_calib']['pixel'],
                        data['x_calib']['value'],
                        data['x_calib'].get('scale', 'linear')
                    )
                if 'y_calib' in data:
                    self.calibration.set_y_calibration(
                        data['y_calib']['pixel'],
                        data['y_calib']['value'],
                        data['y_calib'].get('scale', 'linear')
                    )
                if 'mode' in data:
                    self.control_panel.set_mode(data['mode'])
                if 'parameters' in data:
                    self.control_panel.set_parameters(data['parameters'])
                self._update_status(f"Calibration loaded from: {file_path}")

    def _export_csv(self):
        """Export detected curves to CSV."""
        if not self.curve_clusters:
            QMessageBox.warning(self, "Warning", "No curves detected.")
            return

        if not self.calibration.is_calibrated():
            response = QMessageBox.question(
                self,
                "Calibration Required",
                "Axes are not calibrated. Export in pixel coordinates?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if response == QMessageBox.StandardButton.No:
                return

        # Show metadata dialog
        dialog = MetadataDialog(self)
        if dialog.exec():
            metadata = dialog.get_metadata()

            # Get save directory
            dir_path = QFileDialog.getExistingDirectory(
                self,
                "Select Export Directory"
            )
            if dir_path:
                Exporter.export_curves_csv(
                    dir_path,
                    self.curve_clusters,
                    self.calibration,
                    metadata
                )
                self._update_status(
                    f"Exported {len(self.curve_clusters)} curves to: {dir_path}"
                )

    def _clear_all(self):
        """Clear all detected points and curves."""
        self.detected_points = []
        self.curve_clusters = {}
        self.image_view.clear_overlays()
        self._update_status("Cleared all data")

    def _set_x_axis(self):
        """Set X-axis calibration."""
        dialog = CalibrationDialog(self, "X-Axis Calibration")
        self.image_view.set_calibration_mode(True, 'x')
        if dialog.exec():
            points = self.image_view.get_calibration_points()
            if len(points) >= 2:
                values = dialog.get_values()
                self.calibration.set_x_calibration(
                    [points[0][0], points[1][0]],
                    values,
                    dialog.get_scale()
                )
                self._update_status("X-axis calibrated")
        self.image_view.set_calibration_mode(False)

    def _set_y_axis(self):
        """Set Y-axis calibration."""
        dialog = CalibrationDialog(self, "Y-Axis Calibration")
        self.image_view.set_calibration_mode(True, 'y')
        if dialog.exec():
            points = self.image_view.get_calibration_points()
            if len(points) >= 2:
                values = dialog.get_values()
                self.calibration.set_y_calibration(
                    [points[0][1], points[1][1]],
                    values,
                    dialog.get_scale()
                )
                self._update_status("Y-axis calibrated")
        self.image_view.set_calibration_mode(False)

    def _run_detection(self):
        """Run curve detection based on selected mode."""
        if not self.current_image_path:
            QMessageBox.warning(self, "Warning", "No image loaded.")
            return

        mode = self.control_panel.get_current_mode()
        params = self.control_panel.get_parameters()
        roi = self.image_view.get_roi()

        self._update_status("Detecting curves...")

        try:
            if mode == "B3":
                self._detect_mode_b3(params, roi)
            elif mode == "A":
                self._detect_mode_a(params, roi)
            elif mode == "B1":
                self._detect_mode_b1(params, roi)

            # Update visualization
            self.image_view.set_detected_points(self.detected_points)
            self.image_view.set_curve_clusters(self.curve_clusters)

            total_points = sum(len(pts) for pts in self.curve_clusters.values())
            self._update_status(
                "Detection complete",
                points=total_points,
                curves=len(self.curve_clusters)
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Detection failed: {str(e)}")
            self._update_status("Detection failed")

    def _detect_mode_b3(self, params: dict, roi: list):
        """Detect markers using Mode B3 (Line + Marker)."""
        from .processing import preprocess_image, MarkerDetector, ShapeClusterer
        import cv2

        # Load and preprocess image
        image = cv2.imread(self.current_image_path)
        if roi:
            x1, y1, x2, y2 = roi
            image = image[y1:y2, x1:x2]

        # Preprocess
        binary = preprocess_image(image, params.get('kernel_size', 5))

        # Detect markers
        detector = MarkerDetector(
            min_area=params.get('min_area', 30),
            max_area=params.get('max_area', 500),
            kernel_size=params.get('kernel_size', 5)
        )
        markers = detector.detect(binary, image)

        if not markers:
            QMessageBox.information(self, "Info", "No markers detected.")
            return

        # Cluster markers by shape
        clusterer = ShapeClusterer(n_clusters=params.get('n_clusters', 4))
        self.curve_clusters = clusterer.cluster(markers)

        # Adjust coordinates if ROI was used
        if roi:
            x_offset, y_offset = roi[0], roi[1]
            for cluster_id, points in self.curve_clusters.items():
                for point in points:
                    point['cx'] += x_offset
                    point['cy'] += y_offset

        # Store all detected points
        self.detected_points = []
        for cluster_id, points in self.curve_clusters.items():
            for point in points:
                point['cluster'] = cluster_id
                self.detected_points.append(point)

    def _detect_mode_a(self, params: dict, roi: list):
        """Detect curves using Mode A (Multi-color)."""
        # Will be implemented in Phase 2
        QMessageBox.information(
            self, "Info",
            "Mode A (Multi-color) will be implemented in Phase 2.\n"
            "Click on curve colors to extract them."
        )

    def _detect_mode_b1(self, params: dict, roi: list):
        """Detect curves using Mode B1 (Line only)."""
        # Will be implemented in Phase 2
        QMessageBox.information(
            self, "Info",
            "Mode B1 (Line only) will be implemented in Phase 2.\n"
            "Select line style templates to distinguish curves."
        )

    def _on_roi_changed(self, roi: list):
        """Handle ROI change."""
        self._update_status(f"ROI set: {roi}")

    def _on_point_clicked(self, point: dict):
        """Handle point click for manual editing."""
        # For manual point editing
        pass

    def _on_color_picked(self, color: tuple):
        """Handle color pick for Mode A."""
        # For Mode A color-based extraction
        pass

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Creep Curve Digitizer",
            "Creep Curve Digitizer v0.1\n\n"
            "A tool for extracting creep curve data from graph images.\n\n"
            "Built with PyQt6, OpenCV, and scikit-learn."
        )

    def keyPressEvent(self, event):
        """Handle key press events for manual editing."""
        if event.key() == Qt.Key.Key_Delete:
            # Delete selected point
            self.image_view.delete_selected_point()
        elif event.key() in [Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4]:
            # Reassign cluster
            cluster_id = event.key() - Qt.Key.Key_1
            self.image_view.reassign_selected_point(cluster_id)
        super().keyPressEvent(event)
