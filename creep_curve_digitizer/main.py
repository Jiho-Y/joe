#!/usr/bin/env python3
"""
Creep Curve Digitizer - Entry Point

A PyQt6-based desktop application for extracting creep curve data
from graph images in papers/reports.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.main_window import MainWindow


def main():
    """Main entry point for the application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Creep Curve Digitizer")
    app.setApplicationVersion("0.1")
    app.setOrganizationName("CreepCurveDigitizer")

    # Set application style
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
