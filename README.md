# Research Paper Manager

A desktop application for managing academic research papers with PDF processing, automatic metadata extraction, keyword extraction, and citation network visualization.

## Features

### Current (v0.1 - Tier 1 MVP)
- ✅ PDF import and organization
- ✅ Automatic metadata extraction (title, authors, year, abstract)
- ✅ YAKE keyword extraction
- ✅ Full-text search (SQLite FTS5)
- ✅ BibTeX export
- ✅ Clean PyQt6 interface
- ✅ arXiv paper downloader

### Planned
- 🔄 GROBID integration for structured metadata extraction (Week 2)
- 🔄 KeyBERT for improved keyword accuracy (Week 2-3)
- 🔄 Reference parsing and citation matching (Week 3)
- 🔄 Citation network visualization with Cytoscape.js (Week 4)
- 🔄 Advanced search and filtering (Week 3)

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

# Check if PyQt6 is installed
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

## Quick Start

### Run the Application

```bash
python main.py
```

### Download Test Papers from arXiv

```bash
# Download 20 test papers from arXiv
python -m src.utils.arxiv_downloader
```

This will download papers to the `test_pdfs/` directory. You can then import them using the "Add PDFs" button in the application.

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
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── src/
│   ├── ui/
│   │   └── main_window.py # PyQt6 main window
│   ├── core/
│   │   ├── database.py    # SQLite database management
│   │   ├── pdf_processor.py      # PDF text extraction (PyMuPDF)
│   │   └── metadata_extractor.py # Keyword extraction (YAKE/KeyBERT)
│   ├── utils/
│   │   └── arxiv_downloader.py   # arXiv paper downloader
│   └── models/
│       └── paper.py       # Paper data model
│
├── data/
│   ├── papers.db          # SQLite database (created at runtime)
│   └── pdfs/              # User PDF storage
│
├── test_pdfs/             # Downloaded test papers from arXiv
│
└── tests/                 # Unit tests
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

### "ModuleNotFoundError: No module named 'PyQt6'"
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
- **PyQt6** - Cross-platform GUI framework
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
1. ✅ Run `python main.py` to verify GUI works
2. ✅ Download test papers: `python -m src.utils.arxiv_downloader`
3. ✅ Import PDFs and test basic functionality

### Week 2 (GROBID)
1. Install Docker Desktop for Mac
2. Run GROBID server (instructions will be provided)
3. Test improved metadata extraction

### Week 3-4 (Advanced Features)
1. Test citation network visualization
2. Provide feedback on accuracy
3. Request additional features

---

**Version**: 0.1.0 (MVP)
**Last Updated**: 2025-11-14
