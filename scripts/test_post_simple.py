#!/usr/bin/env python3
"""
Simple LinkedIn posting test - bypasses settings caching issues.

Usage:
    python scripts/test_post_simple.py         # Interactive (asks for confirmation)
    python scripts/test_post_simple.py --yes   # Auto-confirm (no prompt)
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

# Now import after env is loaded
sys.path.insert(0, str(ROOT))

from src.logger import logger
import requests
import time

def test_post_to_linkedin():
    """Test posting to LinkedIn with a simple test post"""

    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    user_urn = os.getenv("LINKEDIN_USER_URN")

    if not access_token:
        print("❌ No access token found in .env")
        return False

    if not user_urn:
        print("❌ No user URN found in .env")
        return False

    print("="*60)
    print("LinkedIn Posting Test")
    print("="*60)
    print(f"✓ Access Token: {access_token[:50]}...")
    print(f"✓ User URN: {user_urn}")
    print()

    # Test post content
    test_content = """🚀 Testing LinkedIn API Integration

This is a test post from my automated LinkedIn Post Generator!

The system can now:
✅ Fetch AI/tech trends from multiple sources
✅ Generate professional posts with LLM
✅ Review and approve posts interactively
✅ Publish directly to LinkedIn via API

#AI #Automation #SoftwareDevelopment #Testing"""

    print("Test post content:")
    print("-" * 60)
    print(test_content)
    print("-" * 60)
    print()

    # Prepare the post payload
    post_data = {
        "author": user_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": test_content
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    url = "https://api.linkedin.com/v2/ugcPosts"

    print(f"Posting to LinkedIn...")
    print()

    # Check for --yes flag
    auto_confirm = "--yes" in sys.argv or "-y" in sys.argv

    if not auto_confirm:
        try:
            confirm = input("Do you want to publish this TEST POST to LinkedIn? (yes/no): ")
            if confirm.lower() != "yes":
                print("\n❌ Posting cancelled by user")
                return False
        except EOFError:
            print("\n❌ Cannot get user confirmation in non-interactive mode")
            print("   Use --yes flag to auto-confirm: python scripts/test_post_simple.py --yes")
            return False
    else:
        print("Auto-confirming (--yes flag detected)...")

    try:
        response = requests.post(url, json=post_data, headers=headers)

        if response.status_code == 201:
            post_id = response.json().get("id", "")
            print("\n✅ Post published successfully!")
            print(f"   Post ID: {post_id}")
            if post_id:
                # Construct LinkedIn URL
                post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
                print(f"   URL: {post_url}")
            return True
        else:
            print(f"\n❌ Failed to publish post")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_post_to_linkedin()
    sys.exit(0 if success else 1)
