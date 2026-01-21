#!/usr/bin/env python3
"""
Test LinkedIn API setup and credentials.

Validates that authentication is working and displays account information.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.linkedin_api import LinkedInAPI
from src.logger import logger


def test_linkedin_api():
    """Test LinkedIn API setup and connectivity"""
    print("\n" + "=" * 80)
    print("LinkedIn API Setup Test")
    print("=" * 80)

    # Initialize API client
    api = LinkedInAPI()

    # Validate setup
    print("\n📋 Step 1: Validating setup...")
    results = api.validate_setup()

    print(f"  {'✓' if results['has_client_id'] else '✗'} Client ID configured")
    print(f"  {'✓' if results['has_client_secret'] else '✗'} Client Secret configured")
    print(f"  {'✓' if results['has_access_token'] else '✗'} Access Token present")
    print(f"  {'✓' if results['token_valid'] else '✗'} Token valid (not expired)")

    if not results['has_client_id'] or not results['has_client_secret']:
        print("\n✗ Missing LinkedIn API credentials!")
        print("\nPlease add these to your .env file:")
        print("  LINKEDIN_CLIENT_ID=your_client_id_here")
        print("  LINKEDIN_CLIENT_SECRET=your_client_secret_here")
        print("\nSee LINKEDIN_SETUP.md for instructions.")
        return False

    if not results['has_access_token']:
        print("\n✗ No access token found!")
        print("\nYou need to authenticate first:")
        print("  python scripts/linkedin_oauth.py")
        return False

    if not results['token_valid']:
        print("\n⚠ Access token is expired or expiring soon!")
        print("\nTrying to refresh token...")

        if api.refresh_access_token():
            print("✓ Token refreshed successfully")
            results['token_valid'] = True
        else:
            print("\n✗ Token refresh failed. Please re-authenticate:")
            print("  python scripts/linkedin_oauth.py")
            return False

    # Get user information
    print("\n📋 Step 2: Fetching user profile...")
    user_info = api.get_user_info()

    if not user_info:
        print("✗ Failed to get user information")
        print("\nThis could mean:")
        print("  - Your access token is invalid")
        print("  - Required scopes are not approved")
        print("  - LinkedIn API is experiencing issues")
        print("\nTry re-authenticating:")
        print("  python scripts/linkedin_oauth.py")
        return False

    print("✓ Successfully retrieved user profile")

    # Display user info
    print("\n📋 User Information:")
    print(f"  Name: {user_info.get('name', 'N/A')}")
    print(f"  Email: {user_info.get('email', 'N/A')}")
    print(f"  Profile: {user_info.get('sub', 'N/A')}")

    if api.user_urn:
        print(f"  User URN: {api.user_urn}")
        print(f"  {'✓' if results['user_urn_available'] else '✗'} User URN available")

    # Test summary
    print("\n" + "=" * 80)
    if all([
        results['has_client_id'],
        results['has_client_secret'],
        results['token_valid'],
        results['can_get_user_info'],
        results['user_urn_available']
    ]):
        print("✓ All checks passed!")
        print("=" * 80)
        print("\nYour LinkedIn API is properly configured and ready to use.")
        print("\nNext steps:")
        print("  - Generate posts: python scripts/generate_sample_posts.py")
        print("  - Review posts: python -m src.review_cli")
        print("  - Publish posts: python -m src.publish_cli")
        print()
        return True
    else:
        print("⚠ Some checks failed")
        print("=" * 80)
        print("\nPlease address the issues above before publishing posts.")
        print()
        return False


def main():
    """Main entry point"""
    try:
        success = test_linkedin_api()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Test error: {e}")
        print(f"\n✗ Error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
