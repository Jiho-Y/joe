"""
Metadata input dialog for CSV export.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QGroupBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from datetime import datetime


class MetadataDialog(QDialog):
    """
    Dialog for entering metadata before CSV export.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Metadata")
        self.setModal(True)
        self.setMinimumWidth(450)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Source information
        source_group = QGroupBox("Source Information")
        source_layout = QFormLayout(source_group)

        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("DOI or reference")
        source_layout.addRow("Source:", self.source_edit)

        self.figure_edit = QLineEdit()
        self.figure_edit.setPlaceholderText("e.g., Figure 3a")
        source_layout.addRow("Figure:", self.figure_edit)

        layout.addWidget(source_group)

        # Material information
        material_group = QGroupBox("Material Information")
        material_layout = QFormLayout(material_group)

        self.material_edit = QLineEdit()
        self.material_edit.setPlaceholderText("e.g., 316L Stainless Steel")
        material_layout.addRow("Material:", self.material_edit)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(-273, 2000)
        self.temp_spin.setDecimals(1)
        self.temp_spin.setValue(0)
        self.temp_spin.setSuffix(" °C")
        material_layout.addRow("Temperature:", self.temp_spin)

        self.stress_spin = QDoubleSpinBox()
        self.stress_spin.setRange(0, 10000)
        self.stress_spin.setDecimals(2)
        self.stress_spin.setValue(0)
        self.stress_spin.setSuffix(" MPa")
        material_layout.addRow("Stress:", self.stress_spin)

        layout.addWidget(material_group)

        # Axis units
        units_group = QGroupBox("Axis Units")
        units_layout = QFormLayout(units_group)

        self.x_unit_edit = QLineEdit()
        self.x_unit_edit.setPlaceholderText("e.g., h (hours)")
        self.x_unit_edit.setText("h")
        units_layout.addRow("X-axis unit:", self.x_unit_edit)

        self.y_unit_edit = QLineEdit()
        self.y_unit_edit.setPlaceholderText("e.g., % (percent)")
        self.y_unit_edit.setText("%")
        units_layout.addRow("Y-axis unit:", self.y_unit_edit)

        layout.addWidget(units_group)

        # Notes
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Additional notes...")
        notes_layout.addWidget(self.notes_edit)
        layout.addWidget(notes_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Export")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

    def get_metadata(self) -> dict:
        """Get all entered metadata."""
        return {
            'source': self.source_edit.text(),
            'figure': self.figure_edit.text(),
            'material': self.material_edit.text(),
            'temperature_C': self.temp_spin.value(),
            'stress_MPa': self.stress_spin.value(),
            'x_unit': self.x_unit_edit.text(),
            'y_unit': self.y_unit_edit.text(),
            'notes': self.notes_edit.toPlainText(),
            'extraction_date': datetime.now().strftime('%Y-%m-%d'),
            'extraction_tool': 'CreepCurveDigitizer v0.1'
        }

    def set_metadata(self, metadata: dict):
        """Set metadata values (e.g., from loaded file)."""
        if 'source' in metadata:
            self.source_edit.setText(metadata['source'])
        if 'figure' in metadata:
            self.figure_edit.setText(metadata['figure'])
        if 'material' in metadata:
            self.material_edit.setText(metadata['material'])
        if 'temperature_C' in metadata:
            self.temp_spin.setValue(metadata['temperature_C'])
        if 'stress_MPa' in metadata:
            self.stress_spin.setValue(metadata['stress_MPa'])
        if 'x_unit' in metadata:
            self.x_unit_edit.setText(metadata['x_unit'])
        if 'y_unit' in metadata:
            self.y_unit_edit.setText(metadata['y_unit'])
        if 'notes' in metadata:
            self.notes_edit.setPlainText(metadata['notes'])
