"""
Control panel widget for mode selection and parameter adjustment.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QRadioButton, QLabel, QSpinBox, QPushButton,
    QButtonGroup, QFrame
)
from PyQt6.QtCore import pyqtSignal


class ControlPanel(QWidget):
    """
    Left-side control panel containing mode selection,
    parameter controls, calibration buttons, and action buttons.
    """

    # Signals
    detect_clicked = pyqtSignal()
    clear_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    set_x_axis_clicked = pyqtSignal()
    set_y_axis_clicked = pyqtSignal()
    set_exclude_zone_clicked = pyqtSignal()
    clear_exclude_zone_clicked = pyqtSignal()
    auto_detect_legend_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the control panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Mode selection group
        mode_group = QGroupBox("Mode Selection")
        mode_layout = QVBoxLayout(mode_group)

        self.mode_button_group = QButtonGroup(self)

        self.mode_a_radio = QRadioButton("Mode A: Multi-color")
        self.mode_b1_radio = QRadioButton("Mode B1: Line only")
        self.mode_b3_radio = QRadioButton("Mode B3: Line + Marker")
        self.mode_b3_radio.setChecked(True)  # Default

        self.mode_button_group.addButton(self.mode_a_radio, 0)
        self.mode_button_group.addButton(self.mode_b1_radio, 1)
        self.mode_button_group.addButton(self.mode_b3_radio, 2)

        mode_layout.addWidget(self.mode_a_radio)
        mode_layout.addWidget(self.mode_b1_radio)
        mode_layout.addWidget(self.mode_b3_radio)

        layout.addWidget(mode_group)

        # Parameters group
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_group)

        # Kernel size
        kernel_layout = QHBoxLayout()
        kernel_label = QLabel("Kernel size:")
        self.kernel_spin = QSpinBox()
        self.kernel_spin.setRange(3, 15)
        self.kernel_spin.setSingleStep(2)
        self.kernel_spin.setValue(5)
        kernel_layout.addWidget(kernel_label)
        kernel_layout.addWidget(self.kernel_spin)
        params_layout.addLayout(kernel_layout)

        # Min area
        min_area_layout = QHBoxLayout()
        min_area_label = QLabel("Min area:")
        self.min_area_spin = QSpinBox()
        self.min_area_spin.setRange(5, 200)
        self.min_area_spin.setValue(30)
        min_area_layout.addWidget(min_area_label)
        min_area_layout.addWidget(self.min_area_spin)
        params_layout.addLayout(min_area_layout)

        # Max area
        max_area_layout = QHBoxLayout()
        max_area_label = QLabel("Max area:")
        self.max_area_spin = QSpinBox()
        self.max_area_spin.setRange(100, 2000)
        self.max_area_spin.setValue(500)
        max_area_layout.addWidget(max_area_label)
        max_area_layout.addWidget(self.max_area_spin)
        params_layout.addLayout(max_area_layout)

        # Number of clusters
        clusters_layout = QHBoxLayout()
        clusters_label = QLabel("Clusters:")
        self.clusters_spin = QSpinBox()
        self.clusters_spin.setRange(1, 10)
        self.clusters_spin.setValue(4)
        clusters_layout.addWidget(clusters_label)
        clusters_layout.addWidget(self.clusters_spin)
        params_layout.addLayout(clusters_layout)

        layout.addWidget(params_group)

        # Calibration group
        calib_group = QGroupBox("Calibration")
        calib_layout = QVBoxLayout(calib_group)

        self.set_x_btn = QPushButton("Set X-axis")
        self.set_x_btn.clicked.connect(self.set_x_axis_clicked.emit)
        calib_layout.addWidget(self.set_x_btn)

        self.set_y_btn = QPushButton("Set Y-axis")
        self.set_y_btn.clicked.connect(self.set_y_axis_clicked.emit)
        calib_layout.addWidget(self.set_y_btn)

        layout.addWidget(calib_group)

        # ROI instruction
        roi_group = QGroupBox("ROI Selection")
        roi_layout = QVBoxLayout(roi_group)
        roi_label = QLabel("Shift + Drag to select\ngraph region")
        roi_label.setStyleSheet("color: gray; font-style: italic;")
        roi_layout.addWidget(roi_label)
        layout.addWidget(roi_group)

        # Exclude Zone (for legend)
        exclude_group = QGroupBox("Exclude Zone (Legend)")
        exclude_layout = QVBoxLayout(exclude_group)

        self.set_exclude_btn = QPushButton("Set Exclude Zone")
        self.set_exclude_btn.setToolTip("Alt + Drag to mark legend area")
        self.set_exclude_btn.clicked.connect(self.set_exclude_zone_clicked.emit)
        exclude_layout.addWidget(self.set_exclude_btn)

        self.auto_legend_btn = QPushButton("Auto-detect Legend")
        self.auto_legend_btn.setToolTip("Automatically detect legend region")
        self.auto_legend_btn.clicked.connect(self.auto_detect_legend_clicked.emit)
        exclude_layout.addWidget(self.auto_legend_btn)

        self.clear_exclude_btn = QPushButton("Clear Exclude Zone")
        self.clear_exclude_btn.clicked.connect(self.clear_exclude_zone_clicked.emit)
        exclude_layout.addWidget(self.clear_exclude_btn)

        exclude_hint = QLabel("Alt + Drag to draw")
        exclude_hint.setStyleSheet("color: gray; font-style: italic; font-size: 10px;")
        exclude_layout.addWidget(exclude_hint)

        layout.addWidget(exclude_group)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Actions group
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)

        self.detect_btn = QPushButton("Detect Curves")
        self.detect_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-weight: bold; padding: 8px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.detect_btn.clicked.connect(self.detect_clicked.emit)
        actions_layout.addWidget(self.detect_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_clicked.emit)
        actions_layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; "
            "font-weight: bold; padding: 8px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        self.export_btn.clicked.connect(self.export_clicked.emit)
        actions_layout.addWidget(self.export_btn)

        layout.addWidget(actions_group)

        # Manual editing instructions
        edit_group = QGroupBox("Manual Editing")
        edit_layout = QVBoxLayout(edit_group)
        edit_label = QLabel(
            "Ctrl + Click: Add point\n"
            "Click: Select point\n"
            "Delete: Remove point\n"
            "1-4 keys: Change cluster"
        )
        edit_label.setStyleSheet("color: gray; font-size: 11px;")
        edit_layout.addWidget(edit_label)
        layout.addWidget(edit_group)

        # Add stretch to push everything to the top
        layout.addStretch()

    def get_current_mode(self) -> str:
        """Get the currently selected mode."""
        if self.mode_a_radio.isChecked():
            return "A"
        elif self.mode_b1_radio.isChecked():
            return "B1"
        else:
            return "B3"

    def set_mode(self, mode: str):
        """Set the mode from loaded calibration."""
        if mode == "A":
            self.mode_a_radio.setChecked(True)
        elif mode == "B1":
            self.mode_b1_radio.setChecked(True)
        else:
            self.mode_b3_radio.setChecked(True)

    def get_parameters(self) -> dict:
        """Get current parameter values."""
        return {
            'kernel_size': self.kernel_spin.value(),
            'min_area': self.min_area_spin.value(),
            'max_area': self.max_area_spin.value(),
            'n_clusters': self.clusters_spin.value()
        }

    def set_parameters(self, params: dict):
        """Set parameters from loaded calibration."""
        if 'kernel_size' in params:
            self.kernel_spin.setValue(params['kernel_size'])
        if 'min_area' in params:
            self.min_area_spin.setValue(params['min_area'])
        if 'max_area' in params:
            self.max_area_spin.setValue(params['max_area'])
        if 'n_clusters' in params:
            self.clusters_spin.setValue(params['n_clusters'])
