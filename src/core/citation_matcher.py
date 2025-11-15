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

        # Strategy 3: Title similarity matching
        if reference.get('parsed_title'):
            ref_title_normalized = self._normalize_title(reference['parsed_title'])
            ref_year = reference.get('parsed_year')

            best_match = None
            best_similarity = 0.0

            for paper in candidate_papers:
                if not paper.get('title'):
                    continue

                paper_title_normalized = self._normalize_title(paper['title'])
                similarity = self._title_similarity(ref_title_normalized, paper_title_normalized)

                # Boost similarity if years match
                if ref_year and paper.get('year') == ref_year:
                    similarity = min(1.0, similarity + 0.10)

                # Only consider if above threshold
                if similarity >= self.min_title_similarity:
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = paper['id']

            if best_match:
                return (best_match, best_similarity)

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
