"""
SQLite database management for the research paper manager.
Handles schema creation, queries, and data persistence.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json


class Database:
    """SQLite database manager for paper metadata and relationships."""

    def __init__(self, db_path: str = "data/papers.db"):
        """
        Initialize database connection and create tables if needed.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._create_tables()

    def _create_tables(self):
        """Create all required database tables."""
        cursor = self.conn.cursor()

        # Main papers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT,  -- JSON array of author names
                year INTEGER,
                journal TEXT,
                doi TEXT,
                arxiv_id TEXT,
                abstract TEXT,
                pdf_path TEXT UNIQUE NOT NULL,
                num_pages INTEGER,
                file_size INTEGER,
                added_date INTEGER NOT NULL,
                modified_date INTEGER,
                notes TEXT,
                UNIQUE(title, authors, year)
            )
        """)

        # Keywords table (many-to-many relationship)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                score REAL,  -- Relevance score from extraction algorithm
                extraction_method TEXT,  -- 'yake', 'keybert', 'manual'
                FOREIGN KEY(paper_id) REFERENCES Papers(id) ON DELETE CASCADE,
                UNIQUE(paper_id, keyword)
            )
        """)

        # PaperReferences table (parsed from PDF)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS PaperReferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                raw_text TEXT NOT NULL,  -- Original reference string
                parsed_title TEXT,
                parsed_authors TEXT,
                parsed_year INTEGER,
                parsed_venue TEXT,
                parsed_doi TEXT,
                FOREIGN KEY(paper_id) REFERENCES Papers(id) ON DELETE CASCADE
            )
        """)

        # Citations table (resolved relationships between papers)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citing_paper_id INTEGER NOT NULL,
                cited_paper_id INTEGER NOT NULL,
                confidence REAL DEFAULT 1.0,  -- Matching confidence
                FOREIGN KEY(citing_paper_id) REFERENCES Papers(id) ON DELETE CASCADE,
                FOREIGN KEY(cited_paper_id) REFERENCES Papers(id) ON DELETE CASCADE,
                UNIQUE(citing_paper_id, cited_paper_id)
            )
        """)

        # Full-text search index (FTS5) - standalone table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS FullTextIndex USING fts5(
                paper_id UNINDEXED,
                title,
                authors,
                abstract,
                full_text
            )
        """)

        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_title ON Papers(title)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_year ON Papers(year)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_keywords_paper ON Keywords(paper_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_citations_citing ON Citations(citing_paper_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_citations_cited ON Citations(cited_paper_id)
        """)

        self.conn.commit()

    def add_paper(
        self,
        title: str,
        pdf_path: str,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None,
        journal: Optional[str] = None,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        abstract: Optional[str] = None,
        num_pages: Optional[int] = None,
        file_size: Optional[int] = None
    ) -> int:
        """
        Add a new paper to the database.

        Args:
            title: Paper title
            pdf_path: Path to PDF file
            authors: List of author names
            year: Publication year
            journal: Journal/venue name
            doi: DOI identifier
            arxiv_id: arXiv identifier
            abstract: Paper abstract
            num_pages: Number of pages in PDF
            file_size: File size in bytes

        Returns:
            Paper ID (rowid)
        """
        cursor = self.conn.cursor()

        authors_json = json.dumps(authors) if authors else None
        added_date = int(datetime.now().timestamp())

        cursor.execute("""
            INSERT INTO Papers (
                title, authors, year, journal, doi, arxiv_id, abstract,
                pdf_path, num_pages, file_size, added_date, modified_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, authors_json, year, journal, doi, arxiv_id, abstract,
            pdf_path, num_pages, file_size, added_date, added_date
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_paper(self, paper_id: int) -> Optional[Dict]:
        """Get paper by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM Papers WHERE id = ?", (paper_id,))
        row = cursor.fetchone()

        if row:
            paper = dict(row)
            # Parse JSON fields
            if paper['authors']:
                paper['authors'] = json.loads(paper['authors'])
            return paper
        return None

    def get_all_papers(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all papers, optionally limited."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM Papers ORDER BY added_date DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        papers = []
        for row in cursor.fetchall():
            paper = dict(row)
            if paper['authors']:
                paper['authors'] = json.loads(paper['authors'])
            papers.append(paper)

        return papers

    def search_papers(self, query: str, limit: int = 100) -> List[Dict]:
        """
        Full-text search across papers - completely rewritten for accuracy.

        Args:
            query: Search query (e.g., "heat treatment", "fatigue crack")
            limit: Maximum results

        Returns:
            List of matching papers with relevance rank
        """
        if not query or not query.strip():
            # Empty query - return all papers
            return self.get_all_papers(limit)

        cursor = self.conn.cursor()

        # Clean query
        query = query.strip()

        # Strategy: Use simple MATCH with proper escaping
        # FTS5 will handle relevance ranking automatically
        try:
            # Simple FTS5 match - let SQLite handle the ranking
            cursor.execute("""
                SELECT DISTINCT
                    Papers.id,
                    Papers.title,
                    Papers.authors,
                    Papers.year,
                    Papers.journal,
                    Papers.doi,
                    Papers.arxiv_id,
                    Papers.abstract,
                    Papers.pdf_path,
                    Papers.num_pages,
                    Papers.file_size,
                    Papers.added_date,
                    Papers.modified_date,
                    Papers.notes,
                    bm25(FullTextIndex) as rank
                FROM FullTextIndex
                JOIN Papers ON FullTextIndex.paper_id = Papers.id
                WHERE FullTextIndex MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))

            papers = []
            for row in cursor.fetchall():
                paper = dict(row)
                if paper['authors']:
                    try:
                        paper['authors'] = json.loads(paper['authors'])
                    except:
                        paper['authors'] = []
                papers.append(paper)

            if papers:
                print(f"✓ Found {len(papers)} results for: {query}")
                return papers

        except Exception as e:
            print(f"FTS5 search error: {e}")

        # Fallback: Simple LIKE search if FTS5 fails
        print(f"⚠ Using fallback LIKE search for: {query}")
        try:
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM Papers
                WHERE title LIKE ? OR abstract LIKE ?
                ORDER BY
                    CASE
                        WHEN title LIKE ? THEN 1
                        WHEN abstract LIKE ? THEN 2
                        ELSE 3
                    END
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, search_pattern, limit))

            papers = []
            for row in cursor.fetchall():
                paper = dict(row)
                if paper['authors']:
                    try:
                        paper['authors'] = json.loads(paper['authors'])
                    except:
                        paper['authors'] = []
                papers.append(paper)

            return papers

        except Exception as e:
            print(f"Fallback search error: {e}")
            return []

    def add_keywords(
        self,
        paper_id: int,
        keywords: List[Tuple[str, float]],
        method: str = "yake"
    ):
        """
        Add keywords for a paper.

        Args:
            paper_id: Paper ID
            keywords: List of (keyword, score) tuples
            method: Extraction method ('yake', 'keybert', 'manual')
        """
        cursor = self.conn.cursor()

        for keyword, score in keywords:
            cursor.execute("""
                INSERT OR REPLACE INTO Keywords (paper_id, keyword, score, extraction_method)
                VALUES (?, ?, ?, ?)
            """, (paper_id, keyword, score, method))

        self.conn.commit()

    def get_keywords(self, paper_id: int) -> List[Tuple[str, float]]:
        """Get keywords for a paper."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT keyword, score FROM Keywords
            WHERE paper_id = ?
            ORDER BY score DESC
        """, (paper_id,))

        return [(row['keyword'], row['score']) for row in cursor.fetchall()]

    def add_references(self, paper_id: int, references: List[str]):
        """
        Add references for a paper.

        Args:
            paper_id: Paper ID
            references: List of raw reference strings
        """
        cursor = self.conn.cursor()

        for ref_text in references:
            cursor.execute("""
                INSERT INTO PaperReferences (paper_id, raw_text)
                VALUES (?, ?)
            """, (paper_id, ref_text))

        self.conn.commit()

    def add_citation(
        self,
        citing_paper_id: int,
        cited_paper_id: int,
        confidence: float = 1.0
    ):
        """
        Add a citation relationship between two papers.

        Args:
            citing_paper_id: ID of paper making the citation
            cited_paper_id: ID of paper being cited
            confidence: Matching confidence (0.0-1.0)
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO Citations (citing_paper_id, cited_paper_id, confidence)
            VALUES (?, ?, ?)
        """, (citing_paper_id, cited_paper_id, confidence))

        self.conn.commit()

    def get_citation_network(self) -> Dict:
        """
        Get the full citation network for visualization.

        Returns:
            Dictionary with 'nodes' and 'edges' for graph rendering
        """
        cursor = self.conn.cursor()

        # Get all papers with citation counts
        cursor.execute("""
            SELECT
                p.id,
                p.title,
                p.authors,
                p.year,
                COUNT(DISTINCT c_out.id) as citations_made,
                COUNT(DISTINCT c_in.id) as citations_received
            FROM Papers p
            LEFT JOIN Citations c_out ON p.id = c_out.citing_paper_id
            LEFT JOIN Citations c_in ON p.id = c_in.cited_paper_id
            GROUP BY p.id
        """)

        nodes = []
        for row in cursor.fetchall():
            node = dict(row)
            if node['authors']:
                node['authors'] = json.loads(node['authors'])
            nodes.append(node)

        # Get all citation edges
        cursor.execute("""
            SELECT citing_paper_id, cited_paper_id, confidence
            FROM Citations
        """)

        edges = [dict(row) for row in cursor.fetchall()]

        return {'nodes': nodes, 'edges': edges}

    def update_full_text_index(self, paper_id: int, full_text: str):
        """
        Update full-text search index for a paper.

        Args:
            paper_id: Paper ID
            full_text: Extracted text from PDF
        """
        cursor = self.conn.cursor()

        # Delete existing entry if any
        cursor.execute("DELETE FROM FullTextIndex WHERE paper_id = ?", (paper_id,))

        # Get paper metadata
        paper = self.get_paper(paper_id)
        if not paper:
            return

        # Prepare text for indexing
        title = paper['title'] or ''
        authors = ' '.join(paper['authors']) if paper['authors'] else ''
        abstract = paper['abstract'] or ''

        # Insert into FTS5
        cursor.execute("""
            INSERT INTO FullTextIndex (paper_id, title, authors, abstract, full_text)
            VALUES (?, ?, ?, ?, ?)
        """, (
            paper_id,
            title,
            authors,
            abstract,
            full_text[:50000]  # Limit full text to 50K chars
        ))

        self.conn.commit()

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
