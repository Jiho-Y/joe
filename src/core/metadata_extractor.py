"""
Metadata extraction using NLP techniques.
Includes keyword extraction using YAKE, KeyBERT, and ML-based ranking.
"""

import yake
from typing import List, Tuple, Optional
import re
import pickle
import numpy as np
from pathlib import Path


class KeywordExtractor:
    """Extract keywords from text using various methods."""

    def __init__(self):
        """Initialize keyword extractors."""
        # YAKE configuration (fast, no model required)
        # Improved settings for academic papers
        self.yake_extractor = yake.KeywordExtractor(
            lan="en",
            n=3,  # max n-gram size (1-3 words)
            dedupLim=0.8,  # higher = less duplication (0.8 recommended for academic)
            dedupFunc='seqm',  # sequence matching for deduplication
            windowsSize=1,  # context window
            top=30,  # extract more, filter later
            features=None
        )

        # KeyBERT will be initialized lazily (requires model download)
        self._keybert_extractor = None

        # ML model will be loaded lazily (if trained)
        self._ml_model = None
        self._ml_model_loaded = False

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

    def extract_ml(
        self,
        title: str,
        abstract: Optional[str],
        full_text: Optional[str],
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Extract keywords using ML-based ranking (if model is trained).

        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Full paper text
            top_n: Number of keywords

        Returns:
            List of (keyword, score) tuples
        """
        # Load ML model lazily
        if not self._ml_model_loaded:
            model_path = Path("models/keyword_ranker.pkl")
            if model_path.exists():
                try:
                    with open(model_path, 'rb') as f:
                        self._ml_model = pickle.load(f)
                    print("✓ Loaded ML keyword ranker model")
                except Exception as e:
                    print(f"⚠ ML model load failed: {e}")
                    self._ml_model = None
            else:
                print("⚠ ML model not found. Train with: python train_keyword_model.py --train")
                self._ml_model = None

            self._ml_model_loaded = True

        # If no model, fallback to YAKE
        if self._ml_model is None:
            print("⚠ Falling back to YAKE")
            combined_text = (title * 5) + (abstract * 3 if abstract else '') + (full_text[:8000] if full_text else '')
            return self.extract_yake(combined_text, top_n)

        # Step 1: Extract candidates using YAKE
        combined_text = (title * 5) + (abstract * 3 if abstract else '') + (full_text[:8000] if full_text else '')
        candidates = self.extract_yake(combined_text, top_n=30)

        if not candidates:
            return []

        # Step 2: Extract features for each candidate
        scored_candidates = []

        for candidate, yake_score in candidates:
            features = self._extract_ml_features(
                candidate, title, abstract or '', full_text or '',
                yake_score, candidates
            )

            # Step 3: Get ML probability
            try:
                prob = self._ml_model.predict_proba([features])[0][1]
                scored_candidates.append((candidate, prob))
            except Exception as e:
                # If ML fails, use YAKE score
                scored_candidates.append((candidate, 1.0 - yake_score))

        # Step 4: Sort by ML probability (descending)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Step 5: Return top N
        return scored_candidates[:top_n]

    def _extract_ml_features(
        self,
        candidate: str,
        title: str,
        abstract: str,
        full_text: str,
        yake_score: float,
        all_candidates: List[Tuple[str, float]]
    ) -> np.ndarray:
        """
        Extract 12-dimensional feature vector for ML model.
        (Same features as in train_keyword_model.py)
        """
        features = []

        # Normalize texts
        title_lower = title.lower()
        abstract_lower = abstract.lower()
        full_text_lower = full_text.lower()
        candidate_lower = candidate.lower()

        # Feature 1: YAKE score (normalized 0-1, inverted)
        max_yake = max(score for _, score in all_candidates) if all_candidates else 1.0
        yake_norm = 1.0 - (yake_score / max_yake) if max_yake > 0 else 0.5
        features.append(yake_norm)

        # Feature 2: In title (binary)
        in_title = 1.0 if candidate_lower in title_lower else 0.0
        features.append(in_title)

        # Feature 3: Title overlap ratio
        candidate_words = set(candidate_lower.split())
        title_words = set(title_lower.split())
        title_overlap = len(candidate_words & title_words) / len(candidate_words) if candidate_words else 0.0
        features.append(title_overlap)

        # Feature 4: Abstract frequency (normalized)
        abstract_freq = abstract_lower.count(candidate_lower)
        abstract_freq_norm = min(abstract_freq / 5.0, 1.0)
        features.append(abstract_freq_norm)

        # Feature 5: Full text frequency (normalized)
        full_freq = full_text_lower.count(candidate_lower)
        full_freq_norm = min(full_freq / 20.0, 1.0)
        features.append(full_freq_norm)

        # Feature 6: N-gram size
        ngram_size = len(candidate.split())
        ngram_feature = ngram_size / 3.0
        features.append(ngram_feature)

        # Feature 7: Keyword length
        length_norm = min(len(candidate) / 30.0, 1.0)
        features.append(length_norm)

        # Feature 8: Capital letter ratio
        capitals = sum(1 for c in candidate if c.isupper())
        capital_ratio = capitals / len(candidate) if len(candidate) > 0 else 0.0
        features.append(capital_ratio)

        # Feature 9: Alphanumeric ratio
        alphanum = sum(1 for c in candidate if c.isalnum())
        alphanum_ratio = alphanum / len(candidate) if len(candidate) > 0 else 0.0
        features.append(alphanum_ratio)

        # Feature 10: Position in document
        if full_text:
            first_pos = full_text_lower.find(candidate_lower)
            position_score = 1.0 - (first_pos / len(full_text_lower)) if first_pos >= 0 else 0.0
        else:
            position_score = 0.5
        features.append(position_score)

        # Feature 11: Contains hyphen or underscore
        has_connector = 1.0 if ('-' in candidate or '_' in candidate) else 0.0
        features.append(has_connector)

        # Feature 12: Rank in YAKE results
        try:
            rank = [kw for kw, _ in all_candidates].index(candidate)
            rank_norm = 1.0 - (rank / len(all_candidates))
        except (ValueError, ZeroDivisionError):
            rank_norm = 0.5
        features.append(rank_norm)

        return np.array(features, dtype=np.float32)

    def extract_from_paper(
        self,
        title: str,
        abstract: Optional[str],
        full_text: Optional[str],
        method: str = "yake",
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Extract keywords from a paper's text with improved weighting.
        Prioritizes title and abstract over full text.

        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Full paper text
            method: 'yake', 'keybert', or 'ml' (ML-based ranking)
            top_n: Number of keywords

        Returns:
            List of (keyword, score) tuples
        """
        # ML method handles its own text processing
        if method == "ml":
            keywords = self.extract_ml(title, abstract, full_text, top_n)
            # ML already filters, so return directly
            return keywords

        # Construct text with weighted importance (for YAKE/KeyBERT)
        text_parts = []

        if title:
            # Title is extremely important, repeat 5 times
            # Keywords in title are most representative
            text_parts.append(title * 5)

        if abstract:
            # Abstract is very important, repeat 3 times
            # Abstract contains key concepts and methodology
            text_parts.append(abstract * 3)

        if full_text:
            # Use first 8000 characters of full text (more context)
            # But lower weight than title/abstract
            text_parts.append(full_text[:8000])

        combined_text = " ".join(text_parts)

        # Extract more keywords initially for better filtering
        extract_count = max(top_n * 2, 20)

        # Extract keywords
        if method == "keybert":
            keywords = self.extract_keybert(combined_text, extract_count)
        else:
            keywords = self.extract_yake(combined_text, extract_count)

        # Post-process: remove very generic terms
        filtered = self._filter_generic_keywords(keywords)

        # Return top N after filtering
        return filtered[:top_n]

    def _filter_generic_keywords(
        self,
        keywords: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """
        Filter out overly generic keywords with improved filtering.

        Args:
            keywords: List of (keyword, score) tuples

        Returns:
            Filtered list
        """
        # Expanded generic terms commonly found in academic papers
        generic_terms = {
            # Meta terms
            'paper', 'study', 'research', 'article', 'work', 'experiment',
            'investigation', 'review', 'survey', 'literature',
            # Structure terms
            'introduction', 'conclusion', 'results', 'discussion',
            'method', 'methodology', 'approach', 'analysis', 'evaluation',
            'background', 'related work', 'future work',
            'figure', 'table', 'section', 'chapter', 'appendix',
            # Vague terms
            'data', 'information', 'system', 'model', 'framework',
            'problem', 'solution', 'issue', 'case', 'example',
            # Common words
            'et al', 'etc', 'i.e', 'e.g', 'via', 'using', 'based',
            'however', 'therefore', 'moreover', 'furthermore',
            'also', 'such', 'various', 'different', 'several',
            'many', 'much', 'more', 'most', 'some', 'other',
            'new', 'recent', 'current', 'previous', 'important',
            'significant', 'main', 'key', 'major', 'general',
            # Time/measurement
            'year', 'years', 'time', 'times', 'number', 'numbers',
            'value', 'values', 'level', 'levels', 'rate', 'rates'
        }

        filtered = []
        seen_normalized = set()  # For deduplication

        for keyword, score in keywords:
            keyword_lower = keyword.lower().strip()

            # Skip if keyword is entirely generic
            if keyword_lower in generic_terms:
                continue

            # Skip very short keywords (< 3 chars)
            if len(keyword) < 3:
                continue

            # Skip keywords that are just numbers or single letters
            if keyword.replace('.', '').replace(',', '').replace('-', '').isdigit():
                continue

            # Skip single character keywords
            if len(keyword_lower.replace(' ', '')) == 1:
                continue

            # Skip keywords that are mostly non-alphanumeric
            alpha_ratio = sum(c.isalnum() for c in keyword) / len(keyword)
            if alpha_ratio < 0.5:
                continue

            # Normalize for deduplication (lowercase, remove plurals)
            normalized = keyword_lower.rstrip('s')

            # Skip if we've seen this (or very similar) keyword
            if normalized in seen_normalized:
                continue

            # Skip keywords with too many words (likely noise)
            if len(keyword.split()) > 4:
                continue

            # Accept this keyword
            seen_normalized.add(normalized)
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
