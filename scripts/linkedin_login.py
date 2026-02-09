"""
Interactive login helper to save LinkedIn session cookies for Playwright scraping.

Usage:
  python scripts/linkedin_login.py
"""

from pathlib import Path
import sys

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:  # pragma: no cover
    raise SystemExit("Playwright not installed. Run: pip install playwright && playwright install") from exc


def main() -> None:
    settings = get_settings().engagement
    cookies_path = Path(settings.cookies_path)
    cookies_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        print("Log in to LinkedIn in the opened browser window.")
        input("Press Enter here after you are fully logged in...")

        context.storage_state(path=str(cookies_path))
        context.close()
        browser.close()

    print(f"Saved LinkedIn session to {cookies_path}")


if __name__ == "__main__":
    main()
