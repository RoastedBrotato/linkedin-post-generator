"""
Interactive CLI for publishing approved posts to LinkedIn.

Allows users to review approved posts and publish them to LinkedIn.
"""

import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from src.database import Database
from src.linkedin_api import LinkedInAPI
from src.logger import logger
from config.settings import get_settings

console = Console()
settings = get_settings()


class PublishCLI:
    """Interactive CLI for publishing posts to LinkedIn"""

    def __init__(self, db: Optional[Database] = None, api: Optional[LinkedInAPI] = None):
        """
        Initialize publish CLI.

        Args:
            db: Database instance (creates new if not provided)
            api: LinkedInAPI instance (creates new if not provided)
        """
        self.db = db or Database()
        self.api = api or LinkedInAPI(db=self.db)

    def run(self):
        """Main publishing loop"""
        console.print(Panel.fit(
            "[bold cyan]LinkedIn Post Publisher[/bold cyan]\n"
            "Publish approved posts to LinkedIn",
            border_style="cyan"
        ))

        # Validate API setup
        if not self._validate_api_setup():
            return

        while True:
            try:
                self._show_menu()
                choice = Prompt.ask(
                    "\n[cyan]Choose an option[/cyan]",
                    choices=["1", "2", "3", "4", "q"],
                    default="1"
                )

                if choice == "q":
                    console.print("\n[yellow]Goodbye![/yellow]\n")
                    break
                elif choice == "1":
                    self._publish_next_post()
                elif choice == "2":
                    self._list_approved_posts()
                elif choice == "3":
                    self._view_published_posts()
                elif choice == "4":
                    self._publish_batch()

            except KeyboardInterrupt:
                console.print("\n\n[yellow]Goodbye![/yellow]\n")
                break
            except Exception as e:
                logger.error(f"Error in publish CLI: {e}")
                console.print(f"\n[red]Error: {e}[/red]\n")

    def _show_menu(self):
        """Display main menu"""
        console.print("\n" + "=" * 80)
        console.print("[bold]Main Menu[/bold]")
        console.print("  [cyan]1.[/cyan] Publish next approved post")
        console.print("  [cyan]2.[/cyan] List approved posts")
        console.print("  [cyan]3.[/cyan] View published posts")
        console.print("  [cyan]4.[/cyan] Publish multiple posts")
        console.print("  [cyan]q.[/cyan] Quit")
        console.print("=" * 80)

    def _validate_api_setup(self) -> bool:
        """
        Validate LinkedIn API is properly configured.

        Returns:
            True if valid, False otherwise
        """
        console.print("\n[dim]Validating LinkedIn API setup...[/dim]")

        results = self.api.validate_setup()

        if not results['has_client_id'] or not results['has_client_secret']:
            console.print("\n[red]✗ Missing LinkedIn API credentials![/red]")
            console.print("\nPlease add credentials to .env file:")
            console.print("  LINKEDIN_CLIENT_ID=your_client_id")
            console.print("  LINKEDIN_CLIENT_SECRET=your_client_secret")
            console.print("\nSee LINKEDIN_SETUP.md for instructions.\n")
            return False

        if not results['has_access_token'] or not results['token_valid']:
            console.print("\n[red]✗ No valid access token![/red]")
            console.print("\nPlease authenticate first:")
            console.print("  python scripts/linkedin_oauth.py\n")
            return False

        if not results['user_urn_available']:
            console.print("\n[yellow]⚠ User URN not available, fetching...[/yellow]")
            user_info = self.api.get_user_info()
            if not user_info:
                console.print("[red]✗ Failed to get user information[/red]\n")
                return False

        console.print("[green]✓ LinkedIn API ready[/green]")
        return True

    def _publish_next_post(self):
        """Publish the next approved post"""
        approved_posts = self.db.get_posts(status="approved", limit=1)

        if not approved_posts:
            console.print("\n[yellow]No approved posts available to publish.[/yellow]")
            console.print("\nGenerate and approve posts first:")
            console.print("  1. Generate: python scripts/generate_sample_posts.py")
            console.print("  2. Review: python -m src.review_cli\n")
            return

        post = approved_posts[0]
        self._display_post_for_publishing(post)

        # Confirm publishing
        if not Confirm.ask("\n[cyan]Publish this post to LinkedIn?[/cyan]"):
            console.print("\n[yellow]Publishing cancelled[/yellow]\n")
            return

        # Publish
        self._publish_post(post)

    def _publish_post(self, post: Dict[str, Any]):
        """
        Publish a single post to LinkedIn.

        Args:
            post: Post dictionary from database
        """
        post_id = post.get("id")
        content = post.get("content", "")

        console.print(f"\n[dim]Publishing post {post_id} to LinkedIn...[/dim]")

        try:
            result = self.api.publish_post(
                text=content,
                post_id=post_id,
                visibility="PUBLIC"
            )

            if result:
                console.print(f"\n[green]✓ Successfully published post {post_id}![/green]")
                console.print(f"  LinkedIn Post ID: {result['linkedin_post_id']}")
                if result.get('post_url'):
                    console.print(f"  Post URL: {result['post_url']}")
                console.print(f"  Published at: {result['published_at']}\n")

                logger.info(f"Successfully published post {post_id} to LinkedIn")
            else:
                console.print(f"\n[red]✗ Failed to publish post {post_id}[/red]")
                console.print("Check logs for details.\n")
                logger.error(f"Failed to publish post {post_id}")

        except Exception as e:
            console.print(f"\n[red]✗ Error publishing post: {e}[/red]\n")
            logger.error(f"Error publishing post {post_id}: {e}")

    def _display_post_for_publishing(self, post: Dict[str, Any]):
        """Display a post before publishing"""
        post_id = post.get("id")
        content = post.get("content", "No content")
        status = post.get("status", "unknown")
        created_at = post.get("generated_at", "Unknown")

        # Get associated trend
        trend = self.db.get_trend(post.get("trend_id")) if post.get("trend_id") else None

        # Create info panel
        info = f"[bold]Post ID:[/bold] {post_id}\n"
        info += f"[bold]Status:[/bold] {status}\n"
        info += f"[bold]Created:[/bold] {created_at}\n"

        if trend:
            info += f"[bold]Trend:[/bold] {trend.get('title', 'Unknown')[:60]}...\n"

        console.print(Panel(info, title="[bold]Post Info[/bold]", border_style="blue"))

        # Display content
        console.print(Panel(
            content,
            title="[bold green]Post Content (will be published)[/bold green]",
            border_style="green"
        ))

        # Word count
        word_count = len(content.split())
        char_count = len(content)
        console.print(f"\n[dim]Words: {word_count} | Characters: {char_count}[/dim]")

    def _list_approved_posts(self):
        """List all approved posts"""
        approved_posts = self.db.get_posts(status="approved", limit=100)

        if not approved_posts:
            console.print("\n[yellow]No approved posts found.[/yellow]\n")
            return

        table = Table(
            title=f"Approved Posts ({len(approved_posts)})",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )

        table.add_column("ID", width=5, justify="right")
        table.add_column("Preview", width=50)
        table.add_column("Trend", width=30)
        table.add_column("Created", width=10)

        for post in approved_posts:
            post_id = str(post.get("id", ""))
            content = post.get("content", "")
            preview = content[:50] + "..." if len(content) > 50 else content

            # Get trend title
            trend_title = ""
            if post.get("trend_id"):
                trend = self.db.get_trend(post.get("trend_id"))
                if trend:
                    trend_title = trend.get("title", "")[:30]

            created = post.get("generated_at", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created)
                    created = dt.strftime("%Y-%m-%d")
                except:
                    pass

            table.add_row(post_id, preview, trend_title, created)

        console.print("\n")
        console.print(table)
        console.print("\n")

    def _view_published_posts(self):
        """View already published posts"""
        published_posts = self.db.get_posts(status="published", limit=100)

        if not published_posts:
            console.print("\n[yellow]No published posts found.[/yellow]\n")
            return

        table = Table(
            title=f"Published Posts ({len(published_posts)})",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold green"
        )

        table.add_column("ID", width=5, justify="right")
        table.add_column("Preview", width=40)
        table.add_column("Published", width=15)
        table.add_column("LinkedIn ID", width=20)

        for post in published_posts:
            post_id = str(post.get("id", ""))
            content = post.get("content", "")
            preview = content[:40] + "..." if len(content) > 40 else content

            published_at = post.get("published_at", "")
            if published_at:
                try:
                    dt = datetime.fromisoformat(published_at)
                    published_at = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass

            # Get LinkedIn post ID from publishing history
            history = self.db.get_publishing_history(post_id)
            linkedin_id = ""
            if history:
                linkedin_id = history[0].get("platform_post_id", "")[:20]

            table.add_row(post_id, preview, published_at, linkedin_id)

        console.print("\n")
        console.print(table)
        console.print("\n")

    def _publish_batch(self):
        """Publish multiple posts in batch"""
        approved_posts = self.db.get_posts(status="approved", limit=100)

        if not approved_posts:
            console.print("\n[yellow]No approved posts available to publish.[/yellow]\n")
            return

        console.print(f"\n[bold]Batch Publishing[/bold]")
        console.print(f"Found {len(approved_posts)} approved post(s)")

        count = Prompt.ask(
            "\n[cyan]How many posts to publish?[/cyan]",
            default="1"
        )

        try:
            count = int(count)
            count = min(count, len(approved_posts))
        except ValueError:
            console.print("\n[red]Invalid number[/red]\n")
            return

        if count <= 0:
            console.print("\n[yellow]Cancelled[/yellow]\n")
            return

        # Confirm
        if not Confirm.ask(f"\n[cyan]Publish {count} post(s) to LinkedIn?[/cyan]"):
            console.print("\n[yellow]Cancelled[/yellow]\n")
            return

        # Publish posts
        console.print(f"\n[bold]Publishing {count} post(s)...[/bold]\n")

        success_count = 0
        fail_count = 0

        for i, post in enumerate(approved_posts[:count], 1):
            console.print(f"[dim]Post {i}/{count}...[/dim]")

            result = self.api.publish_post(
                text=post.get("content", ""),
                post_id=post.get("id"),
                visibility="PUBLIC"
            )

            if result:
                console.print(f"  [green]✓ Post {post.get('id')} published[/green]")
                success_count += 1
            else:
                console.print(f"  [red]✗ Post {post.get('id')} failed[/red]")
                fail_count += 1

            # Add delay between posts
            if i < count:
                import time
                time.sleep(2)  # 2 second delay between posts

        # Summary
        console.print(f"\n[bold]Batch Publishing Complete[/bold]")
        console.print(f"  [green]✓ Success: {success_count}[/green]")
        if fail_count > 0:
            console.print(f"  [red]✗ Failed: {fail_count}[/red]")
        console.print()


def main():
    """CLI entry point"""
    db = Database()
    api = LinkedInAPI(db)
    cli = PublishCLI(db, api)
    cli.run()


if __name__ == "__main__":
    main()
