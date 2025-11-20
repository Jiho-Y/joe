#!/usr/bin/env python3
"""
Research Paper Manager - Main Entry Point
A desktop application for managing academic papers with PDF processing,
keyword extraction, and citation network visualization.

Uses PySide6 (Qt6) for cross-platform GUI.
"""

import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Research Paper Manager")
    app.setOrganizationName("Academic Tools")
    app.setApplicationVersion("0.1.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
