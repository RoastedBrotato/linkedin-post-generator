#!/usr/bin/env python3
"""
Interactive Reddit API setup and testing script.

This script will:
1. Help you set up Reddit API credentials
2. Test the connection
3. Update your .env file
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import praw
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from dotenv import load_dotenv, set_key
import os

console = Console()

def main():
    """Main setup flow"""
    console.print(Panel.fit(
        "[bold cyan]Reddit API Setup Assistant[/bold cyan]\n"
        "This will help you configure Reddit API access",
        border_style="cyan"
    ))

    # Load current .env
    load_dotenv()

    console.print("\n[yellow]Step 1: Create a Reddit App[/yellow]")
    console.print("1. Go to: [link]https://www.reddit.com/prefs/apps[/link]")
    console.print("2. Click 'create another app...' at the bottom")
    console.print("3. Choose type: [bold]script[/bold] (important!)")
    console.print("4. Fill in any name and redirect URI (http://localhost:8080)\n")

    if not Confirm.ask("Have you created a Reddit app?"):
        console.print("\n[yellow]Please create the app first, then run this script again.[/yellow]")
        console.print("See REDDIT_SETUP.md for detailed instructions.\n")
        return

    console.print("\n[yellow]Step 2: Enter Your Credentials[/yellow]")

    # Get credentials
    client_id = Prompt.ask(
        "\nEnter your [cyan]client_id[/cyan] (found under 'personal use script')",
        default=os.getenv("TRENDS_REDDIT_CLIENT_ID", "")
    )

    client_secret = Prompt.ask(
        "Enter your [cyan]client_secret[/cyan]",
        default=os.getenv("TRENDS_REDDIT_CLIENT_SECRET", ""),
        password=True
    )

    username = Prompt.ask(
        "Enter your [cyan]Reddit username[/cyan]",
        default="your_username"
    )

    user_agent = f"linkedin-post-generator/1.0 by /u/{username}"

    console.print("\n[yellow]Step 3: Testing Connection[/yellow]")

    # Test the credentials
    try:
        with console.status("[bold green]Testing Reddit API connection..."):
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )

            # Try to fetch a subreddit to test
            subreddit = reddit.subreddit("python")
            _ = list(subreddit.hot(limit=1))

        console.print("[green]✓ Successfully connected to Reddit API![/green]")

        # Show some test data
        console.print("\n[cyan]Fetching sample data from r/MachineLearning...[/cyan]")

        ml_sub = reddit.subreddit("MachineLearning")
        posts = list(ml_sub.hot(limit=5))

        if posts:
            table = Table(title="Sample Posts from r/MachineLearning")
            table.add_column("Score", justify="right", width=6)
            table.add_column("Title", width=60)

            for post in posts:
                title = post.title
                if len(title) > 60:
                    title = title[:57] + "..."
                table.add_row(str(post.score), title)

            console.print(table)

    except Exception as e:
        console.print(f"\n[red]✗ Failed to connect: {e}[/red]")
        console.print("\n[yellow]Common issues:[/yellow]")
        console.print("- Make sure you selected 'script' as the app type")
        console.print("- Check that client_id and client_secret are correct")
        console.print("- Ensure there are no extra spaces\n")
        return

    # Ask to save
    console.print("\n[yellow]Step 4: Save Configuration[/yellow]")

    if Confirm.ask("Save these credentials to .env file?", default=True):
        env_file = Path(__file__).parent / ".env"

        set_key(env_file, "TRENDS_REDDIT_CLIENT_ID", client_id)
        set_key(env_file, "TRENDS_REDDIT_CLIENT_SECRET", client_secret)
        set_key(env_file, "TRENDS_REDDIT_USER_AGENT", user_agent)
        set_key(env_file, "TRENDS_REDDIT_ENABLED", "true")

        console.print(f"\n[green]✓ Configuration saved to {env_file}[/green]")
        console.print("\n[cyan]You can now run:[/cyan]")
        console.print("  python test_fetch_trends.py")
        console.print("\nReddit trends will now be included in the results!\n")
    else:
        console.print("\n[yellow]Configuration not saved.[/yellow]")
        console.print("To manually update .env, add these lines:")
        console.print(f"\nTRENDS_REDDIT_CLIENT_ID={client_id}")
        console.print(f"TRENDS_REDDIT_CLIENT_SECRET={client_secret}")
        console.print(f"TRENDS_REDDIT_USER_AGENT={user_agent}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled.[/yellow]\n")
        sys.exit(0)
