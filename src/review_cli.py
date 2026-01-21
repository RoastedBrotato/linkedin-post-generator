"""
Interactive CLI for reviewing and approving LinkedIn posts.

Allows human review of AI-generated posts before publishing.
"""

import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich import box

from src.database import Database
from src.logger import logger
from config.settings import get_settings

console = Console()
settings = get_settings()


class ReviewCLI:
    """Interactive CLI for reviewing posts"""

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize review CLI.

        Args:
            db: Database instance (creates new if not provided)
        """
        self.db = db or Database()
        self.current_filter = "pending"

    def run(self):
        """Main review loop"""
        console.print(Panel.fit(
            "[bold cyan]LinkedIn Post Review CLI[/bold cyan]\n"
            "Review and approve AI-generated posts",
            border_style="cyan"
        ))

        while True:
            try:
                self._show_menu()
                choice = Prompt.ask(
                    "\n[cyan]Choose an option[/cyan]",
                    choices=["1", "2", "3", "4", "5", "q"],
                    default="1"
                )

                if choice == "q":
                    console.print("\n[yellow]Goodbye![/yellow]\n")
                    break
                elif choice == "1":
                    self._review_posts()
                elif choice == "2":
                    self._list_posts()
                elif choice == "3":
                    self._filter_posts()
                elif choice == "4":
                    self._search_posts()
                elif choice == "5":
                    self._show_statistics()

            except KeyboardInterrupt:
                console.print("\n\n[yellow]Goodbye![/yellow]\n")
                break
            except Exception as e:
                logger.error(f"Error in review CLI: {e}")
                console.print(f"\n[red]Error: {e}[/red]\n")

    def _show_menu(self):
        """Display main menu"""
        console.print("\n" + "="*80)
        console.print("[bold]Main Menu[/bold]")
        console.print("  [cyan]1.[/cyan] Review pending posts")
        console.print("  [cyan]2.[/cyan] List all posts")
        console.print("  [cyan]3.[/cyan] Filter by status")
        console.print("  [cyan]4.[/cyan] Search posts")
        console.print("  [cyan]5.[/cyan] Show statistics")
        console.print("  [cyan]q.[/cyan] Quit")
        console.print("="*80)

    def _review_posts(self):
        """Review posts one by one"""
        posts = self.db.get_posts(status=self.current_filter, limit=50)

        if not posts:
            console.print(f"\n[yellow]No {self.current_filter} posts found.[/yellow]\n")
            return

        console.print(f"\n[green]Found {len(posts)} {self.current_filter} post(s)[/green]\n")

        for i, post in enumerate(posts, 1):
            console.print(f"\n[dim]Post {i} of {len(posts)}[/dim]")

            action = self._review_single_post(post)

            if action == "quit":
                break
            elif action == "skip":
                continue

    def _review_single_post(self, post: Dict[str, Any]) -> str:
        """
        Review a single post.

        Args:
            post: Post dictionary

        Returns:
            Action taken ("approved", "rejected", "edited", "skip", "quit")
        """
        # Display post
        self._display_post(post)

        # Show options
        console.print("\n[bold]Actions:[/bold]")
        console.print("  [green]a[/green] - Approve")
        console.print("  [red]r[/red] - Reject")
        console.print("  [yellow]e[/yellow] - Edit")
        console.print("  [cyan]s[/cyan] - Skip")
        console.print("  [dim]q[/dim] - Quit review")

        choice = Prompt.ask(
            "\n[cyan]What would you like to do?[/cyan]",
            choices=["a", "r", "e", "s", "q"],
            default="s"
        )

        if choice == "a":
            return self._approve_post(post)
        elif choice == "r":
            return self._reject_post(post)
        elif choice == "e":
            return self._edit_post(post)
        elif choice == "q":
            return "quit"
        else:
            return "skip"

    def _display_post(self, post: Dict[str, Any]):
        """Display a post with formatting"""
        post_id = post.get("id")
        content = post.get("content", "No content")
        status = post.get("status", "unknown")
        created_at = post.get("generated_at", "Unknown")

        # Get associated trend
        trend = self.db.get_trend(post.get("trend_id")) if post.get("trend_id") else None

        # Get sources
        sources = self.db.get_sources_for_post(post_id)

        # Create info panel
        info = f"[bold]Post ID:[/bold] {post_id}\n"
        info += f"[bold]Status:[/bold] {status}\n"
        info += f"[bold]Created:[/bold] {created_at}\n"

        if trend:
            info += f"[bold]Trend:[/bold] {trend.get('title', 'Unknown')[:60]}...\n"
            info += f"[bold]Category:[/bold] {trend.get('category', 'unknown').upper()}\n"

        console.print(Panel(info, title="[bold]Post Info[/bold]", border_style="blue"))

        # Display content
        console.print(Panel(
            content,
            title="[bold green]Post Content[/bold green]",
            border_style="green"
        ))

        # Display sources
        if sources:
            source_text = "\n".join([
                f"• {s.get('source_name', 'Unknown')}: {s.get('source_url', 'N/A')}"
                for s in sources
            ])
            console.print(Panel(
                source_text,
                title="[bold]Sources[/bold]",
                border_style="yellow"
            ))

        # Word count
        word_count = len(content.split())
        char_count = len(content)
        console.print(f"\n[dim]Words: {word_count} | Characters: {char_count}[/dim]")

    def _approve_post(self, post: Dict[str, Any]) -> str:
        """Approve a post"""
        post_id = post.get("id")

        notes = Prompt.ask(
            "\n[green]Approval notes (optional)[/green]",
            default=""
        )

        if self.db.approve_post(post_id, notes or None):
            console.print(f"\n[green]✓ Post {post_id} approved![/green]")
            logger.info(f"Post {post_id} approved by user")
            return "approved"
        else:
            console.print(f"\n[red]✗ Failed to approve post {post_id}[/red]")
            return "skip"

    def _reject_post(self, post: Dict[str, Any]) -> str:
        """Reject a post"""
        post_id = post.get("id")

        # Confirm rejection
        if not Confirm.ask("\n[red]Are you sure you want to reject this post?[/red]"):
            console.print("\n[yellow]Rejection cancelled[/yellow]")
            return "skip"

        notes = Prompt.ask(
            "\n[red]Rejection reason (optional)[/red]",
            default=""
        )

        if self.db.reject_post(post_id, notes or None):
            console.print(f"\n[red]✓ Post {post_id} rejected[/red]")
            logger.info(f"Post {post_id} rejected by user: {notes}")
            return "rejected"
        else:
            console.print(f"\n[red]✗ Failed to reject post {post_id}[/red]")
            return "skip"

    def _edit_post(self, post: Dict[str, Any]) -> str:
        """Edit a post"""
        post_id = post.get("id")
        current_content = post.get("content", "")

        console.print("\n[yellow]Editing post...[/yellow]")
        console.print("[dim]Enter new content (or press Ctrl+C to cancel):[/dim]\n")

        try:
            # Simple line-by-line editing
            lines = []
            console.print("[dim]Enter text (empty line to finish):[/dim]")
            while True:
                line = input()
                if line == "" and lines:  # Empty line after some content = done
                    break
                lines.append(line)

            new_content = "\n".join(lines).strip()

            if not new_content:
                console.print("\n[yellow]Edit cancelled (no content)[/yellow]")
                return "skip"

            # Confirm edit
            console.print(Panel(new_content, title="[bold]New Content[/bold]", border_style="yellow"))

            if not Confirm.ask("\n[yellow]Save these changes?[/yellow]"):
                console.print("\n[yellow]Edit cancelled[/yellow]")
                return "skip"

            # Update post
            if self.db.update_post(post_id, content=new_content, reviewed_at=datetime.now().isoformat()):
                console.print(f"\n[green]✓ Post {post_id} updated![/green]")
                logger.info(f"Post {post_id} edited by user")
                return "edited"
            else:
                console.print(f"\n[red]✗ Failed to update post {post_id}[/red]")
                return "skip"

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Edit cancelled[/yellow]")
            return "skip"

    def _list_posts(self):
        """List all posts in a table"""
        posts = self.db.get_posts(status=self.current_filter, limit=100)

        if not posts:
            console.print(f"\n[yellow]No {self.current_filter} posts found.[/yellow]\n")
            return

        table = Table(
            title=f"{self.current_filter.title()} Posts ({len(posts)})",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )

        table.add_column("ID", width=5, justify="right")
        table.add_column("Status", width=10)
        table.add_column("Preview", width=50)
        table.add_column("Trend", width=30)
        table.add_column("Created", width=10)

        for post in posts:
            post_id = str(post.get("id", ""))
            status = post.get("status", "unknown")
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

            # Color code status
            if status == "approved":
                status_display = f"[green]{status}[/green]"
            elif status == "rejected":
                status_display = f"[red]{status}[/red]"
            else:
                status_display = f"[yellow]{status}[/yellow]"

            table.add_row(post_id, status_display, preview, trend_title, created)

        console.print("\n")
        console.print(table)
        console.print("\n")

    def _filter_posts(self):
        """Change status filter"""
        console.print("\n[bold]Filter by status:[/bold]")
        console.print("  [yellow]1.[/yellow] Pending")
        console.print("  [green]2.[/green] Approved")
        console.print("  [red]3.[/red] Rejected")
        console.print("  [blue]4.[/blue] Published")
        console.print("  [dim]5.[/dim] All")

        choice = Prompt.ask(
            "\n[cyan]Select filter[/cyan]",
            choices=["1", "2", "3", "4", "5"],
            default="1"
        )

        filters = {
            "1": "pending",
            "2": "approved",
            "3": "rejected",
            "4": "published",
            "5": None
        }

        self.current_filter = filters[choice]
        status_name = self.current_filter or "all"
        console.print(f"\n[green]✓ Filter set to: {status_name}[/green]\n")

    def _search_posts(self):
        """Search posts by keyword"""
        query = Prompt.ask("\n[cyan]Enter search term[/cyan]")

        if not query:
            console.print("\n[yellow]Search cancelled[/yellow]\n")
            return

        # Simple search in content
        all_posts = self.db.get_posts(limit=1000)
        matches = [
            p for p in all_posts
            if query.lower() in p.get("content", "").lower()
        ]

        if not matches:
            console.print(f"\n[yellow]No posts found matching '{query}'[/yellow]\n")
            return

        console.print(f"\n[green]Found {len(matches)} post(s) matching '{query}'[/green]\n")

        # Display matches in table
        table = Table(title=f"Search Results: '{query}'", box=box.ROUNDED)
        table.add_column("ID", width=5)
        table.add_column("Status", width=10)
        table.add_column("Match Preview", width=60)

        for post in matches[:20]:  # Limit to 20 results
            post_id = str(post.get("id", ""))
            status = post.get("status", "unknown")
            content = post.get("content", "")

            # Find and highlight match
            idx = content.lower().find(query.lower())
            if idx != -1:
                start = max(0, idx - 30)
                end = min(len(content), idx + len(query) + 30)
                preview = "..." + content[start:end] + "..."
            else:
                preview = content[:60] + "..."

            table.add_row(post_id, status, preview)

        console.print(table)
        console.print("\n")

    def _show_statistics(self):
        """Display statistics about posts"""
        all_posts = self.db.get_posts(limit=10000)

        if not all_posts:
            console.print("\n[yellow]No posts in database[/yellow]\n")
            return

        # Calculate stats
        total = len(all_posts)
        pending = len([p for p in all_posts if p.get("status") == "pending"])
        approved = len([p for p in all_posts if p.get("status") == "approved"])
        rejected = len([p for p in all_posts if p.get("status") == "rejected"])
        published = len([p for p in all_posts if p.get("status") == "published"])

        # Display stats
        stats_table = Table(title="Post Statistics", box=box.ROUNDED, show_header=False)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Count", justify="right", style="bold")

        stats_table.add_row("Total Posts", str(total))
        stats_table.add_row("Pending Review", f"[yellow]{pending}[/yellow]")
        stats_table.add_row("Approved", f"[green]{approved}[/green]")
        stats_table.add_row("Rejected", f"[red]{rejected}[/red]")
        stats_table.add_row("Published", f"[blue]{published}[/blue]")

        if approved + rejected > 0:
            approval_rate = (approved / (approved + rejected)) * 100
            stats_table.add_row("Approval Rate", f"{approval_rate:.1f}%")

        console.print("\n")
        console.print(stats_table)
        console.print("\n")


def main():
    """CLI entry point"""
    db = Database()
    cli = ReviewCLI(db)
    cli.run()


if __name__ == "__main__":
    main()
