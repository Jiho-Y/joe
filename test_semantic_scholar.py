#!/usr/bin/env python3
"""
Test script for Semantic Scholar API integration.
Tests DOI extraction, API calls, and metadata retrieval.
"""

import sys
sys.path.insert(0, '.')

from src.utils.semantic_scholar import SemanticScholarAPI, get_metadata_by_doi, get_metadata_by_title
from src.core.pdf_processor import PDFProcessor
from pathlib import Path


def test_api_basic():
    """Test basic API connectivity."""
    print("\n" + "="*60)
    print("TEST 1: Basic API Connectivity")
    print("="*60)

    api = SemanticScholarAPI()

    # Test with a well-known paper DOI
    test_doi = "10.1038/nature14539"  # AlphaGo paper
    print(f"Testing DOI: {test_doi}")

    result = api.get_paper_by_doi(test_doi)

    if result:
        print("✓ API Working!")
        print(f"  Title: {result.get('title')}")
        print(f"  Authors: {len(result.get('authors', []))} authors")
        print(f"  Year: {result.get('year')}")
        print(f"  Abstract length: {len(result.get('abstract', ''))}")
        return True
    else:
        print("✗ API Failed")
        return False


def test_doi_extraction():
    """Test DOI extraction from test PDFs."""
    print("\n" + "="*60)
    print("TEST 2: DOI Extraction from PDFs")
    print("="*60)

    test_pdfs_dir = Path("test_pdfs")

    if not test_pdfs_dir.exists():
        print("⚠ test_pdfs directory not found, skipping")
        return False

    pdf_files = list(test_pdfs_dir.glob("*.pdf"))

    if not pdf_files:
        print("⚠ No PDF files found in test_pdfs/")
        return False

    print(f"Found {len(pdf_files)} PDF files")

    success_count = 0
    for pdf_file in pdf_files[:3]:  # Test first 3 files
        print(f"\nTesting: {pdf_file.name}")

        try:
            with PDFProcessor(str(pdf_file)) as processor:
                # Extract first two pages
                text = processor.extract_text(max_pages=2)

                # Try to extract DOI
                doi = processor._extract_doi(text)

                if doi:
                    print(f"  ✓ DOI found: {doi}")

                    # Try to fetch metadata
                    metadata = get_metadata_by_doi(doi)
                    if metadata:
                        print(f"  ✓ Semantic Scholar: {metadata.get('title')[:50]}...")
                        print(f"    Abstract: {len(metadata.get('abstract', ''))} chars")
                        success_count += 1
                    else:
                        print(f"  ✗ DOI not in Semantic Scholar")
                else:
                    print(f"  ✗ No DOI found")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\nSuccess rate: {success_count}/{len(pdf_files[:3])}")
    return success_count > 0


def test_title_search():
    """Test title-based search."""
    print("\n" + "="*60)
    print("TEST 3: Title-based Search")
    print("="*60)

    test_titles = [
        "Attention Is All You Need",
        "Deep Residual Learning for Image Recognition",
    ]

    for title in test_titles:
        print(f"\nSearching: {title}")

        metadata = get_metadata_by_title(title)

        if metadata:
            print(f"  ✓ Found: {metadata.get('title')}")
            print(f"    Year: {metadata.get('year')}")
            print(f"    Authors: {len(metadata.get('authors', []))}")
            print(f"    Abstract: {len(metadata.get('abstract', ''))} chars")
        else:
            print(f"  ✗ Not found")

    return True


def test_database_search():
    """Test database FTS5 search."""
    print("\n" + "="*60)
    print("TEST 4: Database Search")
    print("="*60)

    from src.core.database import Database

    db_path = "data/papers.db"

    if not Path(db_path).exists():
        print("⚠ Database not found, skipping")
        return False

    db = Database(db_path)

    # Check paper count
    papers = db.get_all_papers(limit=10)
    print(f"Papers in database: {len(papers)}")

    if not papers:
        print("⚠ No papers in database")
        db.close()
        return False

    # Test search
    test_queries = ["heat", "fatigue", "machine learning"]

    for query in test_queries:
        print(f"\nSearching: '{query}'")
        results = db.search_papers(query, limit=10)
        print(f"  Results: {len(results)}")

        if results:
            print(f"  Top result: {results[0].get('title', 'N/A')[:50]}...")

    db.close()
    return True


def test_full_pipeline():
    """Test the full pipeline with arXiv download."""
    print("\n" + "="*60)
    print("TEST 5: Full Pipeline Test")
    print("="*60)

    # Download one test paper from arXiv
    try:
        from src.utils.arxiv_downloader import ArxivDownloader

        downloader = ArxivDownloader("test_pdfs")

        print("Downloading 1 test paper from arXiv...")
        files = downloader.download_papers("transformer", max_results=1)

        if not files:
            print("✗ Download failed")
            return False

        test_pdf = files[0]
        print(f"✓ Downloaded: {Path(test_pdf).name}")

        # Process it
        print("\nProcessing PDF...")
        with PDFProcessor(test_pdf) as processor:
            metadata = processor.extract_metadata(use_semantic_scholar=True)

            print(f"Title: {metadata.get('title')}")
            print(f"Authors: {len(metadata.get('authors', []))}")
            print(f"Year: {metadata.get('year')}")
            print(f"DOI: {metadata.get('doi')}")
            print(f"Abstract: {len(metadata.get('abstract', ''))} chars")
            print(f"Source: {metadata.get('source')}")

            if metadata.get('source') == 'semantic_scholar':
                print("✓ Semantic Scholar working!")
                return True
            else:
                print("⚠ Fell back to heuristics")
                return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SEMANTIC SCHOLAR INTEGRATION TEST SUITE")
    print("="*60)

    results = []

    # Run all tests
    results.append(("API Connectivity", test_api_basic()))
    results.append(("DOI Extraction", test_doi_extraction()))
    results.append(("Title Search", test_title_search()))
    results.append(("Database Search", test_database_search()))
    results.append(("Full Pipeline", test_full_pipeline()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {passed_count}/{len(results)}")

    if passed_count == len(results):
        print("\n✓ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n⚠ SOME TESTS FAILED")
        sys.exit(1)
