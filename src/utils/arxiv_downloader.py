"""
arXiv paper downloader utility.
Downloads academic papers from arXiv for testing purposes.
"""

import os
import arxiv
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm


class ArxivDownloader:
    """Download papers from arXiv based on search queries."""

    def __init__(self, download_dir: str = "test_pdfs"):
        """
        Initialize the arXiv downloader.

        Args:
            download_dir: Directory to save downloaded PDFs
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True, parents=True)

    def download_papers(
        self,
        query: str,
        max_results: int = 10,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance
    ) -> List[str]:
        """
        Download papers from arXiv based on a search query.

        Args:
            query: Search query (e.g., "attention mechanism", "neural networks")
            max_results: Maximum number of papers to download
            sort_by: Sort criterion (Relevance, LastUpdatedDate, SubmittedDate)

        Returns:
            List of downloaded file paths
        """
        print(f"Searching arXiv for: '{query}'")
        print(f"Max results: {max_results}")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )

        downloaded_files = []

        for result in tqdm(search.results(), total=max_results, desc="Downloading"):
            try:
                # Create safe filename from paper ID
                paper_id = result.entry_id.split('/')[-1]
                filename = f"{paper_id}.pdf"
                filepath = self.download_dir / filename

                # Skip if already downloaded
                if filepath.exists():
                    print(f"  ✓ Already exists: {filename}")
                    downloaded_files.append(str(filepath))
                    continue

                # Download the PDF
                result.download_pdf(dirpath=str(self.download_dir), filename=filename)
                print(f"  ✓ Downloaded: {filename} - {result.title[:50]}...")
                downloaded_files.append(str(filepath))

            except Exception as e:
                print(f"  ✗ Error downloading {result.entry_id}: {e}")
                continue

        print(f"\n✓ Downloaded {len(downloaded_files)} papers to {self.download_dir}")
        return downloaded_files

    def download_by_categories(
        self,
        categories: List[str],
        papers_per_category: int = 5
    ) -> List[str]:
        """
        Download papers from specific arXiv categories.

        Args:
            categories: List of arXiv categories (e.g., ['cs.AI', 'cs.LG'])
            papers_per_category: Number of papers per category

        Returns:
            List of downloaded file paths
        """
        all_files = []

        for category in categories:
            print(f"\n{'='*60}")
            print(f"Category: {category}")
            print('='*60)

            files = self.download_papers(
                query=f"cat:{category}",
                max_results=papers_per_category,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            all_files.extend(files)

        return all_files


def download_test_dataset():
    """
    Download a curated test dataset covering diverse paper types.
    This is the recommended way to get started.
    """
    downloader = ArxivDownloader("test_pdfs")

    print("\n" + "="*60)
    print("DOWNLOADING TEST DATASET FROM ARXIV")
    print("="*60)

    # Download papers from different categories
    test_queries = [
        ("transformer neural networks", 5),
        ("graph neural networks citation", 5),
        ("natural language processing", 5),
        ("computer vision", 5),
    ]

    all_files = []
    for query, count in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        files = downloader.download_papers(query, max_results=count)
        all_files.extend(files)

    print("\n" + "="*60)
    print(f"✓ DOWNLOAD COMPLETE: {len(all_files)} papers ready for testing")
    print(f"Location: {downloader.download_dir.absolute()}")
    print("="*60)

    return all_files


if __name__ == "__main__":
    # Run this script directly to download test papers
    download_test_dataset()
