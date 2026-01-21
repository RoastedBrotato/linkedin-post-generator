#!/usr/bin/env python3
"""
Test LinkedIn post generation from real trends.

This script fetches real trends and generates LinkedIn posts using the LLM.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.trends import TrendFetcher
from src.database import Database
from src.llm import LLMClient
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

def main():
    console.print(Panel.fit(
        "[bold cyan]LinkedIn Post Generator - LLM Test[/bold cyan]\n"
        "Fetching trends and generating LinkedIn posts",
        border_style="cyan"
    ))

    # Initialize components
    console.print("\n[yellow]1. Initializing LLM client...[/yellow]")
    llm = LLMClient()

    # Health check
    console.print("[yellow]2. Checking LLM health...[/yellow]")
    if not llm.health_check():
        console.print("[red]✗ LLM health check failed. Is Ollama running?[/red]")
        console.print("[dim]Try: ollama serve[/dim]\n")
        return

    console.print("[green]✓ LLM is healthy[/green]")

    # Fetch trends
    console.print("\n[yellow]3. Fetching trends...[/yellow]")
    db = Database()
    fetcher = TrendFetcher(db=db)
    trends = fetcher.fetch_all_trends(save_to_db=False)

    if not trends:
        console.print("[red]✗ No trends found[/red]\n")
        return

    console.print(f"[green]✓ Found {len(trends)} trends[/green]")

    # Select a high-quality trend
    top_trend = trends[0]  # Highest relevance score
    console.print(f"\n[cyan]Selected trend:[/cyan] {top_trend.get('title', 'Unknown')[:80]}...")

    # Generate post
    console.print("\n[yellow]4. Generating LinkedIn post...[/yellow]")
    console.print("[dim]This may take 30-60 seconds with local LLM...[/dim]\n")

    result = llm.generate_post(top_trend)

    if not result:
        console.print("[red]✗ Failed to generate post[/red]\n")
        return

    # Display result
    console.print("[green]✓ Post generated successfully![/green]\n")

    display_post(result, top_trend)

    # Offer to generate more
    console.print("\n[cyan]Would you like to generate another post?[/cyan]")
    console.print("[dim]Enter a number (1-10) to select a trend, or press Enter to exit:[/dim]")

    try:
        choice = input("> ").strip()
        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < min(10, len(trends)):
                trend = trends[idx]
                console.print(f"\n[yellow]Generating post for:[/yellow] {trend.get('title', 'Unknown')[:80]}...\n")
                result = llm.generate_post(trend)
                if result:
                    display_post(result, trend)
    except (KeyboardInterrupt, EOFError):
        pass

    console.print("\n[green]✓ Test complete![/green]\n")


def display_post(result: dict, trend: dict):
    """Display the generated post"""
    console.print("="*80)

    # Post content
    console.print(Panel(
        result['content'],
        title="[bold]Generated LinkedIn Post[/bold]",
        border_style="green"
    ))

    # Metadata
    console.print(f"\n[cyan]Hashtags:[/cyan] {' '.join(result.get('hashtags', []))}")
    console.print(f"[cyan]Source:[/cyan] {result.get('source_url', 'N/A')}")
    console.print(f"[cyan]Confidence:[/cyan] {result.get('confidence', 'Unknown')}")
    console.print(f"[cyan]Word Count:[/cyan] {len(result['content'].split())} words")
    console.print(f"[cyan]Character Count:[/cyan] {len(result['content'])} chars")

    # Original trend info
    console.print(f"\n[dim]Original Trend:[/dim] {trend.get('title', 'Unknown')}")
    console.print(f"[dim]Category:[/dim] {trend.get('category', 'unknown').upper()}")
    console.print(f"[dim]Relevance:[/dim] {trend.get('relevance_score', 0):.2f}")

    console.print("="*80)


if __name__ == "__main__":
    main()
