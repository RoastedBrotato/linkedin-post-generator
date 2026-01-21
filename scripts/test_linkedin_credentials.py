#!/usr/bin/env python3
"""
Quick test to validate LinkedIn credentials format.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import get_settings

def test_credentials():
    """Test if LinkedIn credentials are properly configured"""
    settings = get_settings()

    print("\n" + "="*60)
    print("LinkedIn Credentials Check")
    print("="*60)

    # Check client ID
    if not settings.linkedin.client_id:
        print("❌ LINKEDIN_CLIENT_ID is missing")
        return False
    else:
        print(f"✓ Client ID found: {settings.linkedin.client_id}")
        print(f"  Length: {len(settings.linkedin.client_id)} characters")

    # Check client secret
    if not settings.linkedin.client_secret:
        print("❌ LINKEDIN_CLIENT_SECRET is missing")
        return False
    else:
        print(f"✓ Client Secret found: {settings.linkedin.client_secret[:15]}...")
        print(f"  Length: {len(settings.linkedin.client_secret)} characters")

    # Check redirect URI
    if not settings.linkedin.redirect_uri:
        print("❌ LINKEDIN_REDIRECT_URI is missing")
        return False
    else:
        print(f"✓ Redirect URI: {settings.linkedin.redirect_uri}")

    print("\n" + "="*60)
    print("Credentials format looks good!")
    print("="*60)

    print("\nNext steps:")
    print("1. Make sure your LinkedIn app has these settings:")
    print(f"   - Redirect URL: {settings.linkedin.redirect_uri}")
    print("   - Required products:")
    print("     • Sign In with LinkedIn using OpenID Connect")
    print("     • Share on LinkedIn (for w_member_social scope)")
    print("\n2. Run the OAuth flow:")
    print("   python scripts/linkedin_oauth.py")
    print()

    return True

if __name__ == "__main__":
    try:
        success = test_credentials()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
