"""
Semantic Scholar API client for fetching paper metadata.

Semantic Scholar provides free academic paper metadata including:
- Accurate author, title, year, abstract
- Citation counts and influential citations
- Reference lists and citation network
- 200M+ papers from arXiv, PubMed, ACM, IEEE, etc.

API: https://api.semanticscholar.org
Docs: https://api.semanticscholar.org/api-docs/
Rate limit: 100 requests/second (no auth needed for basic use)
"""

import requests
from typing import Optional, Dict, List
import time
from urllib.parse import quote


class SemanticScholarAPI:
    """Client for Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    # Fields to request from API
    PAPER_FIELDS = [
        "paperId",
        "title",
        "abstract",
        "year",
        "authors",
        "venue",
        "publicationDate",
        "citationCount",
        "influentialCitationCount",
        "references",
        "externalIds",
        "url",
        "openAccessPdf",
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Semantic Scholar API client.

        Args:
            api_key: Optional API key for higher rate limits
                    (free tier: 100 req/s, with key: 1000 req/s)
        """
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-api-key": api_key})

        # Simple in-memory cache to avoid duplicate requests
        self._cache = {}

    def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Fetch paper metadata by DOI.

        Args:
            doi: DOI string (e.g., "10.1234/example")

        Returns:
            Dictionary with paper metadata or None if not found
        """
        # Check cache
        cache_key = f"doi:{doi}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Clean DOI (remove common prefixes)
        clean_doi = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")

        # Build URL
        fields = ",".join(self.PAPER_FIELDS)
        url = f"{self.BASE_URL}/paper/DOI:{clean_doi}?fields={fields}"

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self._cache[cache_key] = data
                return data

            elif response.status_code == 404:
                # DOI not found in Semantic Scholar
                print(f"DOI not found in Semantic Scholar: {doi}")
                return None

            elif response.status_code == 429:
                # Rate limit exceeded - wait and retry once
                print("Rate limit hit, waiting 1 second...")
                time.sleep(1)
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self._cache[cache_key] = data
                    return data

            else:
                print(f"Semantic Scholar API error: {response.status_code}")
                return None

        except Exception as e:
            print(f"Error fetching DOI {doi}: {e}")
            return None

    def search_paper_by_title(self, title: str, limit: int = 5) -> List[Dict]:
        """
        Search for papers by title.

        Args:
            title: Paper title
            limit: Maximum number of results (default 5)

        Returns:
            List of paper dictionaries
        """
        # Check cache
        cache_key = f"title:{title[:50]}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Clean and encode title
        clean_title = title.strip()[:200]  # Limit length
        encoded_title = quote(clean_title)

        # Build URL
        fields = ",".join(self.PAPER_FIELDS)
        url = f"{self.BASE_URL}/paper/search?query={encoded_title}&fields={fields}&limit={limit}"

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                papers = data.get("data", [])
                self._cache[cache_key] = papers
                return papers

            elif response.status_code == 429:
                # Rate limit - retry once
                time.sleep(1)
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    papers = data.get("data", [])
                    self._cache[cache_key] = papers
                    return papers

            return []

        except Exception as e:
            print(f"Error searching title '{title}': {e}")
            return []

    def get_best_title_match(self, title: str, threshold: float = 0.8) -> Optional[Dict]:
        """
        Search for paper by title and return best match.

        Args:
            title: Paper title
            threshold: Minimum similarity threshold (0-1)

        Returns:
            Best matching paper or None
        """
        results = self.search_paper_by_title(title, limit=5)

        if not results:
            return None

        # First result is usually the best match
        # Semantic Scholar's search is pretty good
        best_match = results[0]

        # Simple similarity check: does title contain most words from query?
        query_words = set(title.lower().split())
        result_words = set(best_match.get("title", "").lower().split())

        # Calculate Jaccard similarity
        if query_words:
            intersection = query_words & result_words
            union = query_words | result_words
            similarity = len(intersection) / len(union) if union else 0

            if similarity >= threshold:
                return best_match

        return None

    def format_metadata(self, paper_data: Dict) -> Dict:
        """
        Convert Semantic Scholar API response to our metadata format.

        Args:
            paper_data: Raw API response

        Returns:
            Formatted metadata dictionary
        """
        # Extract author names
        authors = []
        if paper_data.get("authors"):
            for author in paper_data["authors"]:
                name = author.get("name")
                if name:
                    authors.append(name)

        # Get DOI from externalIds
        doi = None
        external_ids = paper_data.get("externalIds", {})
        if external_ids:
            doi = external_ids.get("DOI")

        # Get arXiv ID
        arxiv_id = external_ids.get("ArXiv") if external_ids else None

        # Format metadata
        metadata = {
            "title": paper_data.get("title"),
            "authors": authors,
            "year": paper_data.get("year"),
            "abstract": paper_data.get("abstract"),
            "journal": paper_data.get("venue"),
            "doi": doi,
            "arxiv_id": arxiv_id,
            "citation_count": paper_data.get("citationCount", 0),
            "influential_citations": paper_data.get("influentialCitationCount", 0),
            "semantic_scholar_id": paper_data.get("paperId"),
            "semantic_scholar_url": paper_data.get("url"),
            "source": "semantic_scholar",
        }

        # Get PDF URL if available
        open_access = paper_data.get("openAccessPdf")
        if open_access:
            metadata["pdf_url"] = open_access.get("url")

        return metadata


# Convenience functions
def get_metadata_by_doi(doi: str) -> Optional[Dict]:
    """
    Quick function to get paper metadata by DOI.

    Args:
        doi: DOI string

    Returns:
        Formatted metadata or None
    """
    api = SemanticScholarAPI()
    paper_data = api.get_paper_by_doi(doi)

    if paper_data:
        return api.format_metadata(paper_data)

    return None


def get_metadata_by_title(title: str) -> Optional[Dict]:
    """
    Quick function to get paper metadata by title search.

    Args:
        title: Paper title

    Returns:
        Formatted metadata or None
    """
    api = SemanticScholarAPI()
    paper_data = api.get_best_title_match(title)

    if paper_data:
        return api.format_metadata(paper_data)

    return None
