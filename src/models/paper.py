"""
Data models for research papers.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class Paper:
    """Research paper data model."""

    id: Optional[int] = None
    title: str = ""
    authors: List[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    pdf_path: str = ""
    num_pages: Optional[int] = None
    file_size: Optional[int] = None
    added_date: Optional[int] = None
    modified_date: Optional[int] = None
    notes: Optional[str] = None

    # Transient fields (not in database)
    keywords: List[tuple] = None  # List of (keyword, score)
    references: List[str] = None

    def __post_init__(self):
        """Initialize mutable default values."""
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []
        if self.references is None:
            self.references = []

    @property
    def author_string(self) -> str:
        """Get authors as a formatted string."""
        if not self.authors:
            return "Unknown"

        if len(self.authors) == 1:
            return self.authors[0]
        elif len(self.authors) == 2:
            return f"{self.authors[0]} and {self.authors[1]}"
        else:
            return f"{self.authors[0]} et al."

    @property
    def year_string(self) -> str:
        """Get year as a string."""
        return str(self.year) if self.year else "Unknown"

    @property
    def citation_key(self) -> str:
        """
        Generate a BibTeX citation key.
        Format: FirstAuthorLastName_Year
        """
        if not self.authors or not self.year:
            # Fallback to truncated title
            safe_title = self.title[:20].replace(' ', '_')
            return safe_title

        # Get first author's last name
        first_author = self.authors[0]
        last_name = first_author.split()[-1] if ' ' in first_author else first_author

        return f"{last_name}_{self.year}"

    def to_bibtex(self) -> str:
        """
        Convert paper to BibTeX format.

        Returns:
            BibTeX entry as string
        """
        entry_type = "article"  # Default to article

        # Determine entry type
        if self.arxiv_id:
            entry_type = "misc"
        elif self.journal:
            entry_type = "article"

        lines = [f"@{entry_type}{{{self.citation_key},"]

        # Required fields
        if self.title:
            lines.append(f"  title = {{{self.title}}},")

        if self.authors:
            author_str = " and ".join(self.authors)
            lines.append(f"  author = {{{author_str}}},")

        if self.year:
            lines.append(f"  year = {{{self.year}}},")

        # Optional fields
        if self.journal:
            lines.append(f"  journal = {{{self.journal}}},")

        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")

        if self.arxiv_id:
            lines.append(f"  archivePrefix = {{arXiv}},")
            lines.append(f"  eprint = {{{self.arxiv_id}}},")

        if self.abstract:
            # Escape special LaTeX characters
            abstract = self.abstract.replace('%', '\\%').replace('&', '\\&')
            lines.append(f"  abstract = {{{abstract}}},")

        lines.append("}")

        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: dict) -> 'Paper':
        """Create Paper instance from dictionary."""
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            authors=data.get('authors', []),
            year=data.get('year'),
            journal=data.get('journal'),
            doi=data.get('doi'),
            arxiv_id=data.get('arxiv_id'),
            abstract=data.get('abstract'),
            pdf_path=data.get('pdf_path', ''),
            num_pages=data.get('num_pages'),
            file_size=data.get('file_size'),
            added_date=data.get('added_date'),
            modified_date=data.get('modified_date'),
            notes=data.get('notes')
        )
