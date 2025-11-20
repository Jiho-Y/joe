#!/usr/bin/env python3
"""
Diagnostic and repair script for Research Paper Manager.
Checks all functionality and offers to fix issues.
"""

import sys
sys.path.insert(0, '.')

import json
from datetime import datetime
from pathlib import Path
from src.core.database import Database
from src.core.pdf_processor import PDFProcessor
from src.utils.semantic_scholar import SemanticScholarAPI, get_metadata_by_doi
from src.utils.config import get_config

def test_semantic_scholar():
    """Test if Semantic Scholar API is working."""
    print("\n" + "="*60)
    print("TEST: Semantic Scholar API Connectivity")
    print("="*60)

    api = SemanticScholarAPI()
    test_doi = "10.1038/nature14539"  # AlphaGo paper

    print(f"Testing with DOI: {test_doi}")
    result = api.get_paper_by_doi(test_doi)

    if result:
        print("✓ API is WORKING")
        print(f"  Title: {result.get('title')}")
        print(f"  Year: {result.get('year')}")
        print(f"  Abstract length: {len(result.get('abstract', ''))} characters")
        return True
    else:
        print("✗ API FAILED - Semantic Scholar not accessible")
        return False

def test_doi_extraction():
    """Test improved DOI extraction on sample PDFs."""
    print("\n" + "="*60)
    print("TEST: DOI Extraction (Enhanced Algorithm)")
    print("="*60)

    test_pdfs_dir = Path("test_pdfs")
    if not test_pdfs_dir.exists():
        print("⚠ test_pdfs directory not found")
        return False

    pdf_files = list(test_pdfs_dir.glob("*.pdf"))
    if not pdf_files:
        print("⚠ No PDF files found in test_pdfs/")
        return False

    print(f"Testing DOI extraction on {min(len(pdf_files), 5)} PDFs...\n")

    success_count = 0
    for i, pdf_file in enumerate(pdf_files[:5]):
        print(f"[{i+1}] {pdf_file.name}")
        try:
            with PDFProcessor(str(pdf_file)) as processor:
                text = processor.extract_text(max_pages=4)
                doi = processor._extract_doi(text)

                if doi:
                    print(f"  → DOI found: {doi}")
                    success_count += 1
                else:
                    print(f"  → No DOI found")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n✓ DOI extraction success rate: {success_count}/{min(len(pdf_files), 5)}")
    return success_count > 0

def check_database():
    """Check database contents."""
    print("\n" + "="*60)
    print("TEST: Database Contents")
    print("="*60)

    db_path = "data/papers.db"
    if not Path(db_path).exists():
        print("✗ Database does not exist yet")
        return False

    db = Database(db_path)
    papers = db.get_all_papers(limit=10)

    print(f"Papers in database: {len(papers)}")

    if not papers:
        print("⚠ Database is empty")
        db.close()
        return False

    # Check first few papers for abstract
    papers_with_abstract = 0
    papers_without_abstract = 0

    for paper in papers[:5]:
        if paper.get('abstract') and len(paper.get('abstract', '')) > 100:
            papers_with_abstract += 1
        else:
            papers_without_abstract += 1

    print(f"\nSample of first 5 papers:")
    print(f"  ✓ With abstracts: {papers_with_abstract}")
    print(f"  ✗ Without abstracts: {papers_without_abstract}")

    if papers_without_abstract > 0:
        print("\n⚠ WARNING: Some papers are missing abstracts!")
        print("  This usually means they were imported before Semantic Scholar integration.")

    db.close()
    return True

def test_search():
    """Test search functionality (title + keywords only)."""
    print("\n" + "="*60)
    print("TEST: Search Functionality (Title + Keywords)")
    print("="*60)

    db_path = "data/papers.db"
    if not Path(db_path).exists():
        print("✗ Database does not exist")
        return False

    db = Database(db_path)

    # Get a sample paper to search for
    papers = db.get_all_papers(limit=1)
    if not papers:
        print("✗ No papers to search")
        db.close()
        return False

    # Extract a word from the title to search
    sample_paper = papers[0]
    title_words = sample_paper['title'].split()
    if len(title_words) > 2:
        search_word = title_words[1]  # Use second word
    else:
        search_word = title_words[0]

    print(f"Test 1: Search by title word '{search_word}'")
    print(f"  (Word from paper: {sample_paper['title'][:60]}...)")

    results = db.search_papers(search_word, limit=10)

    title_search_success = False
    if results:
        print(f"  ✓ Found {len(results)} results")
        # Check if our sample paper is in results
        found_sample = any(r['id'] == sample_paper['id'] for r in results)
        if found_sample:
            print(f"  ✓ Expected paper found in results")
            title_search_success = True
        else:
            print(f"  ⚠ Expected paper not in results")
    else:
        print(f"  ✗ No results for '{search_word}'")

    # Test 2: Search by keyword (if keywords exist)
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT keyword FROM Keywords
        WHERE paper_id = ?
        LIMIT 1
    """, (sample_paper['id'],))

    keyword_row = cursor.fetchone()
    keyword_search_success = False

    if keyword_row:
        test_keyword = keyword_row['keyword']
        print(f"\nTest 2: Search by keyword '{test_keyword}'")

        results = db.search_papers(test_keyword, limit=10)
        if results:
            print(f"  ✓ Found {len(results)} results via keyword search")
            found_sample = any(r['id'] == sample_paper['id'] for r in results)
            if found_sample:
                print(f"  ✓ Expected paper found via keyword")
                keyword_search_success = True
            else:
                print(f"  ⚠ Expected paper not in keyword results")
        else:
            print(f"  ⚠ No results for keyword '{test_keyword}'")
    else:
        print("\nTest 2: Skipped (no keywords for sample paper)")

    db.close()

    overall_success = title_search_success or keyword_search_success
    if overall_success:
        print(f"\n✓ Search functionality WORKING (title + keywords)")
    else:
        print(f"\n⚠ Search needs attention (see details above)")

    return overall_success

def re_extract_metadata():
    """Re-extract metadata for all papers using Semantic Scholar."""
    print("\n" + "="*60)
    print("RE-EXTRACT METADATA (with Semantic Scholar)")
    print("="*60)

    db_path = "data/papers.db"
    if not Path(db_path).exists():
        print("✗ Database does not exist")
        return False

    db = Database(db_path)
    papers = db.get_all_papers()

    if not papers:
        print("No papers to re-extract")
        db.close()
        return False

    print(f"Found {len(papers)} papers")
    response = input(f"\nRe-extract metadata for all papers? This will:\n"
                     f"  1. Use Semantic Scholar to get accurate metadata\n"
                     f"  2. Update abstracts, authors, years\n"
                     f"  3. Rebuild full-text search index\n"
                     f"Proceed? (yes/no): ")

    if response.lower() not in ['yes', 'y']:
        print("Cancelled")
        db.close()
        return False

    print("\nRe-extracting metadata...")
    success_count = 0
    semantic_scholar_count = 0

    for i, paper in enumerate(papers):
        pdf_path = paper['pdf_path']
        paper_id = paper['id']

        print(f"\n[{i+1}/{len(papers)}] {Path(pdf_path).name}")

        if not Path(pdf_path).exists():
            print(f"  ⚠ PDF not found, skipping")
            continue

        try:
            with PDFProcessor(pdf_path) as processor:
                # Extract with Semantic Scholar enabled
                metadata = processor.extract_metadata(use_semantic_scholar=True)
                full_text = processor.extract_text(max_pages=50)

                # Update database
                cursor = db.conn.cursor()
                authors_json = json.dumps(metadata.get('authors')) if metadata.get('authors') else None
                modified_date = int(datetime.now().timestamp())

                cursor.execute("""
                    UPDATE Papers
                    SET title = ?, authors = ?, year = ?, journal = ?,
                        doi = ?, arxiv_id = ?, abstract = ?, modified_date = ?
                    WHERE id = ?
                """, (
                    metadata.get('title'),
                    authors_json,
                    metadata.get('year'),
                    metadata.get('journal'),
                    metadata.get('doi'),
                    metadata.get('arxiv_id'),
                    metadata.get('abstract'),
                    modified_date,
                    paper_id
                ))

                # Update full-text index
                db.update_full_text_index(paper_id, full_text)
                db.conn.commit()

                # Check if we got data from Semantic Scholar
                if metadata.get('source') == 'semantic_scholar':
                    print(f"  ✓ Updated from Semantic Scholar")
                    semantic_scholar_count += 1
                else:
                    print(f"  ⚠ Used heuristic extraction")

                success_count += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    db.close()

    print(f"\n" + "="*60)
    print(f"Re-extraction complete!")
    print(f"  Successfully updated: {success_count}/{len(papers)}")
    print(f"  From Semantic Scholar: {semantic_scholar_count}")
    print("="*60)

    return True

def check_config():
    """Check configuration."""
    print("\n" + "="*60)
    print("TEST: Configuration")
    print("="*60)

    config = get_config()

    api_key = config.get_semantic_scholar_api_key()
    if api_key:
        print(f"✓ API key configured: ...{api_key[-4:]}")
    else:
        print("⚠ No API key configured (using free tier)")
        print("  Free tier: 100 requests/second")
        print("  With API key: 1000 requests/second")
        print("\n  To add API key:")
        print("  1. Get free key from: https://www.semanticscholar.org/product/api")
        print("  2. Add to data/config.json:")
        print('     "semantic_scholar": {"api_key": "YOUR_KEY"}')

    return True

def main():
    print("="*60)
    print("RESEARCH PAPER MANAGER - DIAGNOSTIC TOOL (v0.2.1)")
    print("="*60)

    # Run all tests
    results = {}
    results['config'] = check_config()
    results['semantic_scholar'] = test_semantic_scholar()
    results['doi_extraction'] = test_doi_extraction()
    results['database'] = check_database()
    results['search'] = test_search()

    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    # Offer fixes
    print("\n" + "="*60)
    print("AVAILABLE FIXES")
    print("="*60)

    if not results['semantic_scholar']:
        print("⚠ Semantic Scholar API not working")
        print("  - Check internet connection")
        print("  - Try again later (might be temporary outage)")

    if results['database'] and not results['search']:
        print("\n⚠ Search not working but database exists")
        print("  This is likely because FTS5 index needs rebuilding")
        print("\n  RECOMMENDED FIX:")
        print("  Run: python diagnose_and_fix.py --rebuild-index")

    if results['database']:
        print("\n✓ Re-extract metadata option available")
        print("  This will update all papers with Semantic Scholar data")
        print("  Run: python diagnose_and_fix.py --re-extract")

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--re-extract':
            re_extract_metadata()
        elif sys.argv[1] == '--rebuild-index':
            rebuild_search_index()
        else:
            print(f"\nUnknown option: {sys.argv[1]}")
            print("Available options:")
            print("  --re-extract    Re-extract metadata for all papers")
            print("  --rebuild-index Rebuild full-text search index")

def rebuild_search_index():
    """Rebuild the full-text search index."""
    print("\n" + "="*60)
    print("REBUILD FULL-TEXT SEARCH INDEX")
    print("="*60)

    db_path = "data/papers.db"
    if not Path(db_path).exists():
        print("✗ Database does not exist")
        return False

    db = Database(db_path)
    papers = db.get_all_papers()

    print(f"Found {len(papers)} papers")
    response = input("Rebuild search index for all papers? (yes/no): ")

    if response.lower() not in ['yes', 'y']:
        print("Cancelled")
        db.close()
        return False

    print("\nRebuilding index...")

    # Clear existing index
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM FullTextIndex")
    db.conn.commit()

    success_count = 0
    for i, paper in enumerate(papers):
        pdf_path = paper['pdf_path']
        paper_id = paper['id']

        print(f"[{i+1}/{len(papers)}] Indexing {Path(pdf_path).name}...", end='\r')

        if not Path(pdf_path).exists():
            continue

        try:
            with PDFProcessor(pdf_path) as processor:
                full_text = processor.extract_text(max_pages=50)
                db.update_full_text_index(paper_id, full_text)
            success_count += 1
        except Exception as e:
            print(f"\n  Error indexing {Path(pdf_path).name}: {e}")

    db.conn.commit()
    db.close()

    print(f"\n✓ Index rebuilt for {success_count}/{len(papers)} papers")
    return True

if __name__ == "__main__":
    main()
