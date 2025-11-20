"""
Citation matching module for resolving references to papers in the database.

Uses multiple matching strategies:
1. Exact DOI matching (highest confidence)
2. Exact arXiv ID matching (high confidence)
3. Title similarity matching (medium confidence)
4. Title + year matching (variable confidence)
"""

import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher


class CitationMatcher:
    """Match parsed references to papers in the database."""

    def __init__(self, db):
        """
        Initialize citation matcher.

        Args:
            db: Database instance
        """
        self.db = db
        self.min_title_similarity = 0.75  # Minimum similarity for title matching

    def match_references_for_paper(self, paper_id: int) -> Dict[str, int]:
        """
        Match all references for a given paper to papers in the database.

        Args:
            paper_id: ID of the paper whose references to match

        Returns:
            Dictionary with matching statistics
        """
        # Get references for this paper
        references = self.db.get_references(paper_id)

        if not references:
            return {
                'total_references': 0,
                'matched': 0,
                'unmatched': 0,
                'confidence_breakdown': {}
            }

        # Get all papers in database for matching
        all_papers = self.db.get_all_papers()

        stats = {
            'total_references': len(references),
            'matched': 0,
            'unmatched': 0,
            'confidence_breakdown': {
                'high': 0,      # DOI or arXiv match (0.95-1.0)
                'medium': 0,    # Strong title match (0.80-0.94)
                'low': 0,       # Weak title match (0.75-0.79)
            }
        }

        # Try to match each reference
        for ref in references:
            match_result = self._match_reference(ref, all_papers)

            if match_result:
                matched_paper_id, confidence = match_result

                # Add citation to database
                self.db.add_citation(
                    citing_paper_id=paper_id,
                    cited_paper_id=matched_paper_id,
                    confidence=confidence
                )

                stats['matched'] += 1

                # Update confidence breakdown
                if confidence >= 0.95:
                    stats['confidence_breakdown']['high'] += 1
                elif confidence >= 0.80:
                    stats['confidence_breakdown']['medium'] += 1
                else:
                    stats['confidence_breakdown']['low'] += 1
            else:
                stats['unmatched'] += 1

        return stats

    def _match_reference(
        self,
        reference: Dict,
        candidate_papers: List[Dict]
    ) -> Optional[Tuple[int, float]]:
        """
        Match a single reference to a paper in the database.

        Args:
            reference: Parsed reference dictionary
            candidate_papers: List of all papers to match against

        Returns:
            Tuple of (paper_id, confidence) if match found, None otherwise
        """
        # Strategy 1: Exact DOI match (highest confidence)
        if reference.get('parsed_doi'):
            for paper in candidate_papers:
                if paper.get('doi') and self._normalize_doi(paper['doi']) == self._normalize_doi(reference['parsed_doi']):
                    return (paper['id'], 1.0)

        # Strategy 2: Exact arXiv ID match (high confidence)
        if reference.get('arxiv_id'):
            ref_arxiv = self._normalize_arxiv_id(reference['arxiv_id'])
            for paper in candidate_papers:
                if paper.get('arxiv_id'):
                    paper_arxiv = self._normalize_arxiv_id(paper['arxiv_id'])
                    if ref_arxiv == paper_arxiv:
                        return (paper['id'], 0.98)

        # Strategy 3: Title similarity matching (with author support)
        if reference.get('parsed_title'):
            ref_title_normalized = self._normalize_title(reference['parsed_title'])
            ref_year = reference.get('parsed_year')
            ref_authors = reference.get('parsed_authors')

            best_match = None
            best_similarity = 0.0

            for paper in candidate_papers:
                if not paper.get('title'):
                    continue

                paper_title_normalized = self._normalize_title(paper['title'])

                # Calculate title similarity
                similarity = self._title_similarity(ref_title_normalized, paper_title_normalized)

                # Boost similarity if years match
                if ref_year and paper.get('year') == ref_year:
                    similarity = min(1.0, similarity + 0.10)

                # Additional boost if first author matches
                if ref_authors and paper.get('authors'):
                    if self._first_author_matches(ref_authors, paper['authors']):
                        similarity = min(1.0, similarity + 0.05)

                # Only consider if above threshold
                if similarity >= self.min_title_similarity:
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = paper['id']

            if best_match:
                return (best_match, best_similarity)

        # Strategy 4: Partial title matching (for truncated references)
        # Try matching first N significant words
        if reference.get('parsed_title'):
            ref_title_words = self._get_significant_words(reference['parsed_title'])
            if len(ref_title_words) >= 4:  # Need at least 4 words
                ref_year = reference.get('parsed_year')

                for paper in candidate_papers:
                    if not paper.get('title'):
                        continue

                    paper_title_words = self._get_significant_words(paper['title'])

                    # Check if first 4+ words match
                    if len(paper_title_words) >= 4:
                        match_count = sum(1 for i in range(min(5, len(ref_title_words), len(paper_title_words)))
                                        if ref_title_words[i] == paper_title_words[i])

                        if match_count >= 4:  # At least 4 words match in order
                            confidence = 0.80 + (match_count - 4) * 0.03  # 0.80-0.95

                            # Boost if year matches
                            if ref_year and paper.get('year') == ref_year:
                                confidence = min(0.95, confidence + 0.05)

                            return (paper['id'], confidence)

        # No match found
        return None

    def _normalize_doi(self, doi: str) -> str:
        """Normalize DOI for comparison."""
        if not doi:
            return ""
        # Remove URL prefix, lowercase, remove whitespace
        doi = doi.lower().strip()
        doi = re.sub(r'^(?:https?://)?(?:dx\.)?doi\.org/', '', doi)
        doi = re.sub(r'\s+', '', doi)
        return doi

    def _normalize_arxiv_id(self, arxiv_id: str) -> str:
        """Normalize arXiv ID for comparison."""
        if not arxiv_id:
            return ""
        # Extract just the ID part, remove version
        arxiv_id = arxiv_id.lower().strip()
        arxiv_id = re.sub(r'^arxiv:', '', arxiv_id)
        arxiv_id = re.sub(r'v\d+$', '', arxiv_id)  # Remove version
        return arxiv_id

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ""
        # Lowercase, remove punctuation, collapse whitespace
        title = title.lower()
        title = re.sub(r'[^\w\s]', ' ', title)  # Remove punctuation
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles using sequence matching.

        Args:
            title1: First normalized title
            title2: Second normalized title

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not title1 or not title2:
            return 0.0

        # Use SequenceMatcher for similarity
        matcher = SequenceMatcher(None, title1, title2)
        similarity = matcher.ratio()

        # Additional check: word overlap ratio
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            return similarity

        # Jaccard similarity for words
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        word_similarity = intersection / union if union > 0 else 0.0

        # Combine both metrics (weighted average)
        combined_similarity = (similarity * 0.6) + (word_similarity * 0.4)

        return combined_similarity

    def _first_author_matches(self, ref_authors: str, paper_authors: List[str]) -> bool:
        """
        Check if first author matches between reference and paper.

        Args:
            ref_authors: Authors string from reference (may be formatted differently)
            paper_authors: List of author names from paper

        Returns:
            True if first author appears to match
        """
        if not ref_authors or not paper_authors:
            return False

        # Extract first author from reference
        # Handle formats: "Smith, J." or "J. Smith" or "Smith et al."
        ref_first = ref_authors.split(',')[0].split(' and ')[0].split(';')[0].strip()

        # Extract last name (usually the identifying part)
        ref_last_name = self._extract_last_name(ref_first)

        if not ref_last_name or len(ref_last_name) < 3:
            return False

        # Check if this name appears in first paper author
        paper_first = paper_authors[0] if isinstance(paper_authors, list) else str(paper_authors)
        paper_last_name = self._extract_last_name(paper_first)

        if not paper_last_name:
            return False

        # Normalize and compare
        ref_last_name = ref_last_name.lower()
        paper_last_name = paper_last_name.lower()

        # Allow for slight variations (e.g., "Smith" vs "Smithson")
        if ref_last_name in paper_last_name or paper_last_name in ref_last_name:
            return True

        return ref_last_name == paper_last_name

    def _extract_last_name(self, author_name: str) -> str:
        """
        Extract last name from author name string.

        Handles formats:
        - "Smith, John" -> "Smith"
        - "John Smith" -> "Smith"
        - "J. Smith" -> "Smith"
        - "Smith et al." -> "Smith"
        """
        if not author_name:
            return ""

        # Remove common suffixes
        author_name = re.sub(r'\s+et\s+al\.?', '', author_name, flags=re.IGNORECASE)
        author_name = author_name.strip()

        # Format: "Last, First" or "Last, F."
        if ',' in author_name:
            return author_name.split(',')[0].strip()

        # Format: "First Last" or "F. Last"
        parts = author_name.split()
        if parts:
            # Last part is usually the last name
            last_part = parts[-1].strip('.,')
            # But if it's too short, it might be an initial
            if len(last_part) > 2:
                return last_part

            # Try second to last if last is too short
            if len(parts) > 1 and len(parts[-2]) > 2:
                return parts[-2].strip('.,')

        return author_name

    def _get_significant_words(self, title: str) -> List[str]:
        """
        Extract significant words from title (normalized, without stopwords).

        Args:
            title: Title string

        Returns:
            List of significant words in order
        """
        # Normalize title
        normalized = self._normalize_title(title)

        # Common stopwords to ignore
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'it', 'its', 'their', 'there', 'than'
        }

        words = normalized.split()
        significant_words = [w for w in words if w not in stopwords and len(w) > 2]

        return significant_words

    def match_all_papers(self) -> Dict[str, any]:
        """
        Match references for all papers in the database.

        Returns:
            Overall matching statistics
        """
        all_papers = self.db.get_all_papers()

        overall_stats = {
            'total_papers_processed': 0,
            'total_references': 0,
            'total_matched': 0,
            'total_unmatched': 0,
            'confidence_breakdown': {
                'high': 0,
                'medium': 0,
                'low': 0,
            },
            'papers_with_matches': 0,
        }

        for paper in all_papers:
            # Check if paper has references
            references = self.db.get_references(paper['id'])
            if not references:
                continue

            overall_stats['total_papers_processed'] += 1

            # Match references for this paper
            paper_stats = self.match_references_for_paper(paper['id'])

            # Accumulate stats
            overall_stats['total_references'] += paper_stats['total_references']
            overall_stats['total_matched'] += paper_stats['matched']
            overall_stats['total_unmatched'] += paper_stats['unmatched']

            for level in ['high', 'medium', 'low']:
                overall_stats['confidence_breakdown'][level] += \
                    paper_stats['confidence_breakdown'][level]

            if paper_stats['matched'] > 0:
                overall_stats['papers_with_matches'] += 1

        return overall_stats


def match_citations(db) -> Dict:
    """
    Convenience function to match citations for all papers.

    Args:
        db: Database instance

    Returns:
        Matching statistics
    """
    matcher = CitationMatcher(db)
    return matcher.match_all_papers()
