"""
Main application window using PySide6 (Qt6).
Compatible with both PyQt6 and PySide6.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QLineEdit, QLabel,
    QSplitter, QTextEdit, QListWidget, QProgressDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction
from pathlib import Path
from typing import List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.database import Database
from src.core.pdf_processor import PDFProcessor
from src.core.metadata_extractor import KeywordExtractor
from src.core.citation_matcher import CitationMatcher
from src.models.paper import Paper
from src.ui.settings_dialog import SettingsDialog
from src.ui.citation_network_dialog import CitationNetworkDialog


class PDFImportThread(QThread):
    """Background thread for importing PDFs."""

    progress = Signal(int, str)  # (percentage, status_message)
    finished = Signal(list)  # List of imported paper IDs
    error = Signal(str)

    def __init__(self, pdf_paths: List[str], db_path: str = "data/papers.db"):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.db_path = db_path
        self.keyword_extractor = KeywordExtractor()

    def run(self):
        """Process PDFs in background."""
        # Create new database connection in this thread
        db = Database(self.db_path)

        imported_ids = []
        total = len(self.pdf_paths)

        for i, pdf_path in enumerate(self.pdf_paths):
            try:
                # Update progress
                filename = Path(pdf_path).name
                self.progress.emit(int((i / total) * 100), f"Processing {filename}...")

                # Extract text, metadata, and references
                with PDFProcessor(pdf_path) as processor:
                    metadata = processor.extract_metadata(use_semantic_scholar=True)
                    full_text = processor.extract_text(max_pages=10)  # Limit for speed
                    references = processor.extract_references()  # Extract references

                # Add to database
                paper_id = db.add_paper(
                    title=metadata['title'],
                    pdf_path=pdf_path,
                    authors=metadata.get('authors'),
                    year=metadata.get('year'),
                    journal=metadata.get('journal'),
                    doi=metadata.get('doi'),
                    arxiv_id=metadata.get('arxiv_id'),
                    abstract=metadata.get('abstract'),
                    num_pages=metadata['num_pages'],
                    file_size=metadata['file_size']
                )

                # Log metadata source for debugging
                source = metadata.get('source', 'unknown')
                if source == 'semantic_scholar':
                    print(f"✓ {filename}: Metadata from Semantic Scholar")
                else:
                    print(f"⚠ {filename}: Using heuristic extraction")

                # Extract keywords (YAKE for speed)
                keywords = self.keyword_extractor.extract_from_paper(
                    title=metadata['title'],
                    abstract=metadata.get('abstract'),
                    full_text=full_text[:5000],
                    method='yake',
                    top_n=10
                )

                # Save keywords
                db.add_keywords(paper_id, keywords, method='yake')

                # Save references
                if references:
                    db.add_references(paper_id, references)
                    print(f"  → Extracted {len(references)} references")

                # Update full-text index
                db.update_full_text_index(paper_id, full_text)

                imported_ids.append(paper_id)

            except Exception as e:
                self.error.emit(f"Error processing {filename}: {str(e)}")
                continue

        # Close database connection
        db.close()

        self.progress.emit(100, "Import complete!")
        self.finished.emit(imported_ids)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, db_path: str = "data/papers.db"):
        super().__init__()
        self.db_path = db_path
        self.db = Database(db_path)
        self.current_paper: Optional[Paper] = None

        self.init_ui()
        self.load_papers()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Research Paper Manager")
        self.setGeometry(100, 100, 1400, 900)

        # Create menu bar
        self.create_menu_bar()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Top toolbar
        toolbar = self.create_toolbar()
        main_layout.addLayout(toolbar)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search papers by title, author, or keywords...")
        self.search_input.returnPressed.connect(self.search_papers)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_papers)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        main_layout.addLayout(search_layout)

        # Splitter for paper list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Paper list (table)
        self.paper_table = QTableWidget()
        self.paper_table.setColumnCount(4)
        self.paper_table.setHorizontalHeaderLabels(["Title", "Authors", "Year", "Keywords"])
        self.paper_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.paper_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.paper_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.paper_table.itemSelectionChanged.connect(self.on_paper_selected)

        # Right: Paper details
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        details_label = QLabel("Paper Details")
        details_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        details_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)

        # Keywords section
        keywords_label = QLabel("Keywords")
        keywords_label.setStyleSheet("font-weight: bold;")
        details_layout.addWidget(keywords_label)

        self.keywords_list = QListWidget()
        self.keywords_list.setMaximumHeight(150)
        details_layout.addWidget(self.keywords_list)

        # Add to splitter
        splitter.addWidget(self.paper_table)
        splitter.addWidget(details_widget)
        splitter.setSizes([800, 600])

        main_layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        import_action = QAction("Import PDFs...", self)
        import_action.setShortcut("Ctrl+O")
        import_action.triggered.connect(self.import_pdfs)
        file_menu.addAction(import_action)

        export_bibtex_action = QAction("Export to BibTeX...", self)
        export_bibtex_action.setShortcut("Ctrl+E")
        export_bibtex_action.triggered.connect(self.export_bibtex)
        file_menu.addAction(export_bibtex_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        download_arxiv_action = QAction("Download from arXiv...", self)
        download_arxiv_action.triggered.connect(self.download_arxiv)
        tools_menu.addAction(download_arxiv_action)

        view_network_action = QAction("View Citation Network", self)
        view_network_action.setShortcut("Ctrl+N")
        view_network_action.triggered.connect(self.view_citation_network)
        tools_menu.addAction(view_network_action)

        match_citations_action = QAction("Match Citations...", self)
        match_citations_action.setShortcut("Ctrl+M")
        match_citations_action.triggered.connect(self.match_citations)
        tools_menu.addAction(match_citations_action)

        tools_menu.addSeparator()

        diagnostics_action = QAction("Run Diagnostics...", self)
        diagnostics_action.triggered.connect(self.run_diagnostics)
        tools_menu.addAction(diagnostics_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        preferences_action = QAction("Preferences...", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self.open_settings)
        settings_menu.addAction(preferences_action)

    def create_toolbar(self) -> QHBoxLayout:
        """Create toolbar with action buttons."""
        layout = QHBoxLayout()

        add_btn = QPushButton("Add PDFs")
        add_btn.clicked.connect(self.import_pdfs)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_papers)

        export_btn = QPushButton("Export BibTeX")
        export_btn.clicked.connect(self.export_bibtex)

        layout.addWidget(add_btn)
        layout.addWidget(refresh_btn)
        layout.addWidget(export_btn)
        layout.addStretch()

        return layout

    def import_pdfs(self):
        """Import PDF files into the library."""
        file_dialog = QFileDialog()
        pdf_paths, _ = file_dialog.getOpenFileNames(
            self,
            "Select PDF files",
            "",
            "PDF Files (*.pdf)"
        )

        if not pdf_paths:
            return

        # Show progress dialog
        progress = QProgressDialog("Importing PDFs...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        # Create import thread (pass db_path, not db object for thread safety)
        self.import_thread = PDFImportThread(pdf_paths, self.db_path)
        self.import_thread.progress.connect(
            lambda pct, msg: (progress.setValue(pct), progress.setLabelText(msg))
        )
        self.import_thread.finished.connect(
            lambda ids: self.on_import_finished(ids, progress)
        )
        self.import_thread.error.connect(
            lambda msg: QMessageBox.warning(self, "Import Error", msg)
        )

        self.import_thread.start()

    def on_import_finished(self, paper_ids: List[int], progress_dialog):
        """Handle import completion."""
        progress_dialog.close()
        QMessageBox.information(
            self,
            "Import Complete",
            f"Successfully imported {len(paper_ids)} paper(s)."
        )
        self.load_papers()

    def load_papers(self):
        """Load all papers from database and populate table."""
        papers = self.db.get_all_papers()

        self.paper_table.setRowCount(len(papers))

        for row, paper_dict in enumerate(papers):
            paper = Paper.from_dict(paper_dict)

            # Title
            self.paper_table.setItem(row, 0, QTableWidgetItem(paper.title))

            # Authors
            self.paper_table.setItem(row, 1, QTableWidgetItem(paper.author_string))

            # Year
            self.paper_table.setItem(row, 2, QTableWidgetItem(paper.year_string))

            # Keywords
            keywords = self.db.get_keywords(paper.id)
            keyword_str = ", ".join([kw for kw, _ in keywords[:3]])
            self.paper_table.setItem(row, 3, QTableWidgetItem(keyword_str))

            # Store paper ID in row
            self.paper_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, paper.id)

        self.statusBar().showMessage(f"Loaded {len(papers)} paper(s)")

    def on_paper_selected(self):
        """Handle paper selection in table."""
        selected_items = self.paper_table.selectedItems()
        if not selected_items:
            return

        # Get paper ID from first column
        paper_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        paper_dict = self.db.get_paper(paper_id)

        if not paper_dict:
            return

        self.current_paper = Paper.from_dict(paper_dict)

        # Display details with proper abstract formatting
        abstract_text = self.current_paper.abstract or 'No abstract available.'

        # Show abstract length if available
        abstract_info = ""
        if self.current_paper.abstract:
            abstract_info = f" ({len(self.current_paper.abstract)} characters)"

        details_html = f"""
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h2 {{ color: #2c3e50; margin-bottom: 10px; }}
            h3 {{ color: #34495e; margin-top: 15px; margin-bottom: 8px; }}
            .metadata {{ margin: 5px 0; }}
            .abstract {{
                text-align: justify;
                line-height: 1.6;
                padding: 10px;
                background-color: #f9f9f9;
                border-left: 3px solid #3498db;
            }}
        </style>
        <h2>{self.current_paper.title}</h2>
        <div class="metadata"><b>Authors:</b> {', '.join(self.current_paper.authors) if self.current_paper.authors else 'Unknown'}</div>
        <div class="metadata"><b>Year:</b> {self.current_paper.year or 'Unknown'}</div>
        <div class="metadata"><b>Journal:</b> {self.current_paper.journal or 'N/A'}</div>
        <div class="metadata"><b>DOI:</b> {self.current_paper.doi or 'N/A'}</div>
        <div class="metadata"><b>Pages:</b> {self.current_paper.num_pages or 'N/A'}</div>
        <div class="metadata"><b>File:</b> <small>{self.current_paper.pdf_path}</small></div>
        <hr>
        <h3>Abstract{abstract_info}</h3>
        <div class="abstract">{abstract_text}</div>
        """

        self.details_text.setHtml(details_html)

        # Display keywords
        self.keywords_list.clear()
        keywords = self.db.get_keywords(paper_id)
        for keyword, score in keywords:
            self.keywords_list.addItem(f"{keyword} ({score:.2f})")

    def search_papers(self):
        """Search papers using full-text search."""
        query = self.search_input.text().strip()

        if not query:
            self.load_papers()
            return

        # Perform FTS search
        results = self.db.search_papers(query, limit=100)

        # Update table with results
        self.paper_table.setRowCount(len(results))

        for row, paper_dict in enumerate(results):
            paper = Paper.from_dict(paper_dict)

            self.paper_table.setItem(row, 0, QTableWidgetItem(paper.title))
            self.paper_table.setItem(row, 1, QTableWidgetItem(paper.author_string))
            self.paper_table.setItem(row, 2, QTableWidgetItem(paper.year_string))

            keywords = self.db.get_keywords(paper.id)
            keyword_str = ", ".join([kw for kw, _ in keywords[:3]])
            self.paper_table.setItem(row, 3, QTableWidgetItem(keyword_str))

            self.paper_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, paper.id)

        self.statusBar().showMessage(f"Found {len(results)} result(s)")

    def export_bibtex(self):
        """Export all papers to BibTeX file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export BibTeX",
            "library.bib",
            "BibTeX Files (*.bib)"
        )

        if not file_path:
            return

        papers = self.db.get_all_papers()
        bibtex_entries = []

        for paper_dict in papers:
            paper = Paper.from_dict(paper_dict)
            bibtex_entries.append(paper.to_bibtex())

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(bibtex_entries))

        QMessageBox.information(
            self,
            "Export Complete",
            f"Exported {len(papers)} paper(s) to {file_path}"
        )

    def download_arxiv(self):
        """Download papers from arXiv."""
        # Placeholder - will be implemented with a dialog
        QMessageBox.information(
            self,
            "arXiv Download",
            "arXiv download feature coming soon!\n\n"
            "For now, use: python -m src.utils.arxiv_downloader"
        )

    def view_citation_network(self):
        """View citation network visualization."""
        try:
            dialog = CitationNetworkDialog(self.db, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Citation Network Error",
                f"Failed to open citation network:\n{str(e)}"
            )

    def match_citations(self):
        """Match references to papers in the database to build citation network."""
        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Match Citations",
            "This will attempt to match all references in your papers to create citation links.\n\n"
            "Matching strategies:\n"
            "• Exact DOI matching (highest confidence)\n"
            "• Exact arXiv ID matching\n"
            "• Title similarity matching\n\n"
            "This may take a few moments. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # Create progress dialog
        progress = QProgressDialog("Matching citations...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()

        try:
            # Run citation matching
            matcher = CitationMatcher(self.db)
            stats = matcher.match_all_papers()

            progress.close()

            # Show results
            result_message = (
                f"Citation Matching Complete!\n\n"
                f"Papers processed: {stats['total_papers_processed']}\n"
                f"Total references: {stats['total_references']}\n"
                f"Matched: {stats['total_matched']}\n"
                f"Unmatched: {stats['total_unmatched']}\n\n"
                f"Match confidence breakdown:\n"
                f"  High (DOI/arXiv): {stats['confidence_breakdown']['high']}\n"
                f"  Medium (strong title): {stats['confidence_breakdown']['medium']}\n"
                f"  Low (weak title): {stats['confidence_breakdown']['low']}\n\n"
                f"Papers with at least one match: {stats['papers_with_matches']}"
            )

            QMessageBox.information(self, "Citation Matching Results", result_message)

        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self,
                "Citation Matching Error",
                f"Failed to match citations:\n{str(e)}"
            )

    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def run_diagnostics(self):
        """Run diagnostic script."""
        QMessageBox.information(
            self,
            "Run Diagnostics",
            "To run comprehensive diagnostics:\n\n"
            "Open terminal and run:\n"
            "  python diagnose_and_fix.py\n\n"
            "Available options:\n"
            "  --re-extract    Re-extract metadata with Semantic Scholar\n"
            "  --rebuild-index Rebuild search index\n\n"
            "This will test:\n"
            "• Semantic Scholar API connectivity\n"
            "• Database contents and abstracts\n"
            "• Search functionality\n"
            "• And offer automated fixes"
        )

    def closeEvent(self, event):
        """Handle window close event."""
        self.db.close()
        event.accept()
