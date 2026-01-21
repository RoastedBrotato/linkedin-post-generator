#!/usr/bin/env python3
"""
Generate a LinkedIn post from a real trend using the local LLM.

Usage:
  python scripts/generate_post_from_trend.py
  python scripts/generate_post_from_trend.py --index 3 --limit 10
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import Database
from src.llm import LLMClient
from src.trends import TrendFetcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a LinkedIn post from a real trend.")
    parser.add_argument(
        "--index",
        type=int,
        default=1,
        help="1-based index of the trend to use after sorting by relevance (default: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max number of trends to consider when selecting by index (default: 10)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Optional minimum relevance score filter (overrides config if set).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional LLM model override (e.g., mistral, llama2).",
    )
    parser.add_argument(
        "--save-to-db",
        action="store_true",
        help="Save fetched trends to the database.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("Fetching real trends...")
    db = Database()
    fetcher = TrendFetcher(db=db if args.save_to_db else None)
    trends = fetcher.fetch_all_trends(save_to_db=args.save_to_db)

    if args.min_score is not None:
        trends = [t for t in trends if t.get("relevance_score", 0) >= args.min_score]

    if not trends:
        print("No trends found. Try again later or adjust filters.")
        return 1

    trends = trends[: max(1, args.limit)]
    if args.index < 1 or args.index > len(trends):
        print(f"Index {args.index} is out of range for {len(trends)} trends.")
        for i, trend in enumerate(trends, start=1):
            title = trend.get("title", "Unknown")
            score = trend.get("relevance_score", 0)
            print(f"{i}. {title[:80]} (score={score:.2f})")
        return 1

    trend = trends[args.index - 1]
    print(f"Selected trend: {trend.get('title', 'Unknown')}")

    llm = LLMClient(model=args.model)
    if not llm.health_check():
        print("LLM health check failed. Start Ollama with: ollama serve")
        return 1

    print("Generating post... this can take a minute.")
    result = llm.generate_post(trend)

    if not result:
        print("Failed to generate a post.")
        return 1

    print("\n--- Generated LinkedIn Post ---\n")
    print(result["content"])
    print("\n--- Metadata ---")
    print(f"Hashtags: {' '.join(result.get('hashtags', []))}")
    print(f"Source: {result.get('source_url', 'N/A')}")
    print(f"Confidence: {result.get('confidence', 'Unknown')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
