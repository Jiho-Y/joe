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
        Search papers by TITLE and KEYWORDS only (improved accuracy).

        Strategy:
        1. Search in paper titles (FTS5)
        2. Search in keywords (Keywords table)
        3. Merge and rank results

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

        # Dictionary to collect papers and their relevance scores
        paper_scores = {}  # {paper_id: score}

        # STRATEGY 1: Search in TITLE using FTS5
        try:
            # Search only in the title field using FTS5 column syntax
            title_query = f"title:{query}"
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
            """, (title_query, limit * 2))  # Get more for merging

            for row in cursor.fetchall():
                paper_id = row['id']
                rank = row['rank']
                # BM25 returns negative scores, lower is better
                # Convert to positive score (higher is better)
                score = -rank
                paper_scores[paper_id] = max(paper_scores.get(paper_id, 0), score * 2)  # Title match = 2x weight

        except Exception as e:
            print(f"Title FTS5 search error: {e}")

        # STRATEGY 2: Search in KEYWORDS
        try:
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT DISTINCT paper_id, keyword, score
                FROM Keywords
                WHERE keyword LIKE ?
                ORDER BY score DESC
            """, (search_pattern,))

            for row in cursor.fetchall():
                paper_id = row['paper_id']
                keyword_score = row['score'] or 0.5
                # Add keyword match score
                paper_scores[paper_id] = paper_scores.get(paper_id, 0) + keyword_score

        except Exception as e:
            print(f"Keyword search error: {e}")

        # If no results from FTS5 or keywords, try simple title LIKE search
        if not paper_scores:
            print(f"⚠ Using fallback LIKE search for: {query}")
            try:
                search_pattern = f"%{query}%"
                cursor.execute("""
                    SELECT id FROM Papers
                    WHERE title LIKE ?
                    LIMIT ?
                """, (search_pattern, limit))

                for row in cursor.fetchall():
                    paper_id = row['id']
                    paper_scores[paper_id] = 1.0  # Default score

            except Exception as e:
                print(f"Fallback search error: {e}")

        # Sort papers by score (highest first)
        sorted_paper_ids = sorted(
            paper_scores.keys(),
            key=lambda pid: paper_scores[pid],
            reverse=True
        )[:limit]

        # Fetch full paper details for top results
        if not sorted_paper_ids:
            print(f"✗ No results found for: {query}")
            return []

        # Build query with placeholders
        placeholders = ','.join('?' * len(sorted_paper_ids))
        cursor.execute(f"""
            SELECT * FROM Papers
            WHERE id IN ({placeholders})
        """, sorted_paper_ids)

        # Create a map of papers by ID
        papers_map = {}
        for row in cursor.fetchall():
            paper = dict(row)
            if paper['authors']:
                try:
                    paper['authors'] = json.loads(paper['authors'])
                except:
                    paper['authors'] = []
            papers_map[paper['id']] = paper

        # Return papers in order of relevance
        papers = [papers_map[pid] for pid in sorted_paper_ids if pid in papers_map]

        print(f"✓ Found {len(papers)} results for '{query}' (title + keywords only)")
        return papers

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

    def add_references(self, paper_id: int, references: List[Dict]):
        """
        Add parsed references for a paper.

        Args:
            paper_id: Paper ID
            references: List of dictionaries with parsed reference data
                        Each dict should have: raw_text, doi, arxiv_id, title, authors, year, journal
        """
        cursor = self.conn.cursor()

        for ref in references:
            # Support both old format (string) and new format (dict)
            if isinstance(ref, str):
                ref = {'raw_text': ref}

            cursor.execute("""
                INSERT INTO PaperReferences (
                    paper_id, raw_text, parsed_title, parsed_authors,
                    parsed_year, parsed_venue, parsed_doi
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                ref.get('raw_text', ''),
                ref.get('title'),
                ref.get('authors'),
                ref.get('year'),
                ref.get('journal'),
                ref.get('doi')
            ))

        self.conn.commit()

    def get_references(self, paper_id: int) -> List[Dict]:
        """
        Get all references for a paper.

        Args:
            paper_id: Paper ID

        Returns:
            List of dictionaries with reference data
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM PaperReferences
            WHERE paper_id = ?
            ORDER BY id
        """, (paper_id,))

        return [dict(row) for row in cursor.fetchall()]

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

    def delete_paper(self, paper_id: int) -> bool:
        """
        Delete a paper and all associated data.

        Due to CASCADE DELETE constraints:
        - Keywords will be deleted automatically
        - PaperReferences will be deleted automatically
        - Citations (both citing and cited) will be deleted automatically
        - FullTextIndex entry will need manual deletion

        Args:
            paper_id: Paper ID to delete

        Returns:
            True if deleted successfully, False if paper not found
        """
        cursor = self.conn.cursor()

        # Check if paper exists
        cursor.execute("SELECT id FROM Papers WHERE id = ?", (paper_id,))
        if not cursor.fetchone():
            return False

        # Delete from FullTextIndex (not covered by CASCADE)
        cursor.execute("DELETE FROM FullTextIndex WHERE paper_id = ?", (paper_id,))

        # Delete from Papers table (CASCADE will handle related tables)
        cursor.execute("DELETE FROM Papers WHERE id = ?", (paper_id,))

        self.conn.commit()
        return True

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
