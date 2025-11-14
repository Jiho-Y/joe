"""
PDF processing module using PyMuPDF (fitz).
Handles text extraction, metadata parsing, and page-level operations.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


class PDFProcessor:
    """Process PDF files to extract text and metadata."""

    def __init__(self, pdf_path: str):
        """
        Initialize PDF processor.

        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self.doc = fitz.open(str(self.pdf_path))
        self.num_pages = len(self.doc)

    def extract_text(self, max_pages: Optional[int] = None) -> str:
        """
        Extract all text from PDF.

        Args:
            max_pages: Maximum number of pages to process (None = all)

        Returns:
            Extracted text as a single string
        """
        pages_to_process = min(max_pages or self.num_pages, self.num_pages)
        text_parts = []

        for page_num in range(pages_to_process):
            page = self.doc[page_num]
            text = page.get_text("text")
            text_parts.append(text)

        return "\n\n".join(text_parts)

    def extract_text_by_page(self) -> List[str]:
        """
        Extract text page by page.

        Returns:
            List of text strings, one per page
        """
        return [page.get_text("text") for page in self.doc]

    def extract_metadata(self) -> Dict[str, any]:
        """
        Extract PDF metadata and infer additional information.

        Returns:
            Dictionary with metadata fields
        """
        # Get embedded PDF metadata
        pdf_metadata = self.doc.metadata

        # Extract first page text for title/author inference
        first_page_text = self.doc[0].get_text("text") if self.num_pages > 0 else ""

        # Get file information
        file_size = self.pdf_path.stat().st_size

        metadata = {
            'pdf_path': str(self.pdf_path),
            'num_pages': self.num_pages,
            'file_size': file_size,
            'embedded_title': pdf_metadata.get('title', ''),
            'embedded_author': pdf_metadata.get('author', ''),
            'embedded_subject': pdf_metadata.get('subject', ''),
            'creation_date': pdf_metadata.get('creationDate', ''),
            'modification_date': pdf_metadata.get('modDate', ''),
        }

        # Try to infer title from first page (often in large font)
        inferred_title = self._infer_title_from_text(first_page_text)
        if inferred_title and not metadata['embedded_title']:
            metadata['title'] = inferred_title
        else:
            metadata['title'] = metadata['embedded_title'] or self.pdf_path.stem

        # Try to infer authors
        inferred_authors = self._infer_authors_from_text(first_page_text)
        metadata['authors'] = inferred_authors

        # Try to extract abstract
        abstract = self._extract_abstract(self.extract_text(max_pages=3))
        metadata['abstract'] = abstract

        # Try to infer year
        year = self._infer_year_from_text(first_page_text)
        metadata['year'] = year

        return metadata

    def _infer_title_from_text(self, text: str) -> Optional[str]:
        """
        Infer paper title from first page text.
        Usually the title is in the first few lines, often capitalized.

        Args:
            text: First page text

        Returns:
            Inferred title or None
        """
        lines = text.split('\n')
        candidates = []

        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            line = line.strip()

            # Skip very short lines or lines with weird characters
            if len(line) < 10 or len(line) > 200:
                continue

            # Skip lines that look like headers/footers
            if re.search(r'^\d+$|^page \d+|copyright|proceedings', line, re.I):
                continue

            # Title is often in title case or all caps
            if line[0].isupper() and len(line.split()) > 3:
                candidates.append(line)

        # Return the longest candidate (likely the full title)
        if candidates:
            return max(candidates, key=len)

        return None

    def _infer_authors_from_text(self, text: str) -> List[str]:
        """
        Infer author names from first page text with improved patterns.

        Args:
            text: First page text

        Returns:
            List of inferred author names
        """
        authors = []

        # Look for explicit author section first
        author_section_patterns = [
            r'(?:Authors?|By)\s*[:\-]?\s*\n\s*(.+?)(?:\n\n|Abstract|ABSTRACT)',
            r'(?:Authors?|By)\s*[:\-]\s*(.+?)(?:\n\n|$)',
        ]

        for pattern in author_section_patterns:
            match = re.search(pattern, text[:2000], re.DOTALL | re.IGNORECASE)
            if match:
                author_text = match.group(1)
                # Extract names from this section
                names = self._extract_names_from_text(author_text)
                if names:
                    return names[:15]  # Max 15 authors

        # Fallback: look for names after title (usually 2nd-5th line)
        lines = text.split('\n')
        for i, line in enumerate(lines[1:10]):  # Skip first line (usually title)
            line = line.strip()

            # Skip short lines, URLs, dates, etc.
            if len(line) < 5 or '@' in line or 'http' in line:
                continue

            # Look for name patterns in this line
            names = self._extract_names_from_text(line)
            if names:
                authors.extend(names)

        # Deduplicate and return
        unique_authors = []
        seen = set()
        for author in authors:
            if author.lower() not in seen:
                seen.add(author.lower())
                unique_authors.append(author)

        return unique_authors[:15]  # Max 15 authors

    def _extract_names_from_text(self, text: str) -> List[str]:
        """
        Extract person names from text using multiple patterns.

        Args:
            text: Text containing potential names

        Returns:
            List of extracted names
        """
        names = []

        # Pattern 1: First Middle Last (e.g., John A. Smith)
        pattern1 = r'\b[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+\b'

        # Pattern 2: First Last (e.g., John Smith)
        pattern2 = r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b'

        # Pattern 3: Last, First (e.g., Smith, John)
        pattern3 = r'\b[A-Z][a-z]+,\s*[A-Z][a-z]+\b'

        # Pattern 4: Initials + Last (e.g., J.A. Smith)
        pattern4 = r'\b[A-Z]\.[A-Z]\.\s+[A-Z][a-z]+\b'

        all_patterns = [pattern1, pattern2, pattern3, pattern4]

        for pattern in all_patterns:
            matches = re.findall(pattern, text)
            names.extend(matches)

        # Filter out false positives
        stopwords = {
            'The', 'This', 'That', 'These', 'Those', 'They', 'There',
            'University', 'Institute', 'Department', 'College', 'School',
            'Science', 'Engineering', 'Technology', 'Research', 'Center',
            'Journal', 'Conference', 'Proceedings', 'International', 'National',
            'American', 'European', 'Asian', 'Society', 'Association',
            'All Rights', 'Copyright', 'Permission', 'Published'
        }

        filtered_names = []
        for name in names:
            # Clean up
            name = name.strip(',. ')

            # Skip if first word is a stopword
            first_word = name.split()[0]
            if first_word in stopwords:
                continue

            # Skip if contains numbers
            if any(char.isdigit() for char in name):
                continue

            # Skip if too short
            if len(name) < 5:
                continue

            filtered_names.append(name)

        return filtered_names

    def _extract_abstract(self, text: str) -> Optional[str]:
        """
        Extract abstract from paper text with improved pattern matching.

        Args:
            text: First few pages of text

        Returns:
            Abstract text or None
        """
        # Multiple patterns to catch different abstract formats
        patterns = [
            # Pattern 1: Abstract followed by content until double newline or section
            r'(?:abstract|ABSTRACT|Abstract)\s*[:\-—]?\s*\n\s*(.+?)(?:\n\n\s*(?:[A-Z]|Keywords|Introduction|1\.|I\.))',

            # Pattern 2: Abstract in same line
            r'(?:abstract|ABSTRACT|Abstract)\s*[:\-—]\s*(.+?)(?:\n\n|Keywords|Introduction)',

            # Pattern 3: Abstract with Keywords marker
            r'(?:abstract|ABSTRACT|Abstract)\s*[:\-—]?\s*\n\s*(.+?)(?:Keywords|KEYWORDS|Key words)',

            # Pattern 4: Very flexible - abstract until Introduction or section 1
            r'(?:abstract|ABSTRACT|Abstract)[\s\S]{0,50}?(.+?)(?:Introduction|INTRODUCTION|1\s+Introduction|I\s+INTRODUCTION|\n1\.)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()

                # Clean up
                abstract = re.sub(r'\s+', ' ', abstract)  # Multiple spaces to single
                abstract = re.sub(r'\n', ' ', abstract)   # Newlines to spaces

                # Remove common artifacts
                abstract = re.sub(r'^\d+\s*', '', abstract)  # Leading numbers
                abstract = abstract.strip('.,;:')

                # Validate: should be at least 50 chars and not too long
                if 50 <= len(abstract) <= 3000:
                    return abstract[:2000]  # Limit but allow longer abstracts

        return None

    def _infer_year_from_text(self, text: str) -> Optional[int]:
        """
        Infer publication year from text with improved pattern matching.

        Args:
            text: First page text

        Returns:
            Year as integer or None
        """
        # Priority 1: Look for copyright/published year
        copyright_patterns = [
            r'[©Cc]opyright\s+(?:©\s*)?(\d{4})',
            r'[Pp]ublished\s+(?:in\s+)?(\d{4})',
            r'[Pp]ublication\s+[Yy]ear[:\s]+(\d{4})',
            r'[Pp]ublished:\s+\w+\s+\d+,?\s+(\d{4})',
        ]

        for pattern in copyright_patterns:
            match = re.search(pattern, text[:3000])
            if match:
                year = int(match.group(1))
                if 1950 <= year <= 2030:  # Reasonable range
                    return year

        # Priority 2: Look for date patterns (Month Day, Year or Day Month Year)
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(\d{4})\b',
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text[:3000], re.IGNORECASE)
            if match:
                year = int(match.group(1))
                if 1950 <= year <= 2030:
                    return year

        # Priority 3: Look for any 4-digit year in reasonable range
        year_pattern = r'\b(19\d{2}|20[0-2]\d)\b'
        matches = re.findall(year_pattern, text[:2000])

        if matches:
            # Filter to reasonable range and return most recent
            years = [int(y) for y in matches if 1950 <= int(y) <= 2030]
            if years:
                return max(years)

        return None

    def extract_references(self) -> List[str]:
        """
        Extract references section from PDF.
        This is a basic extraction; GROBID will do structured parsing.

        Returns:
            List of reference strings
        """
        # Get text from last 30% of document (references usually at end)
        start_page = int(self.num_pages * 0.7)
        end_text = ""

        for page_num in range(start_page, self.num_pages):
            end_text += self.doc[page_num].get_text("text") + "\n"

        # Find "References" section
        ref_pattern = r'(?:references|REFERENCES|bibliography|BIBLIOGRAPHY)\s*\n(.+)'
        match = re.search(ref_pattern, end_text, re.DOTALL | re.IGNORECASE)

        if not match:
            return []

        ref_text = match.group(1)

        # Split by common reference patterns
        # Pattern: [1], [2], etc. or 1., 2., etc.
        references = re.split(r'\n\[\d+\]|\n\d+\.', ref_text)

        # Clean and filter
        references = [ref.strip() for ref in references if len(ref.strip()) > 50]

        return references[:100]  # Limit to 100 references

    def get_page_count(self) -> int:
        """Get number of pages in PDF."""
        return self.num_pages

    def get_file_size(self) -> int:
        """Get file size in bytes."""
        return self.pdf_path.stat().st_size

    def close(self):
        """Close PDF document."""
        self.doc.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def process_pdf(pdf_path: str) -> Dict:
    """
    Convenience function to process a PDF and return all extracted data.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with all extracted information
    """
    with PDFProcessor(pdf_path) as processor:
        metadata = processor.extract_metadata()
        full_text = processor.extract_text()
        references = processor.extract_references()

        return {
            **metadata,
            'full_text': full_text,
            'references': references,
        }
