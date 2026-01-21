#!/usr/bin/env python3
"""
Generate sample posts for testing the review workflow.

Usage:
  python scripts/generate_sample_posts.py --count 3
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import Database
from src.trends import TrendFetcher
from src.post_generator import PostGenerator
from src.logger import logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sample posts for review.")
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of posts to generate (default: 3)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.7,
        help="Minimum relevance score for trends (default: 0.7)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print(f"Generating {args.count} sample posts...")
    print(f"Minimum relevance score: {args.min_score}\n")

    # Initialize components
    db = Database()
    fetcher = TrendFetcher(db=db)
    generator = PostGenerator(db=db)

    # Fetch trends
    print("1. Fetching trends...")
    trends = fetcher.fetch_all_trends(save_to_db=True)

    # Filter by relevance
    trends = [t for t in trends if t.get("relevance_score", 0) >= args.min_score]

    if len(trends) < args.count:
        print(f"Warning: Only {len(trends)} trends found (requested {args.count})")

    # Generate posts
    print(f"2. Generating {min(args.count, len(trends))} posts...\n")

    results = generator.generate_posts_batch(
        trends[:args.count],
        save_to_db=True
    )

    # Display results
    print(f"\n{'='*80}")
    print(f"Generated {len(results)} posts successfully!")
    print(f"{'='*80}\n")

    for i, post in enumerate(results, 1):
        print(f"Post {i}:")
        print(f"  - ID: {post.get('post_id')}")
        print(f"  - Trend: {post.get('trend_title', 'Unknown')[:60]}...")
        print(f"  - Category: {post.get('trend_category', 'unknown').upper()}")
        print(f"  - Length: {len(post.get('content', ''))} chars")
        print(f"  - Hashtags: {', '.join(post.get('hashtags', []))}")
        print()

    print("\nYou can now review these posts using:")
    print("  python -m src.review_cli")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
