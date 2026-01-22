#!/usr/bin/env python3
"""
Quick test script to fetch and display real trends from all sources.

Usage: python test_fetch_trends.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.trends import TrendFetcher
from src.database import Database
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

def main():
    """Fetch and display trends"""
    console = Console()

    console.print(Panel.fit(
        "[bold cyan]LinkedIn Post Generator - Trend Fetcher Test[/bold cyan]\n"
        "Fetching trends from Hacker News, RSS, Reddit, and GitHub...",
        border_style="cyan"
    ))

    # Initialize database (optional, set to None to skip storage)
    db = Database()

    # Initialize trend fetcher
    console.print("\n[yellow]Initializing trend sources...[/yellow]")
    fetcher = TrendFetcher(db=db)

    # Fetch trends (don't save to DB for testing)
    console.print("\n[yellow]Fetching trends from all sources...[/yellow]")
    console.print("[dim]This may take 30-60 seconds...[/dim]\n")

    trends = fetcher.fetch_all_trends(save_to_db=False)

    if not trends:
        console.print("[red]No trends found! Check your internet connection.[/red]")
        return

    # Display summary
    console.print(f"\n[green]✓ Found {len(trends)} relevant trends[/green]\n")

    # Count by category
    ai_count = len([t for t in trends if t.get('category') == 'ai'])
    tech_count = len([t for t in trends if t.get('category') == 'tech'])

    console.print(f"[cyan]AI trends:[/cyan] {ai_count}")
    console.print(f"[cyan]Tech trends:[/cyan] {tech_count}\n")

    # Display top 20 trends in a table
    table = Table(
        title="Top 20 Trends by Relevance Score",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("#", style="dim", width=3)
    table.add_column("Category", width=8)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Title", width=60)
    table.add_column("Source", width=20)

    for i, trend in enumerate(trends[:20], 1):
        category = trend.get('category', 'unknown')
        score = trend.get('relevance_score', 0)
        title = trend.get('title', 'No title')

        # Truncate long titles
        if len(title) > 60:
            title = title[:57] + "..."

        # Get source name
        metadata = trend.get('metadata', {})
        source = (
            metadata.get('feed_name') or
            metadata.get('subreddit') or
            metadata.get('repo_name') or
            'Hacker News'
        )

        # Truncate source name
        if len(source) > 20:
            source = source[:17] + "..."

        # Color code by category
        if category == 'ai':
            category_display = f"[green]{category.upper()}[/green]"
        else:
            category_display = f"[blue]{category.upper()}[/blue]"

        # Color code score
        if score >= 0.7:
            score_display = f"[green]{score:.2f}[/green]"
        elif score >= 0.5:
            score_display = f"[yellow]{score:.2f}[/yellow]"
        else:
            score_display = f"[dim]{score:.2f}[/dim]"

        table.add_row(
            str(i),
            category_display,
            score_display,
            title,
            source
        )

    console.print(table)

    # Ask user if they want to see details
    console.print("\n[cyan]Would you like to see details of a specific trend?[/cyan]")
    console.print("[dim]Enter a number (1-20), or press Enter to skip:[/dim]")

    try:
        choice = input("> ").strip()
        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < min(20, len(trends)):
                show_trend_details(console, trends[idx])
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Skipped[/dim]")

    console.print("\n[green]✓ Test complete![/green]")


def show_trend_details(console: Console, trend: dict):
    """Display detailed information about a trend"""
    console.print("\n" + "="*80)
    console.print(Panel(
        f"[bold]{trend.get('title', 'No title')}[/bold]",
        border_style="cyan"
    ))

    console.print(f"\n[cyan]Category:[/cyan] {trend.get('category', 'unknown').upper()}")
    console.print(f"[cyan]Relevance Score:[/cyan] {trend.get('relevance_score', 0):.3f}")
    console.print(f"[cyan]URL:[/cyan] {trend.get('url', 'N/A')}")

    # Source info
    metadata = trend.get('metadata', {})
    source = (
        metadata.get('feed_name') or
        f"r/{metadata.get('subreddit')}" if metadata.get('subreddit') else
        metadata.get('repo_name') or
        'Hacker News'
    )
    console.print(f"[cyan]Source:[/cyan] {source}")

    # Engagement metrics
    score = trend.get('score', 0)
    if score > 0:
        if 'subreddit' in metadata:
            console.print(f"[cyan]Reddit Score:[/cyan] {score} upvotes")
        elif 'stars_today' in metadata:
            console.print(f"[cyan]GitHub Stars Today:[/cyan] {score}")
        else:
            console.print(f"[cyan]HN Score:[/cyan] {score} points")

    # Description
    description = trend.get('description', 'No description')
    if len(description) > 500:
        description = description[:497] + "..."

    console.print(f"\n[cyan]Description:[/cyan]")
    console.print(Panel(description, border_style="dim"))

    console.print("\n" + "="*80)


if __name__ == "__main__":
    main()
