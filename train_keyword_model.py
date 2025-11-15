#!/usr/bin/env python3
"""
Machine Learning-based Keyword Extraction Training Script

Trains a supervised learning model to improve keyword extraction accuracy
using user-provided PDF + keyword pairs.

Usage:
    # Step 1: Prepare training data
    python train_keyword_model.py --prepare

    # Step 2: Train model
    python train_keyword_model.py --train

    # Step 3: Evaluate model
    python train_keyword_model.py --evaluate
"""

import sys
sys.path.insert(0, '.')

import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
import re

# ML libraries
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report

# Our modules
from src.core.pdf_processor import PDFProcessor
from src.core.metadata_extractor import KeywordExtractor


class KeywordFeatureExtractor:
    """Extract features from candidate keywords for ML training."""

    def __init__(self):
        self.keyword_extractor = KeywordExtractor()

    def extract_features(
        self,
        candidate: str,
        title: str,
        abstract: str,
        full_text: str,
        yake_score: float,
        all_candidates: List[Tuple[str, float]]
    ) -> np.ndarray:
        """
        Extract features for a candidate keyword.

        Returns 12-dimensional feature vector.
        """
        features = []

        # Normalize texts
        title_lower = title.lower()
        abstract_lower = abstract.lower() if abstract else ""
        full_text_lower = full_text.lower() if full_text else ""
        candidate_lower = candidate.lower()

        # Feature 1: YAKE score (normalized 0-1)
        # Lower YAKE score = better, so invert
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
        abstract_freq = abstract_lower.count(candidate_lower) if abstract else 0
        abstract_freq_norm = min(abstract_freq / 5.0, 1.0)  # Cap at 5
        features.append(abstract_freq_norm)

        # Feature 5: Full text frequency (normalized)
        full_freq = full_text_lower.count(candidate_lower) if full_text else 0
        full_freq_norm = min(full_freq / 20.0, 1.0)  # Cap at 20
        features.append(full_freq_norm)

        # Feature 6: N-gram size (1, 2, or 3)
        ngram_size = len(candidate.split())
        ngram_feature = ngram_size / 3.0  # Normalize to 0-1
        features.append(ngram_feature)

        # Feature 7: Keyword length (characters)
        length_norm = min(len(candidate) / 30.0, 1.0)  # Normalize, cap at 30
        features.append(length_norm)

        # Feature 8: Capital letter ratio
        capitals = sum(1 for c in candidate if c.isupper())
        capital_ratio = capitals / len(candidate) if len(candidate) > 0 else 0.0
        features.append(capital_ratio)

        # Feature 9: Alphanumeric ratio
        alphanum = sum(1 for c in candidate if c.isalnum())
        alphanum_ratio = alphanum / len(candidate) if len(candidate) > 0 else 0.0
        features.append(alphanum_ratio)

        # Feature 10: Position in document (first occurrence)
        if full_text:
            first_pos = full_text_lower.find(candidate_lower)
            if first_pos >= 0:
                position_score = 1.0 - (first_pos / len(full_text_lower))
            else:
                position_score = 0.0
        else:
            position_score = 0.5
        features.append(position_score)

        # Feature 11: Contains hyphen or underscore (technical terms)
        has_connector = 1.0 if ('-' in candidate or '_' in candidate) else 0.0
        features.append(has_connector)

        # Feature 12: Rank in YAKE results (normalized)
        try:
            rank = [kw for kw, _ in all_candidates].index(candidate)
            rank_norm = 1.0 - (rank / len(all_candidates))
        except (ValueError, ZeroDivisionError):
            rank_norm = 0.5
        features.append(rank_norm)

        return np.array(features, dtype=np.float32)


def prepare_training_data():
    """
    Interactive tool to prepare training data.
    Guides user through adding PDF + keyword pairs.
    """
    print("="*70)
    print("KEYWORD EXTRACTION ML - TRAINING DATA PREPARATION")
    print("="*70)

    training_data_file = Path("data/keyword_training_data.json")

    # Load existing data if available
    if training_data_file.exists():
        with open(training_data_file, 'r', encoding='utf-8') as f:
            training_data = json.load(f)
        print(f"\n✓ Loaded existing training data: {len(training_data)} samples")
    else:
        training_data = []
        print("\n• Creating new training data file")

    print("\n" + "-"*70)
    print("INSTRUCTIONS:")
    print("1. Place your PDF files in a directory")
    print("2. For each PDF, provide the correct keywords (comma-separated)")
    print("3. The system will learn to extract similar keywords from new papers")
    print("-"*70)

    while True:
        print("\n" + "="*70)
        pdf_path = input("\nEnter PDF path (or 'done' to finish): ").strip()

        if pdf_path.lower() == 'done':
            break

        # Validate PDF exists
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            print(f"✗ File not found: {pdf_path}")
            continue

        if not pdf_file.suffix.lower() == '.pdf':
            print(f"✗ Not a PDF file: {pdf_path}")
            continue

        # Get keywords
        print("\nEnter the correct keywords for this paper (comma-separated):")
        print("Example: heat treatment, microstructure, fatigue life, FEM")
        keywords_input = input("Keywords: ").strip()

        if not keywords_input:
            print("✗ No keywords provided, skipping...")
            continue

        # Parse keywords
        keywords = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]

        if len(keywords) < 3:
            print(f"⚠ Warning: Only {len(keywords)} keywords provided. Recommend at least 5-10.")
            confirm = input("Continue anyway? (yes/no): ")
            if confirm.lower() not in ['yes', 'y']:
                continue

        # Add to training data
        sample = {
            "pdf_path": str(pdf_file.absolute()),
            "keywords": keywords
        }

        training_data.append(sample)

        print(f"✓ Added sample #{len(training_data)}")
        print(f"  PDF: {pdf_file.name}")
        print(f"  Keywords ({len(keywords)}): {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")

    # Save training data
    if training_data:
        training_data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(training_data_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)

        print("\n" + "="*70)
        print(f"✓ Training data saved: {training_data_file}")
        print(f"  Total samples: {len(training_data)}")
        print(f"  Total keywords: {sum(len(s['keywords']) for s in training_data)}")
        print("\nNext step: python train_keyword_model.py --train")
    else:
        print("\n✗ No training data collected")


def train_model():
    """
    Train ML model for keyword ranking.
    """
    print("="*70)
    print("KEYWORD EXTRACTION ML - MODEL TRAINING")
    print("="*70)

    training_data_file = Path("data/keyword_training_data.json")

    if not training_data_file.exists():
        print("\n✗ Training data not found!")
        print("  Run: python train_keyword_model.py --prepare")
        return

    # Load training data
    with open(training_data_file, 'r', encoding='utf-8') as f:
        training_data = json.load(f)

    print(f"\n✓ Loaded {len(training_data)} training samples")

    if len(training_data) < 10:
        print(f"\n⚠ Warning: Only {len(training_data)} samples. Recommend at least 20-30 for good performance.")
        confirm = input("Continue training anyway? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            return

    # Feature extractor
    feature_extractor = KeywordFeatureExtractor()

    # Collect features and labels
    X_data = []  # Features
    y_data = []  # Labels (1 = correct keyword, 0 = incorrect)

    print("\nExtracting features from PDFs...")

    for i, sample in enumerate(training_data):
        pdf_path = sample['pdf_path']
        true_keywords = [kw.lower().strip() for kw in sample['keywords']]

        print(f"[{i+1}/{len(training_data)}] Processing {Path(pdf_path).name}...")

        try:
            # Extract PDF text and metadata
            with PDFProcessor(pdf_path) as processor:
                metadata = processor.extract_metadata(use_semantic_scholar=False)
                full_text = processor.extract_text(max_pages=20)

            title = metadata.get('title', '')
            abstract = metadata.get('abstract', '')

            # Extract candidate keywords using YAKE
            candidates = feature_extractor.keyword_extractor.extract_yake(
                title * 5 + (abstract * 3 if abstract else '') + full_text[:8000],
                top_n=30
            )

            print(f"  Extracted {len(candidates)} candidates")

            # For each candidate, extract features and label
            positive_count = 0
            for candidate, yake_score in candidates:
                candidate_lower = candidate.lower().strip()

                # Extract features
                features = feature_extractor.extract_features(
                    candidate, title, abstract, full_text,
                    yake_score, candidates
                )

                # Label: 1 if this is a true keyword, 0 otherwise
                # Use fuzzy matching (check if candidate is in any true keyword or vice versa)
                is_correct = any(
                    candidate_lower in true_kw or true_kw in candidate_lower
                    for true_kw in true_keywords
                )

                X_data.append(features)
                y_data.append(1 if is_correct else 0)

                if is_correct:
                    positive_count += 1

            print(f"  Found {positive_count}/{len(candidates)} matching keywords")

        except Exception as e:
            print(f"  ✗ Error processing {Path(pdf_path).name}: {e}")
            continue

    # Convert to numpy arrays
    X = np.array(X_data, dtype=np.float32)
    y = np.array(y_data, dtype=np.int32)

    print("\n" + "="*70)
    print("TRAINING DATA SUMMARY")
    print("="*70)
    print(f"Total samples: {len(X)}")
    print(f"Positive (correct keywords): {np.sum(y)} ({np.mean(y)*100:.1f}%)")
    print(f"Negative (incorrect keywords): {len(y) - np.sum(y)} ({(1-np.mean(y))*100:.1f}%)")
    print(f"Feature dimensions: {X.shape[1]}")

    if len(X) < 50:
        print(f"\n⚠ Warning: Only {len(X)} training examples. Recommend 200+ for best results.")

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Train Random Forest
    print("\n" + "="*70)
    print("TRAINING MODEL...")
    print("="*70)

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',  # Handle imbalanced data
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    print("✓ Model trained!")

    # Evaluate
    print("\n" + "="*70)
    print("MODEL EVALUATION")
    print("="*70)

    # Training accuracy
    train_acc = model.score(X_train, y_train)
    print(f"Training accuracy: {train_acc*100:.2f}%")

    # Test accuracy
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc*100:.2f}%")

    # Detailed metrics
    y_pred = model.predict(X_test)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"\nPrecision: {precision*100:.2f}% (정확도: 추출한 키워드 중 정답 비율)")
    print(f"Recall: {recall*100:.2f}% (재현율: 정답 키워드 중 찾아낸 비율)")
    print(f"F1 Score: {f1*100:.2f}% (종합 점수)")

    # Feature importance
    print("\n" + "="*70)
    print("FEATURE IMPORTANCE (Top 5)")
    print("="*70)

    feature_names = [
        "YAKE score",
        "In title",
        "Title overlap",
        "Abstract freq",
        "Full text freq",
        "N-gram size",
        "Keyword length",
        "Capital ratio",
        "Alphanum ratio",
        "Position score",
        "Has connector",
        "YAKE rank"
    ]

    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]

    for i in range(min(5, len(feature_names))):
        idx = indices[i]
        print(f"{i+1}. {feature_names[idx]}: {importances[idx]*100:.2f}%")

    # Save model
    model_dir = Path("models")
    model_dir.mkdir(parents=True, exist_ok=True)

    model_file = model_dir / "keyword_ranker.pkl"
    with open(model_file, 'wb') as f:
        pickle.dump(model, f)

    print("\n" + "="*70)
    print(f"✓ Model saved: {model_file}")
    print("="*70)

    print("\nNext steps:")
    print("1. Test model: python train_keyword_model.py --evaluate")
    print("2. Use in app: KeywordExtractor(..., method='ml')")

    return model


def evaluate_model():
    """
    Evaluate trained model on test data.
    """
    print("="*70)
    print("KEYWORD EXTRACTION ML - MODEL EVALUATION")
    print("="*70)

    model_file = Path("models/keyword_ranker.pkl")
    if not model_file.exists():
        print("\n✗ Model not found! Train first:")
        print("  python train_keyword_model.py --train")
        return

    # Load model
    with open(model_file, 'rb') as f:
        model = pickle.load(f)

    print(f"\n✓ Loaded model from {model_file}")

    # Test on a sample PDF
    test_pdf = input("\nEnter path to test PDF: ").strip()

    if not Path(test_pdf).exists():
        print(f"✗ File not found: {test_pdf}")
        return

    print("\nProcessing PDF...")

    feature_extractor = KeywordFeatureExtractor()

    try:
        with PDFProcessor(test_pdf) as processor:
            metadata = processor.extract_metadata(use_semantic_scholar=False)
            full_text = processor.extract_text(max_pages=20)

        title = metadata.get('title', '')
        abstract = metadata.get('abstract', '')

        # Extract candidates
        candidates = feature_extractor.keyword_extractor.extract_yake(
            title * 5 + (abstract * 3 if abstract else '') + full_text[:8000],
            top_n=30
        )

        print(f"\nExtracted {len(candidates)} candidate keywords")

        # Score each candidate
        scored_candidates = []
        for candidate, yake_score in candidates:
            features = feature_extractor.extract_features(
                candidate, title, abstract, full_text,
                yake_score, candidates
            )

            # Get probability from model
            prob = model.predict_proba([features])[0][1]  # Probability of being a good keyword

            scored_candidates.append((candidate, prob, yake_score))

        # Sort by ML probability (descending)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Display results
        print("\n" + "="*70)
        print("TOP 10 KEYWORDS (ML-ranked)")
        print("="*70)
        print(f"{'Rank':<6} {'Keyword':<30} {'ML Score':<12} {'YAKE Score':<12}")
        print("-"*70)

        for i, (keyword, ml_score, yake_score) in enumerate(scored_candidates[:10]):
            print(f"{i+1:<6} {keyword:<30} {ml_score:>10.3f}  {yake_score:>10.3f}")

        print("\n" + "="*70)
        print("COMPARISON: YAKE vs ML")
        print("="*70)

        # Top 10 by YAKE (original)
        yake_top10 = [kw for kw, _ in candidates[:10]]

        # Top 10 by ML
        ml_top10 = [kw for kw, _, _ in scored_candidates[:10]]

        # Only in YAKE
        only_yake = set(yake_top10) - set(ml_top10)
        # Only in ML
        only_ml = set(ml_top10) - set(yake_top10)
        # In both
        common = set(yake_top10) & set(ml_top10)

        print(f"\nCommon to both (good!): {len(common)}/10")
        if common:
            for kw in common:
                print(f"  • {kw}")

        print(f"\nOnly in YAKE top-10 (ML rejected): {len(only_yake)}")
        if only_yake:
            for kw in only_yake:
                print(f"  • {kw}")

        print(f"\nOnly in ML top-10 (ML promoted): {len(only_ml)}")
        if only_ml:
            for kw in only_ml:
                print(f"  • {kw}")

    except Exception as e:
        print(f"\n✗ Error: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Train ML model for keyword extraction"
    )
    parser.add_argument(
        '--prepare',
        action='store_true',
        help='Prepare training data (interactive)'
    )
    parser.add_argument(
        '--train',
        action='store_true',
        help='Train model on prepared data'
    )
    parser.add_argument(
        '--evaluate',
        action='store_true',
        help='Evaluate trained model on test PDF'
    )

    args = parser.parse_args()

    if args.prepare:
        prepare_training_data()
    elif args.train:
        train_model()
    elif args.evaluate:
        evaluate_model()
    else:
        print("Usage:")
        print("  python train_keyword_model.py --prepare   # Prepare training data")
        print("  python train_keyword_model.py --train     # Train model")
        print("  python train_keyword_model.py --evaluate  # Evaluate model")


if __name__ == "__main__":
    main()
