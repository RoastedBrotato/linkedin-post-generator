#!/usr/bin/env python3
"""Show sample trends from different sources"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.trends import TrendFetcher
from src.database import Database
from rich.console import Console
from rich.panel import Panel

console = Console()

def main():
    console.print("\n[cyan]Fetching trends...[/cyan]")

    db = Database()
    fetcher = TrendFetcher(db=db)
    trends = fetcher.fetch_all_trends(save_to_db=False)

    # Get a mix of trends from different sources
    hn_trends = [t for t in trends if 'descendants' in t.get('metadata', {})]
    rss_trends = [t for t in trends if 'feed_name' in t.get('metadata', {})]
    github_trends = [t for t in trends if 'repo_name' in t.get('metadata', {})]

    console.print(f"\n[green]✓ Found {len(trends)} total trends[/green]")
    console.print(f"  - Hacker News: {len(hn_trends)}")
    console.print(f"  - RSS Feeds: {len(rss_trends)}")
    console.print(f"  - GitHub: {len(github_trends)}\n")

    # Show sample from each source
    console.print("[bold cyan]Sample Hacker News Trend:[/bold cyan]")
    if hn_trends:
        show_trend(hn_trends[0])

    console.print("\n[bold cyan]Sample RSS Feed Trend:[/bold cyan]")
    if rss_trends:
        show_trend(rss_trends[0])

    console.print("\n[bold cyan]Sample GitHub Trend:[/bold cyan]")
    if github_trends:
        show_trend(github_trends[0])

def show_trend(trend):
    """Display a trend"""
    metadata = trend.get('metadata', {})

    # Determine source
    if 'descendants' in metadata:
        source = "Hacker News"
        engagement = f"{trend.get('score', 0)} points, {metadata.get('descendants', 0)} comments"
    elif 'feed_name' in metadata:
        source = metadata.get('feed_name')
        engagement = f"Published {trend.get('published_at', 'recently')}"
    elif 'repo_name' in metadata:
        source = f"GitHub: {metadata.get('repo_name')}"
        engagement = f"{metadata.get('stars_today', 0)} stars today, {metadata.get('total_stars', 0)} total"
    else:
        source = "Unknown"
        engagement = ""

    console.print(Panel(
        f"[bold]{trend.get('title', 'No title')}[/bold]\n\n"
        f"[dim]{trend.get('description', 'No description')[:300]}...[/dim]\n\n"
        f"[cyan]Source:[/cyan] {source}\n"
        f"[cyan]Category:[/cyan] {trend.get('category', 'unknown').upper()}\n"
        f"[cyan]Relevance:[/cyan] {trend.get('relevance_score', 0):.2f}\n"
        f"[cyan]Engagement:[/cyan] {engagement}\n"
        f"[cyan]URL:[/cyan] {trend.get('url', 'N/A')[:80]}",
        border_style="blue"
    ))

if __name__ == "__main__":
    main()
