"""
Calibration dialog for setting axis values.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QGroupBox,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt


class CalibrationDialog(QDialog):
    """
    Dialog for entering calibration values for an axis.

    User clicks two points on the image, then enters the
    corresponding real-world values in this dialog.
    """

    def __init__(self, parent=None, title="Axis Calibration"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(350)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Click two points on the axis in the image,\n"
            "then enter their corresponding values below."
        )
        instructions.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(instructions)

        # Point 1
        point1_group = QGroupBox("Point 1")
        point1_layout = QHBoxLayout(point1_group)
        point1_label = QLabel("Value:")
        self.point1_spin = QDoubleSpinBox()
        self.point1_spin.setRange(-1e9, 1e9)
        self.point1_spin.setDecimals(4)
        self.point1_spin.setValue(0.0)
        point1_layout.addWidget(point1_label)
        point1_layout.addWidget(self.point1_spin)
        layout.addWidget(point1_group)

        # Point 2
        point2_group = QGroupBox("Point 2")
        point2_layout = QHBoxLayout(point2_group)
        point2_label = QLabel("Value:")
        self.point2_spin = QDoubleSpinBox()
        self.point2_spin.setRange(-1e9, 1e9)
        self.point2_spin.setDecimals(4)
        self.point2_spin.setValue(100.0)
        point2_layout.addWidget(point2_label)
        point2_layout.addWidget(self.point2_spin)
        layout.addWidget(point2_group)

        # Scale type
        scale_layout = QHBoxLayout()
        scale_label = QLabel("Scale:")
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Linear", "Logarithmic"])
        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(self.scale_combo)
        layout.addLayout(scale_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

    def get_values(self) -> list:
        """Get the entered calibration values."""
        return [self.point1_spin.value(), self.point2_spin.value()]

    def get_scale(self) -> str:
        """Get the selected scale type."""
        return self.scale_combo.currentText().lower()

    def set_values(self, value1: float, value2: float):
        """Set initial values."""
        self.point1_spin.setValue(value1)
        self.point2_spin.setValue(value2)

    def set_scale(self, scale: str):
        """Set the scale type."""
        index = 0 if scale == "linear" else 1
        self.scale_combo.setCurrentIndex(index)
