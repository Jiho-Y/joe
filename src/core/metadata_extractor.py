"""
Metadata extraction using NLP techniques.
Includes keyword extraction using YAKE and KeyBERT.
"""

import yake
from typing import List, Tuple, Optional
import re


class KeywordExtractor:
    """Extract keywords from text using various methods."""

    def __init__(self):
        """Initialize keyword extractors."""
        # YAKE configuration (fast, no model required)
        self.yake_extractor = yake.KeywordExtractor(
            lan="en",
            n=3,  # max n-gram size
            dedupLim=0.7,  # deduplication threshold
            top=20,  # top N keywords
            features=None
        )

        # KeyBERT will be initialized lazily (requires model download)
        self._keybert_extractor = None

    def extract_yake(
        self,
        text: str,
        top_n: int = 10,
        max_ngram: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Extract keywords using YAKE (fast, statistical method).

        Args:
            text: Input text
            top_n: Number of keywords to extract
            max_ngram: Maximum n-gram size (1-3)

        Returns:
            List of (keyword, score) tuples (lower score = more relevant)
        """
        if not text or len(text.strip()) < 100:
            return []

        # Update extractor config if needed
        if self.yake_extractor.n != max_ngram:
            self.yake_extractor = yake.KeywordExtractor(
                lan="en",
                n=max_ngram,
                dedupLim=0.7,
                top=top_n,
                features=None
            )

        keywords = self.yake_extractor.extract_keywords(text)

        # YAKE returns (keyword, score) where lower is better
        # Normalize scores to 0-1 range for consistency
        if keywords:
            max_score = max(score for _, score in keywords)
            if max_score > 0:
                keywords = [(kw, 1.0 - (score / max_score)) for kw, score in keywords]

        return keywords[:top_n]

    def extract_keybert(
        self,
        text: str,
        top_n: int = 10,
        use_scibert: bool = False
    ) -> List[Tuple[str, float]]:
        """
        Extract keywords using KeyBERT (more accurate, requires model).

        Args:
            text: Input text
            top_n: Number of keywords to extract
            use_scibert: Use SciBERT model (better for academic papers)

        Returns:
            List of (keyword, score) tuples (higher score = more relevant)
        """
        # Lazy import and initialization
        if self._keybert_extractor is None:
            try:
                from keybert import KeyBERT

                # Choose model
                if use_scibert:
                    # SciBERT for academic papers (requires download ~440MB)
                    model_name = "allenai/scibert_scivocab_uncased"
                else:
                    # Default all-MiniLM (smaller, faster)
                    model_name = "all-MiniLM-L6-v2"

                self._keybert_extractor = KeyBERT(model=model_name)

            except Exception as e:
                print(f"Warning: KeyBERT initialization failed: {e}")
                print("Falling back to YAKE...")
                return self.extract_yake(text, top_n)

        if not text or len(text.strip()) < 100:
            return []

        try:
            keywords = self._keybert_extractor.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words='english',
                top_n=top_n,
                use_mmr=True,  # Maximal Marginal Relevance for diversity
                diversity=0.5
            )
            return keywords

        except Exception as e:
            print(f"KeyBERT extraction failed: {e}")
            return self.extract_yake(text, top_n)

    def extract_from_paper(
        self,
        title: str,
        abstract: Optional[str],
        full_text: Optional[str],
        method: str = "yake",
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Extract keywords from a paper's text.
        Prioritizes title and abstract over full text.

        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Full paper text
            method: 'yake' or 'keybert'
            top_n: Number of keywords

        Returns:
            List of (keyword, score) tuples
        """
        # Construct text with weighted importance
        text_parts = []

        if title:
            # Title is very important, repeat 3 times
            text_parts.append(title * 3)

        if abstract:
            # Abstract is important, repeat 2 times
            text_parts.append(abstract * 2)

        if full_text:
            # Use first 5000 characters of full text
            text_parts.append(full_text[:5000])

        combined_text = " ".join(text_parts)

        # Extract keywords
        if method == "keybert":
            keywords = self.extract_keybert(combined_text, top_n)
        else:
            keywords = self.extract_yake(combined_text, top_n)

        # Post-process: remove very generic terms
        filtered = self._filter_generic_keywords(keywords)

        return filtered[:top_n]

    def _filter_generic_keywords(
        self,
        keywords: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """
        Filter out overly generic keywords.

        Args:
            keywords: List of (keyword, score) tuples

        Returns:
            Filtered list
        """
        # Common generic terms in academic papers
        generic_terms = {
            'paper', 'study', 'research', 'results', 'conclusion',
            'introduction', 'method', 'approach', 'analysis', 'data',
            'figure', 'table', 'section', 'chapter', 'appendix',
            'et al', 'etc', 'i.e', 'e.g', 'however', 'therefore'
        }

        filtered = []
        for keyword, score in keywords:
            keyword_lower = keyword.lower()

            # Skip if keyword is entirely generic
            if keyword_lower in generic_terms:
                continue

            # Skip very short keywords (< 3 chars)
            if len(keyword) < 3:
                continue

            # Skip keywords that are just numbers
            if keyword.replace('.', '').replace(',', '').isdigit():
                continue

            filtered.append((keyword, score))

        return filtered


class ReferenceParser:
    """Parse and structure reference strings."""

    @staticmethod
    def parse_reference(ref_text: str) -> dict:
        """
        Parse a reference string into structured components.
        This is a basic heuristic parser; GROBID will do better.

        Args:
            ref_text: Raw reference string

        Returns:
            Dictionary with parsed fields
        """
        parsed = {
            'raw_text': ref_text,
            'title': None,
            'authors': None,
            'year': None,
            'venue': None,
            'doi': None
        }

        # Extract DOI
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        doi_match = re.search(doi_pattern, ref_text)
        if doi_match:
            parsed['doi'] = doi_match.group(0)

        # Extract year (4-digit number)
        year_pattern = r'\b(19\d{2}|20[0-2]\d)\b'
        year_match = re.search(year_pattern, ref_text)
        if year_match:
            parsed['year'] = int(year_match.group(1))

        # Extract title (text in quotes or between periods)
        title_pattern = r'["\'](.+?)["\']|\.(.+?)\.'
        title_match = re.search(title_pattern, ref_text)
        if title_match:
            parsed['title'] = title_match.group(1) or title_match.group(2)

        # Extract authors (text before year, if year found)
        if parsed['year']:
            author_text = ref_text.split(str(parsed['year']))[0]
            # Clean up
            author_text = re.sub(r'[\[\]\(\)]', '', author_text).strip()
            parsed['authors'] = author_text[:200]  # Limit length

        return parsed

    @staticmethod
    def match_references_to_papers(
        references: List[str],
        papers_in_db: List[dict]
    ) -> List[Tuple[str, Optional[int], float]]:
        """
        Match reference strings to papers in database.
        Returns list of (ref_text, paper_id, confidence) tuples.

        Args:
            references: List of reference strings
            papers_in_db: List of paper dictionaries from database

        Returns:
            List of (reference_text, matched_paper_id, confidence_score) tuples
        """
        matches = []

        for ref in references:
            parsed = ReferenceParser.parse_reference(ref)

            best_match_id = None
            best_confidence = 0.0

            # Try to match by DOI first (most reliable)
            if parsed['doi']:
                for paper in papers_in_db:
                    if paper.get('doi') == parsed['doi']:
                        best_match_id = paper['id']
                        best_confidence = 1.0
                        break

            # If no DOI match, try title + year
            if not best_match_id and parsed['title'] and parsed['year']:
                for paper in papers_in_db:
                    # Simple substring matching (case-insensitive)
                    if (paper.get('year') == parsed['year'] and
                        paper.get('title') and
                        parsed['title'].lower() in paper['title'].lower()):
                        best_match_id = paper['id']
                        best_confidence = 0.8
                        break

            matches.append((ref, best_match_id, best_confidence))

        return matches
