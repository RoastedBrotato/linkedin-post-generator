"""
LinkedIn engagement helper for scraping trending posts and posting comments.

Uses Playwright with a logged-in session stored in data/linkedin_cookies.json.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from config.settings import get_settings
from src.llm import LLMClient
from src.logger import logger

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except Exception:  # pragma: no cover - runtime dependency
    sync_playwright = None
    PlaywrightTimeout = Exception


@dataclass
class EngagementTargetPayload:
    post_url: str
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    post_text: Optional[str] = None
    source: Optional[str] = None


class LinkedInEngagementClient:
    """Scrape LinkedIn content and post comments via a logged-in session."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.settings = get_settings().engagement
        self.llm = llm or LLMClient()

    def _ensure_playwright(self) -> None:
        if sync_playwright is None:
            raise RuntimeError("Playwright is not installed. Install 'playwright' and run 'playwright install'.")

    def _ensure_cookies(self) -> Path:
        cookies_path = Path(self.settings.cookies_path)
        if not cookies_path.exists():
            raise RuntimeError(
                f"LinkedIn cookies not found at {cookies_path}. "
                "Run scripts/linkedin_login.py to create a session."
            )
        return cookies_path

    def _extract_post_urls(self, html: str) -> List[str]:
        urls = set()
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select("a[href*='/feed/update/']"):
            href = link.get("href") or ""
            if href.startswith("/"):
                href = f"https://www.linkedin.com{href}"
            if "/feed/update/" in href:
                urls.add(href.split("?")[0])

        # Fallback: extract activity URNs from HTML
        for match in re.findall(r"urn:li:activity:\\d+", html):
            urls.add(f"https://www.linkedin.com/feed/update/{match}")

        return list(urls)

    def _extract_post_details(self, html: str, url: str) -> EngagementTargetPayload:
        soup = BeautifulSoup(html, "html.parser")
        selectors = [
            "div.feed-shared-update-v2__description",
            "div.update-components-text",
            "span.update-components-text",
            "div.feed-shared-text",
        ]
        text = None
        for selector in selectors:
            node = soup.select_one(selector)
            if node and node.get_text(strip=True):
                text = node.get_text(" ", strip=True)
                break

        author = None
        author_url = None
        author_selectors = [
            "span.update-components-actor__name",
            "span.feed-shared-actor__name",
            "span.feed-shared-actor__title",
        ]
        for selector in author_selectors:
            node = soup.select_one(selector)
            if node and node.get_text(strip=True):
                author = node.get_text(" ", strip=True)
                break

        author_link = soup.select_one("a[href*='/in/'], a[href*='/company/']")
        if author_link:
            author_url = author_link.get("href")
            if author_url and author_url.startswith("/"):
                author_url = f"https://www.linkedin.com{author_url}"

        return EngagementTargetPayload(
            post_url=url,
            author_name=author,
            author_url=author_url,
            post_text=text,
        )

    def _collect_from_search(self, page, keyword: str, limit: int) -> List[str]:
        search_url = (
            "https://www.linkedin.com/search/results/content/"
            f"?keywords={quote_plus(keyword)}&sortBy=RELEVANCE"
        )
        logger.info(f"Scraping LinkedIn search for keyword: {keyword}")
        page.goto(search_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        html = page.content()
        urls = self._extract_post_urls(html)
        return urls[:limit]

    def _collect_from_influencer(self, page, profile: str, limit: int) -> List[str]:
        if profile.startswith("http"):
            profile_url = profile.rstrip("/")
        else:
            profile_url = f"https://www.linkedin.com/in/{profile.strip('/')}"

        activity_url = f"{profile_url}/recent-activity/shares/"
        logger.info(f"Scraping LinkedIn activity for profile: {profile_url}")
        page.goto(activity_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        html = page.content()
        urls = self._extract_post_urls(html)
        return urls[:limit]

    def fetch_targets(self, keywords: List[str], influencers: List[str], limit: int) -> List[EngagementTargetPayload]:
        self._ensure_playwright()
        cookies_path = self._ensure_cookies()

        targets: Dict[str, EngagementTargetPayload] = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.settings.headless)
            context = browser.new_context(storage_state=str(cookies_path))
            page = context.new_page()

            # Search keywords
            for keyword in keywords:
                for url in self._collect_from_search(page, keyword, limit=limit * 2):
                    if url not in targets:
                        targets[url] = EngagementTargetPayload(post_url=url, source="search")
                    if len(targets) >= limit:
                        break
                if len(targets) >= limit:
                    break

            # Influencer posts
            if len(targets) < limit:
                for profile in influencers:
                    for url in self._collect_from_influencer(page, profile, limit=limit * 2):
                        if url not in targets:
                            targets[url] = EngagementTargetPayload(post_url=url, source="influencer")
                        if len(targets) >= limit:
                            break
                    if len(targets) >= limit:
                        break

            # Hydrate post details
            hydrated: List[EngagementTargetPayload] = []
            for url, payload in list(targets.items())[:limit]:
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                    details = self._extract_post_details(page.content(), url)
                    details.source = payload.source
                    hydrated.append(details)
                except PlaywrightTimeout:
                    logger.warning(f"Timeout fetching LinkedIn post: {url}")

            context.close()
            browser.close()

        return hydrated

    def generate_comment(self, post_text: str) -> Optional[str]:
        if not post_text:
            return None
        return self.llm.generate_comment(post_text, max_chars=self.settings.comment_max_chars)

    def post_comment(self, post_url: str, comment_text: str) -> Optional[str]:
        """Post a comment on LinkedIn. Returns a comment identifier if available."""
        self._ensure_playwright()
        cookies_path = self._ensure_cookies()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.settings.headless)
            context = browser.new_context(storage_state=str(cookies_path))
            page = context.new_page()
            page.goto(post_url, wait_until="domcontentloaded")

            # Try multiple selectors for the comment button/editor
            comment_button_selectors = [
                "button[aria-label*='Comment']",
                "button[data-control-name='comment']",
                "button.feed-shared-social-action--comment",
            ]
            clicked = False
            for selector in comment_button_selectors:
                try:
                    page.click(selector, timeout=3000)
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                raise RuntimeError("Could not find comment button on LinkedIn post")

            editor_selectors = [
                "div.comments-comment-box__editor",
                "div.ql-editor",
                "div[contenteditable='true']",
            ]
            editor = None
            for selector in editor_selectors:
                try:
                    editor = page.wait_for_selector(selector, timeout=4000)
                    if editor:
                        break
                except Exception:
                    continue

            if not editor:
                raise RuntimeError("Could not find comment editor on LinkedIn post")

            editor.click()
            editor.fill(comment_text)

            submit_selectors = [
                "button.comments-comment-box__submit-button",
                "button[aria-label='Post comment']",
                "button[aria-label='Comment']",
            ]
            posted = False
            for selector in submit_selectors:
                try:
                    page.click(selector, timeout=3000)
                    posted = True
                    break
                except Exception:
                    continue

            if not posted:
                raise RuntimeError("Could not submit LinkedIn comment")

            page.wait_for_timeout(1500)
            context.close()
            browser.close()

        return None
