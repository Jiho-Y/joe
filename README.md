# Research Paper Manager

A desktop application for managing academic research papers with PDF processing, automatic metadata extraction, keyword extraction, and citation network visualization.

## Features

### Current (v0.2 - Enhanced MVP)
- ✅ PDF import and organization
- ✅ **Semantic Scholar API integration** (95%+ accurate metadata)
- ✅ Automatic metadata extraction with 3-tier fallback system
- ✅ Full abstract extraction
- ✅ YAKE keyword extraction
- ✅ **Enhanced full-text search** (SQLite FTS5 with fallback)
- ✅ BibTeX export
- ✅ Clean PySide6 (Qt6) interface
- ✅ arXiv paper downloader
- ✅ **Settings dialog** for configuration
- ✅ **Diagnostic and repair tools**
- ✅ Configuration system with API key support

### Planned
- 🔄 KeyBERT for improved keyword accuracy
- 🔄 Reference parsing and citation matching
- 🔄 Citation network visualization with NetworkX
- 🔄 Advanced search filters
- 🔄 Batch re-extraction for existing papers

## Requirements

- **Python**: 3.10 or higher
- **Operating System**: macOS (recommended), Linux, or Windows
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB for application + space for PDF library

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd joe
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: If installation fails for any package, you may need to install system dependencies:

**macOS**:
```bash
brew install python-tk
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install python3-tk python3-dev
```

### 4. Verify Installation

```bash
# Check Python version
python --version  # Should be 3.10+

# Check if PySide6 is installed
python -c "from PySide6.QtWidgets import QApplication; print('PySide6 OK')"
```

## Quick Start

### First Time Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run diagnostics:**
   ```bash
   python diagnose_and_fix.py
   ```
   This will test your setup and verify everything works.

3. **Run the application:**
   ```bash
   python main.py
   ```

4. **Download test papers from arXiv:**
   ```bash
   python -m src.utils.arxiv_downloader
   ```
   This will download papers to the `test_pdfs/` directory.

### For Existing Users (Upgrading from v0.1)

If you have papers already imported:

```bash
# Re-extract metadata with Semantic Scholar for better accuracy
python diagnose_and_fix.py --re-extract

# Or rebuild search index if search isn't working
python diagnose_and_fix.py --rebuild-index
```

See `QUICK_START.md` for detailed upgrade instructions.

### Adding Your Own PDFs

1. Click **"Add PDFs"** button (or File → Import PDFs)
2. Select one or more PDF files
3. Wait for processing (metadata extraction + keyword extraction)
4. Papers will appear in the main table

### Searching Papers

- **Simple search**: Type keywords in the search box and press Enter
- **Full-text search**: Searches across title, authors, abstract, and full text
- **Clear search**: Empty the search box and press Enter to show all papers

### Exporting to BibTeX

1. Click **"Export BibTeX"** button (or File → Export to BibTeX)
2. Choose save location
3. All papers in your library will be exported

## Project Structure

```
joe/
├── main.py                       # Application entry point
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── QUICK_START.md                # Quick start guide for users
├── FIXES_AND_IMPROVEMENTS.md     # Detailed changelog
├── diagnose_and_fix.py           # Diagnostic and repair tool
├── test_semantic_scholar.py      # Comprehensive test suite
│
├── src/
│   ├── ui/
│   │   ├── main_window.py        # PySide6 main window
│   │   └── settings_dialog.py    # Settings/preferences dialog
│   ├── core/
│   │   ├── database.py           # SQLite database + FTS5 search
│   │   ├── pdf_processor.py      # PDF text extraction (PyMuPDF)
│   │   └── metadata_extractor.py # Keyword extraction (YAKE)
│   ├── utils/
│   │   ├── config.py             # Configuration management
│   │   ├── semantic_scholar.py   # Semantic Scholar API client
│   │   └── arxiv_downloader.py   # arXiv paper downloader
│   └── models/
│       └── paper.py              # Paper data model
│
├── data/
│   ├── papers.db                 # SQLite database (created at runtime)
│   ├── config.json               # User configuration
│   └── pdfs/                     # User PDF storage
│
├── test_pdfs/                    # Downloaded test papers from arXiv
│
└── tests/                        # Unit tests
```

## Usage Guide

### Basic Workflow

1. **Import Papers**
   - Add PDFs via "Add PDFs" button
   - Or download from arXiv using `python -m src.utils.arxiv_downloader`

2. **Browse and Search**
   - View all papers in the main table
   - Click a paper to see details (abstract, keywords, etc.)
   - Use search box for full-text search

3. **Export Citations**
   - Export to BibTeX for use with LaTeX, Zotero, Mendeley, etc.

### Keyboard Shortcuts

- **Ctrl+O**: Import PDFs
- **Ctrl+E**: Export to BibTeX
- **Ctrl+,**: Open Settings/Preferences
- **Ctrl+N**: View Citation Network (coming soon)
- **Ctrl+Q**: Quit application

## Providing Your PDF Files

### Option 1: Direct Copy (Recommended)
```bash
# Copy your PDFs to the test_pdfs directory
cp /path/to/your/papers/*.pdf test_pdfs/

# Then import via the GUI
python main.py
# Click "Add PDFs" → Select files from test_pdfs/
```

### Option 2: Import from Any Location
- In the GUI, click "Add PDFs"
- Navigate to wherever your PDFs are stored
- Select files (can select multiple with Cmd+Click or Ctrl+Click)

### Option 3: Use arXiv Downloader
```bash
# Download papers by keyword
python -m src.utils.arxiv_downloader

# Or use as Python module:
python -c "from src.utils.arxiv_downloader import download_test_dataset; download_test_dataset()"
```

## Troubleshooting

### General Issues - Run Diagnostics First!
```bash
python diagnose_and_fix.py
```
This will test all critical functionality and suggest fixes.

### "ModuleNotFoundError: No module named 'PySide6'"
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

### "fitz module not found"
```bash
# PyMuPDF sometimes has import issues
pip uninstall PyMuPDF
pip install PyMuPDF==1.23.26
```

### Search not working
```bash
# Rebuild search index
python diagnose_and_fix.py --rebuild-index
```

### Abstracts missing
```bash
# Re-extract metadata with Semantic Scholar
python diagnose_and_fix.py --re-extract
```

### Database errors
```bash
# Delete and recreate database
rm data/papers.db
python main.py  # Will create fresh database
```

### GUI doesn't appear
```bash
# Check if display is available
echo $DISPLAY  # On Linux/macOS

# Try running with verbose output
python main.py --verbose
```

For detailed troubleshooting, see `FIXES_AND_IMPROVEMENTS.md`

## Development Roadmap

### Week 1-2: Core Functionality (Current)
- [x] Project structure
- [x] PyQt6 UI skeleton
- [x] PDF text extraction (PyMuPDF)
- [x] SQLite database
- [x] YAKE keyword extraction
- [x] Full-text search
- [x] BibTeX export
- [x] arXiv downloader

### Week 2: GROBID Integration
- [ ] Docker setup instructions
- [ ] GROBID API client
- [ ] Structured metadata extraction
- [ ] Reference parsing

### Week 3: Advanced Features
- [ ] KeyBERT integration
- [ ] Citation matching algorithm
- [ ] Advanced search filters
- [ ] Batch processing improvements

### Week 4: Citation Network
- [ ] NetworkX graph construction
- [ ] Cytoscape.js visualization
- [ ] Interactive graph navigation
- [ ] Export network data

### Week 5-6: Polish & Distribution
- [ ] Bug fixes
- [ ] Performance optimization
- [ ] PyInstaller packaging
- [ ] User documentation

## Testing

### Run Unit Tests
```bash
pytest tests/
```

### Test PDF Processing
```bash
python -c "
from src.core.pdf_processor import process_pdf
result = process_pdf('test_pdfs/your_paper.pdf')
print(result['title'])
print(result['authors'])
"
```

### Test Keyword Extraction
```bash
python -c "
from src.core.metadata_extractor import KeywordExtractor
extractor = KeywordExtractor()
text = 'Your paper abstract or text here...'
keywords = extractor.extract_yake(text, top_n=5)
print(keywords)
"
```

## Contributing

This is a personal research tool, but contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License (see LICENSE file)

## Acknowledgments

Built with:
- **PySide6 (Qt6)** - Cross-platform GUI framework
- **Semantic Scholar API** - Academic paper metadata (200M+ papers)
- **PyMuPDF** - Fast PDF processing
- **YAKE** - Keyword extraction
- **SQLite FTS5** - Full-text search
- **arXiv API** - Academic paper access

## Support

For issues or questions:
1. Check this README's Troubleshooting section
2. Review the code comments and docstrings
3. Open an issue on GitHub

## Next Steps for Users

### Immediate (After Setup)
1. ✅ Run diagnostics: `python diagnose_and_fix.py`
2. ✅ Run application: `python main.py`
3. ✅ Download test papers: `python -m src.utils.arxiv_downloader`
4. ✅ Import PDFs and verify abstracts display
5. ✅ Test search functionality
6. ✅ Configure settings (optional): Settings → Preferences

### For Existing Users (Upgrading)
1. ✅ Run: `python diagnose_and_fix.py --re-extract` to update metadata
2. ✅ Test search: `python diagnose_and_fix.py --rebuild-index` if needed
3. ✅ See `QUICK_START.md` for detailed upgrade guide

### Future Features
1. KeyBERT integration for better keyword extraction
2. Citation network visualization
3. Reference parsing and matching
4. Advanced filtering and sorting

---

**Version**: 0.2.0 (Enhanced MVP - Semantic Scholar Integration)
**Last Updated**: 2025-11-14

## Recent Updates (v0.2.0)

- ✅ Added Semantic Scholar API integration (95%+ metadata accuracy)
- ✅ Fixed search functionality (complete FTS5 rewrite)
- ✅ Fixed abstract display (full text now shows)
- ✅ Added settings dialog with API key configuration
- ✅ Created diagnostic and repair tools
- ✅ Added configuration management system
- ✅ Improved import logging and error handling
- ✅ Updated from PyQt6 to PySide6 for better M4 Mac compatibility

See `FIXES_AND_IMPROVEMENTS.md` for detailed changelog.
