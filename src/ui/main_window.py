"""
Main application window using PySide6 (Qt6).
Compatible with both PyQt6 and PySide6.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QLineEdit, QLabel,
    QSplitter, QTextEdit, QListWidget, QProgressDialog,
    QGroupBox, QToolBar, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QAction, QKeySequence, QDesktopServices, QIcon
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


class NumericTableWidgetItem(QTableWidgetItem):
    """QTableWidgetItem that sorts numerically instead of alphabetically."""

    def __lt__(self, other):
        """Compare items numerically for sorting."""
        # Get numeric values from UserRole data
        self_value = self.data(Qt.ItemDataRole.UserRole)
        other_value = other.data(Qt.ItemDataRole.UserRole)

        # If both are numbers, compare numerically
        if isinstance(self_value, (int, float)) and isinstance(other_value, (int, float)):
            return self_value < other_value

        # Otherwise, fall back to string comparison
        return super().__lt__(other)


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
        self.update_window_title()
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

        # Double-click to open PDF
        self.paper_table.doubleClicked.connect(self.open_pdf_preview)

        # Enable sorting by clicking column headers
        self.paper_table.setSortingEnabled(True)

        # Enable drag and drop for manual reordering
        self.paper_table.setDragEnabled(True)
        self.paper_table.setAcceptDrops(True)
        self.paper_table.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
        self.paper_table.setDefaultDropAction(Qt.DropAction.MoveAction)

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

        new_library_action = QAction("New Library...", self)
        new_library_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_library_action.triggered.connect(self.new_library)
        file_menu.addAction(new_library_action)

        open_library_action = QAction("Open Library...", self)
        open_library_action.setShortcut(QKeySequence.StandardKey.Open)  # Cmd+O on Mac, Ctrl+O on others
        open_library_action.triggered.connect(self.open_library)
        file_menu.addAction(open_library_action)

        file_menu.addSeparator()

        import_action = QAction("Import PDFs...", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self.import_pdfs)
        file_menu.addAction(import_action)

        import_folder_action = QAction("Import Folder...", self)
        import_folder_action.setShortcut(QKeySequence("Ctrl+Shift+I"))
        import_folder_action.triggered.connect(self.import_from_folder)
        file_menu.addAction(import_folder_action)

        file_menu.addSeparator()

        export_bibtex_action = QAction("Export to BibTeX...", self)
        export_bibtex_action.setShortcut(QKeySequence("Ctrl+E"))
        export_bibtex_action.triggered.connect(self.export_bibtex)
        file_menu.addAction(export_bibtex_action)

        file_menu.addSeparator()

        close_window_action = QAction("Close Window", self)
        close_window_action.setShortcut(QKeySequence.StandardKey.Close)  # Cmd+W on Mac
        close_window_action.triggered.connect(self.close)
        file_menu.addAction(close_window_action)

        exit_action = QAction("Quit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)  # Cmd+Q on Mac, Ctrl+Q on others
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        delete_action = QAction("Delete Paper", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)  # Delete key or Cmd+Backspace on Mac
        delete_action.triggered.connect(self.delete_selected_paper)
        edit_menu.addAction(delete_action)

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

        # View menu
        view_menu = menubar.addMenu("View")

        sort_by_title_action = QAction("Sort by Title", self)
        sort_by_title_action.triggered.connect(lambda: self.sort_papers(0))
        view_menu.addAction(sort_by_title_action)

        sort_by_authors_action = QAction("Sort by Authors", self)
        sort_by_authors_action.triggered.connect(lambda: self.sort_papers(1))
        view_menu.addAction(sort_by_authors_action)

        sort_by_year_action = QAction("Sort by Year", self)
        sort_by_year_action.triggered.connect(lambda: self.sort_papers(2))
        view_menu.addAction(sort_by_year_action)

        view_menu.addSeparator()

        sort_ascending_action = QAction("Sort Ascending", self)
        sort_ascending_action.setCheckable(True)
        sort_ascending_action.setChecked(True)
        sort_ascending_action.triggered.connect(self.toggle_sort_order)
        view_menu.addAction(sort_ascending_action)
        self.sort_ascending_action = sort_ascending_action

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        preferences_action = QAction("Preferences...", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self.open_settings)
        settings_menu.addAction(preferences_action)

    def create_toolbar(self) -> QHBoxLayout:
        """Create toolbar with logically grouped action buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(5)  # Reduce spacing between groups
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins

        # File Operations Group
        file_group = QGroupBox("File Operations")
        file_group.setStyleSheet("QGroupBox { padding-top: 10px; margin-top: 0px; font-weight: bold; }")
        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(5, 5, 5, 5)  # Reduce internal margins
        file_layout.setSpacing(3)  # Reduce spacing between buttons

        add_btn = QPushButton("➕ Import PDFs")
        add_btn.setToolTip("Import PDF files into library (Ctrl+I)")
        add_btn.clicked.connect(self.import_pdfs)

        folder_btn = QPushButton("📁 Import Folder")
        folder_btn.setToolTip("Import all PDFs from a folder and its subfolders (Ctrl+Shift+I)")
        folder_btn.clicked.connect(self.import_from_folder)

        export_btn = QPushButton("📤 Export BibTeX")
        export_btn.setToolTip("Export selected papers to BibTeX format (Ctrl+E)")
        export_btn.clicked.connect(self.export_bibtex)

        file_layout.addWidget(add_btn)
        file_layout.addWidget(folder_btn)
        file_layout.addWidget(export_btn)
        file_group.setLayout(file_layout)

        # Paper Management Group
        paper_group = QGroupBox("Paper Management")
        paper_group.setStyleSheet("QGroupBox { padding-top: 10px; margin-top: 0px; font-weight: bold; }")
        paper_layout = QHBoxLayout()
        paper_layout.setContentsMargins(5, 5, 5, 5)
        paper_layout.setSpacing(3)

        open_btn = QPushButton("🔍 Open PDF")
        open_btn.setToolTip("Open selected PDF in Preview (Double-click or press Space)")
        open_btn.clicked.connect(self.open_pdf_preview)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setToolTip("Delete selected paper (Delete key)")
        delete_btn.clicked.connect(self.delete_selected_paper)

        paper_layout.addWidget(open_btn)
        paper_layout.addWidget(delete_btn)
        paper_group.setLayout(paper_layout)

        # View Group
        view_group = QGroupBox("View")
        view_group.setStyleSheet("QGroupBox { padding-top: 10px; margin-top: 0px; font-weight: bold; }")
        view_layout = QHBoxLayout()
        view_layout.setContentsMargins(5, 5, 5, 5)
        view_layout.setSpacing(3)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setToolTip("Reload papers from database")
        refresh_btn.clicked.connect(self.load_papers)

        network_btn = QPushButton("🕸️ Citation Network")
        network_btn.setToolTip("View citation network (Ctrl+N)")
        network_btn.clicked.connect(self.view_citation_network)

        view_layout.addWidget(refresh_btn)
        view_layout.addWidget(network_btn)
        view_group.setLayout(view_layout)

        # Add groups to main layout
        layout.addWidget(file_group)
        layout.addWidget(paper_group)
        layout.addWidget(view_group)
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

    def import_from_folder(self):
        """Import all PDF files from a folder and its subfolders."""
        file_dialog = QFileDialog()
        folder_path = file_dialog.getExistingDirectory(
            self,
            "Select folder containing PDFs",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder_path:
            return

        # Find all PDF files recursively
        folder = Path(folder_path)
        pdf_paths = [str(p) for p in folder.rglob('*.pdf')]

        if not pdf_paths:
            QMessageBox.information(
                self,
                "No PDFs Found",
                f"No PDF files found in:\n{folder_path}\n\n"
                f"The folder and its subfolders were searched."
            )
            return

        # Confirm import
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Found {len(pdf_paths)} PDF file(s) in folder and subfolders.\n\n"
            f"Do you want to import all of them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Show progress dialog
        progress = QProgressDialog("Importing PDFs from folder...", "Cancel", 0, 100, self)
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

        # Temporarily disable sorting for faster loading
        self.paper_table.setSortingEnabled(False)
        self.paper_table.setRowCount(len(papers))

        for row, paper_dict in enumerate(papers):
            paper = Paper.from_dict(paper_dict)

            # Title
            title_item = QTableWidgetItem(paper.title)
            title_item.setData(Qt.ItemDataRole.UserRole, paper.id)  # Store paper ID
            self.paper_table.setItem(row, 0, title_item)

            # Authors
            authors_item = QTableWidgetItem(paper.author_string)
            self.paper_table.setItem(row, 1, authors_item)

            # Year - use NumericTableWidgetItem for proper numeric sorting
            year_item = NumericTableWidgetItem(paper.year_string)
            # Store numeric year for sorting (0 if no year, will sort to top)
            year_item.setData(Qt.ItemDataRole.UserRole, paper_dict.get('year') or 0)
            self.paper_table.setItem(row, 2, year_item)

            # Keywords
            keywords = self.db.get_keywords(paper.id)
            keyword_str = ", ".join([kw for kw, _ in keywords[:3]])
            keyword_item = QTableWidgetItem(keyword_str)
            self.paper_table.setItem(row, 3, keyword_item)

        # Re-enable sorting
        self.paper_table.setSortingEnabled(True)

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

    def delete_selected_paper(self):
        """Delete the currently selected paper."""
        selected_items = self.paper_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a paper to delete."
            )
            return

        # Get selected row
        row = self.paper_table.currentRow()
        if row < 0:
            return

        # Get paper ID from row (stored as hidden data)
        paper_id_item = self.paper_table.item(row, 0)
        if not paper_id_item:
            return

        # Get paper title for confirmation
        title = paper_id_item.text()

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete this paper?\n\n"
            f"Title: {title}\n\n"
            f"This will also delete:\n"
            f"• All keywords\n"
            f"• All references\n"
            f"• All citation relationships\n"
            f"• Full-text index\n\n"
            f"This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # Get paper ID from the row's user data
        # We need to store paper_id when loading papers
        paper_id = paper_id_item.data(Qt.ItemDataRole.UserRole)

        if not paper_id:
            QMessageBox.critical(self, "Error", "Could not determine paper ID.")
            return

        # Delete from database
        success = self.db.delete_paper(paper_id)

        if success:
            # Remove from table
            self.paper_table.removeRow(row)
            # Clear details panel
            self.paper_details.clear()
            self.keywords_list.clear()
            QMessageBox.information(
                self,
                "Deleted",
                f"Paper deleted successfully."
            )
        else:
            QMessageBox.critical(
                self,
                "Error",
                "Failed to delete paper."
            )

    def new_library(self):
        """Create a new library database."""
        file_dialog = QFileDialog()
        new_db_path, _ = file_dialog.getSaveFileName(
            self,
            "Create New Library",
            "data/",
            "Database Files (*.db)"
        )

        if not new_db_path:
            return

        # Ensure .db extension
        if not new_db_path.endswith('.db'):
            new_db_path += '.db'

        # Close current database
        self.db.close()

        # Create new database
        self.db_path = new_db_path
        self.db = Database(new_db_path)

        # Update UI
        self.update_window_title()
        self.load_papers()

        QMessageBox.information(
            self,
            "New Library",
            f"New library created:\n{Path(new_db_path).name}"
        )

    def open_library(self):
        """Open an existing library database."""
        file_dialog = QFileDialog()
        db_path, _ = file_dialog.getOpenFileName(
            self,
            "Open Library",
            "data/",
            "Database Files (*.db)"
        )

        if not db_path:
            return

        # Close current database
        self.db.close()

        # Open new database
        self.db_path = db_path
        self.db = Database(db_path)

        # Update UI
        self.update_window_title()
        self.load_papers()

        QMessageBox.information(
            self,
            "Library Opened",
            f"Opened library:\n{Path(db_path).name}"
        )

    def update_window_title(self):
        """Update window title with current library name."""
        db_name = Path(self.db_path).stem
        self.setWindowTitle(f"Research Paper Manager - {db_name}")

    def sort_papers(self, column: int):
        """
        Sort papers by the specified column.

        Args:
            column: Column index (0=Title, 1=Authors, 2=Year, 3=Keywords)
        """
        # Get current sort order
        order = Qt.SortOrder.AscendingOrder if self.sort_ascending_action.isChecked() else Qt.SortOrder.DescendingOrder

        # Sort the table
        self.paper_table.sortItems(column, order)

        # Update status bar
        column_names = ["Title", "Authors", "Year", "Keywords"]
        order_str = "ascending" if order == Qt.SortOrder.AscendingOrder else "descending"
        self.statusBar().showMessage(f"Sorted by {column_names[column]} ({order_str})")

    def toggle_sort_order(self):
        """Toggle between ascending and descending sort order."""
        is_ascending = self.sort_ascending_action.isChecked()
        self.sort_ascending_action.setText("Sort Ascending" if is_ascending else "Sort Descending")

    def open_pdf_preview(self):
        """Open selected PDF in system default viewer (Mac Preview)."""
        selected_items = self.paper_table.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a paper to open."
            )
            return

        # Get paper ID from first column
        row = self.paper_table.currentRow()
        if row < 0:
            return

        title_item = self.paper_table.item(row, 0)
        if not title_item:
            return

        paper_id = title_item.data(Qt.ItemDataRole.UserRole)
        paper_dict = self.db.get_paper(paper_id)

        if not paper_dict:
            QMessageBox.warning(
                self,
                "Paper Not Found",
                "Could not find paper in database."
            )
            return

        pdf_path = paper_dict.get('pdf_path')
        if not pdf_path or not Path(pdf_path).exists():
            QMessageBox.warning(
                self,
                "PDF Not Found",
                f"PDF file not found:\n{pdf_path}\n\n"
                f"The file may have been moved or deleted."
            )
            return

        # Open PDF with system default application
        # On Mac: Preview
        # On Windows: Default PDF viewer
        # On Linux: Default PDF viewer
        try:
            url = QUrl.fromLocalFile(str(Path(pdf_path).resolve()))
            success = QDesktopServices.openUrl(url)

            if not success:
                QMessageBox.critical(
                    self,
                    "Open Failed",
                    f"Failed to open PDF:\n{pdf_path}\n\n"
                    f"Please check if you have a PDF viewer installed."
                )
            else:
                self.statusBar().showMessage(f"Opened: {Path(pdf_path).name}", 3000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error opening PDF:\n{str(e)}"
            )

    def keyPressEvent(self, event):
        """Handle key press events."""
        # Space key to open PDF
        if event.key() == Qt.Key.Key_Space:
            if self.paper_table.hasFocus():
                self.open_pdf_preview()
                event.accept()
                return

        # Pass other events to parent
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle window close event."""
        self.db.close()
        event.accept()
