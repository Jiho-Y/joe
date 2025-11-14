"""
Settings dialog for Research Paper Manager.
Allows configuration of API keys, search preferences, and other settings.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTabWidget, QWidget,
    QCheckBox, QSpinBox, QGroupBox, QMessageBox,
    QFormLayout
)
from PySide6.QtCore import Qt

from src.utils.config import get_config


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        # Create tab widget
        tabs = QTabWidget()

        # Semantic Scholar tab
        semantic_scholar_tab = self.create_semantic_scholar_tab()
        tabs.addTab(semantic_scholar_tab, "Semantic Scholar")

        # Search tab
        search_tab = self.create_search_tab()
        tabs.addTab(search_tab, "Search")

        # PDF Processing tab
        pdf_tab = self.create_pdf_processing_tab()
        tabs.addTab(pdf_tab, "PDF Processing")

        # Keyword Extraction tab
        keyword_tab = self.create_keyword_tab()
        tabs.addTab(keyword_tab, "Keywords")

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()

        test_api_btn = QPushButton("Test API Connection")
        test_api_btn.clicked.connect(self.test_api_connection)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(test_api_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def create_semantic_scholar_tab(self) -> QWidget:
        """Create Semantic Scholar configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # API Key section
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout()

        # Enabled checkbox
        self.ss_enabled_check = QCheckBox("Enable Semantic Scholar integration")
        self.ss_enabled_check.setToolTip(
            "Use Semantic Scholar API for accurate metadata extraction"
        )
        api_layout.addRow("", self.ss_enabled_check)

        # API Key input
        self.ss_api_key_input = QLineEdit()
        self.ss_api_key_input.setPlaceholderText("Optional - for higher rate limits")
        self.ss_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("API Key:", self.ss_api_key_input)

        # Show/Hide API Key button
        show_api_key_btn = QPushButton("Show/Hide")
        show_api_key_btn.clicked.connect(self.toggle_api_key_visibility)
        api_layout.addRow("", show_api_key_btn)

        # Get API Key link
        info_label = QLabel(
            'Get a free API key at: '
            '<a href="https://www.semanticscholar.org/product/api">'
            'semanticscholar.org/product/api</a>'
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        api_layout.addRow("", info_label)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Rate limits section
        limits_group = QGroupBox("Rate Limits")
        limits_layout = QFormLayout()

        self.ss_timeout_spin = QSpinBox()
        self.ss_timeout_spin.setRange(5, 60)
        self.ss_timeout_spin.setSuffix(" seconds")
        limits_layout.addRow("Timeout:", self.ss_timeout_spin)

        self.ss_retries_spin = QSpinBox()
        self.ss_retries_spin.setRange(0, 5)
        limits_layout.addRow("Max Retries:", self.ss_retries_spin)

        info_text = QLabel(
            "Free tier: 100 requests/second\n"
            "With API key: 1,000 requests/second"
        )
        info_text.setWordWrap(True)
        limits_layout.addRow("", info_text)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        layout.addStretch()

        return widget

    def create_search_tab(self) -> QWidget:
        """Create search configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        search_group = QGroupBox("Search Settings")
        search_layout = QFormLayout()

        # Default result limit
        self.search_limit_spin = QSpinBox()
        self.search_limit_spin.setRange(10, 1000)
        self.search_limit_spin.setSingleStep(10)
        search_layout.addRow("Default Results Limit:", self.search_limit_spin)

        # FTS5 enabled
        self.fts5_enabled_check = QCheckBox("Enable FTS5 full-text search")
        self.fts5_enabled_check.setToolTip(
            "Use SQLite FTS5 for fast full-text search (recommended)"
        )
        search_layout.addRow("", self.fts5_enabled_check)

        # Fallback enabled
        self.fallback_enabled_check = QCheckBox("Enable fallback LIKE search")
        self.fallback_enabled_check.setToolTip(
            "Use slower LIKE queries if FTS5 returns no results"
        )
        search_layout.addRow("", self.fallback_enabled_check)

        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        layout.addStretch()

        return widget

    def create_pdf_processing_tab(self) -> QWidget:
        """Create PDF processing configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        pdf_group = QGroupBox("PDF Processing")
        pdf_layout = QFormLayout()

        # Max pages for metadata
        self.metadata_pages_spin = QSpinBox()
        self.metadata_pages_spin.setRange(1, 10)
        self.metadata_pages_spin.setToolTip(
            "Number of pages to scan for title, authors, etc."
        )
        pdf_layout.addRow("Pages for Metadata:", self.metadata_pages_spin)

        # Max pages for full text
        self.fulltext_pages_spin = QSpinBox()
        self.fulltext_pages_spin.setRange(10, 200)
        self.fulltext_pages_spin.setSingleStep(10)
        self.fulltext_pages_spin.setToolTip(
            "Maximum pages to extract for full-text search"
        )
        pdf_layout.addRow("Pages for Full Text:", self.fulltext_pages_spin)

        # Extract references
        self.extract_refs_check = QCheckBox("Extract reference list")
        self.extract_refs_check.setToolTip(
            "Attempt to extract citation references from papers"
        )
        pdf_layout.addRow("", self.extract_refs_check)

        pdf_group.setLayout(pdf_layout)
        layout.addWidget(pdf_group)

        layout.addStretch()

        return widget

    def create_keyword_tab(self) -> QWidget:
        """Create keyword extraction configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        keyword_group = QGroupBox("Keyword Extraction")
        keyword_layout = QFormLayout()

        # Top N keywords
        self.keyword_top_n_spin = QSpinBox()
        self.keyword_top_n_spin.setRange(5, 50)
        keyword_layout.addRow("Number of Keywords:", self.keyword_top_n_spin)

        # Method info
        info_label = QLabel(
            "Method: YAKE (fast, statistical)\n"
            "Future: KeyBERT (ML-based, slower but more accurate)"
        )
        info_label.setWordWrap(True)
        keyword_layout.addRow("", info_label)

        keyword_group.setLayout(keyword_layout)
        layout.addWidget(keyword_group)

        layout.addStretch()

        return widget

    def load_settings(self):
        """Load current settings from config."""
        # Semantic Scholar
        self.ss_enabled_check.setChecked(
            self.config.get('semantic_scholar.enabled', True)
        )
        api_key = self.config.get_semantic_scholar_api_key()
        if api_key:
            self.ss_api_key_input.setText(api_key)

        self.ss_timeout_spin.setValue(
            self.config.get('semantic_scholar.timeout', 10)
        )
        self.ss_retries_spin.setValue(
            self.config.get('semantic_scholar.max_retries', 2)
        )

        # Search
        self.search_limit_spin.setValue(
            self.config.get('search.default_limit', 100)
        )
        self.fts5_enabled_check.setChecked(
            self.config.get('search.enable_fts5', True)
        )
        self.fallback_enabled_check.setChecked(
            self.config.get('search.enable_fallback', True)
        )

        # PDF Processing
        self.metadata_pages_spin.setValue(
            self.config.get('pdf_processing.max_pages_for_metadata', 3)
        )
        self.fulltext_pages_spin.setValue(
            self.config.get('pdf_processing.max_pages_for_full_text', 50)
        )
        self.extract_refs_check.setChecked(
            self.config.get('pdf_processing.extract_references', True)
        )

        # Keywords
        self.keyword_top_n_spin.setValue(
            self.config.get('keywords.top_n', 10)
        )

    def save_settings(self):
        """Save settings to config."""
        # Semantic Scholar
        self.config.enable_semantic_scholar(
            self.ss_enabled_check.isChecked()
        )

        api_key = self.ss_api_key_input.text().strip()
        if api_key:
            self.config.set_semantic_scholar_api_key(api_key)
        else:
            self.config.set_semantic_scholar_api_key(None)

        self.config.set('semantic_scholar.timeout',
                       self.ss_timeout_spin.value())
        self.config.set('semantic_scholar.max_retries',
                       self.ss_retries_spin.value())

        # Search
        self.config.set('search.default_limit',
                       self.search_limit_spin.value())
        self.config.set('search.enable_fts5',
                       self.fts5_enabled_check.isChecked())
        self.config.set('search.enable_fallback',
                       self.fallback_enabled_check.isChecked())

        # PDF Processing
        self.config.set('pdf_processing.max_pages_for_metadata',
                       self.metadata_pages_spin.value())
        self.config.set('pdf_processing.max_pages_for_full_text',
                       self.fulltext_pages_spin.value())
        self.config.set('pdf_processing.extract_references',
                       self.extract_refs_check.isChecked())

        # Keywords
        self.config.set('keywords.top_n',
                       self.keyword_top_n_spin.value())

        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings have been saved successfully."
        )

        self.accept()

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        response = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if response == QMessageBox.StandardButton.Yes:
            # Reset config to defaults
            from src.utils.config import Config
            self.config.config = Config.DEFAULT_CONFIG.copy()
            self.config.save()
            self.load_settings()

            QMessageBox.information(
                self,
                "Settings Reset",
                "All settings have been reset to defaults."
            )

    def toggle_api_key_visibility(self):
        """Toggle API key field visibility."""
        if self.ss_api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.ss_api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.ss_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

    def test_api_connection(self):
        """Test Semantic Scholar API connection."""
        from src.utils.semantic_scholar import SemanticScholarAPI

        # Get API key from input (if changed but not saved)
        api_key = self.ss_api_key_input.text().strip() or None

        try:
            api = SemanticScholarAPI(api_key=api_key)

            # Test with a known paper
            test_doi = "10.1038/nature14539"  # AlphaGo paper
            result = api.get_paper_by_doi(test_doi)

            if result:
                QMessageBox.information(
                    self,
                    "API Test Successful",
                    f"✓ Successfully connected to Semantic Scholar API\n\n"
                    f"Test paper: {result.get('title')}\n"
                    f"Year: {result.get('year')}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "API Test Failed",
                    "Could not retrieve test paper from Semantic Scholar.\n"
                    "Please check your internet connection."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "API Test Error",
                f"Error testing API connection:\n{str(e)}"
            )
