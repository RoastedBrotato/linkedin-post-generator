#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 authentication flow.

This script helps you authenticate with LinkedIn and obtain access tokens.
Tokens are automatically saved to .env file.
"""

import sys
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.linkedin_api import LinkedInAPI
from src.logger import logger
from config.settings import get_settings

settings = get_settings()


class ReuseHTTPServer(HTTPServer):
    """HTTP server that allows address reuse"""
    allow_reuse_address = True


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP server handler for OAuth callback"""

    authorization_code = None
    state = None

    def do_GET(self):
        """Handle GET request from OAuth callback"""
        try:
            # Parse query parameters
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            if "code" in query:
                # Success - got authorization code
                OAuthCallbackHandler.authorization_code = query["code"][0]
                OAuthCallbackHandler.state = query.get("state", [None])[0]

                # Send success response
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                success_html = """
                <html>
                <head><title>LinkedIn Authentication Success</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #0077B5;">✓ Authentication Successful!</h1>
                    <p>You have successfully authenticated with LinkedIn.</p>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode())
                logger.info("Received authorization code from LinkedIn")

            elif "error" in query:
                # Error occurred
                error = query.get("error", ["Unknown error"])[0]
                error_desc = query.get("error_description", [""])[0]

                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                error_html = f"""
                <html>
                <head><title>LinkedIn Authentication Error</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #D14;">✗ Authentication Failed</h1>
                    <p><strong>Error:</strong> {error}</p>
                    <p>{error_desc}</p>
                    <p>Please return to the terminal and try again.</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode())
                logger.error(f"OAuth error: {error} - {error_desc}")

        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")

    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        pass


def update_env_file(token_data: dict, user_urn: str):
    """
    Update .env file with new tokens.

    Args:
        token_data: Dict containing access_token, refresh_token, expires_at
        user_urn: LinkedIn user URN
    """
    env_file = ROOT / ".env"

    try:
        # Read existing .env content
        if env_file.exists():
            with open(env_file, "r") as f:
                lines = f.readlines()
        else:
            lines = []

        # Update or add token values
        updates = {
            "LINKEDIN_ACCESS_TOKEN": token_data["access_token"],
            "LINKEDIN_REFRESH_TOKEN": token_data.get("refresh_token", ""),
            "LINKEDIN_TOKEN_EXPIRES_AT": token_data["expires_at"],
            "LINKEDIN_USER_URN": user_urn,
        }

        updated_lines = []
        updated_keys = set()

        for line in lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith("#"):
                key = line_stripped.split("=")[0]
                if key in updates:
                    updated_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # Add any missing keys
        for key, value in updates.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}\n")

        # Write back to .env
        with open(env_file, "w") as f:
            f.writelines(updated_lines)

        logger.info("✓ Updated .env file with tokens")
        print("\n✓ Tokens saved to .env file")

    except Exception as e:
        logger.error(f"Error updating .env file: {e}")
        print(f"\n✗ Failed to update .env: {e}")
        print("\nPlease manually add these to your .env file:")
        for key, value in updates.items():
            print(f"{key}={value}")


def run_oauth_flow():
    """Run the complete OAuth authentication flow"""
    print("\n" + "=" * 80)
    print("LinkedIn OAuth 2.0 Authentication")
    print("=" * 80)

    # Check for client credentials
    if not settings.linkedin.client_id or not settings.linkedin.client_secret:
        print("\n✗ Missing LinkedIn API credentials!")
        print("\nPlease add these to your .env file:")
        print("  LINKEDIN_CLIENT_ID=your_client_id_here")
        print("  LINKEDIN_CLIENT_SECRET=your_client_secret_here")
        print("\nSee LINKEDIN_SETUP.md for instructions on getting credentials.")
        return False

    print(f"\n✓ Found client credentials")
    print(f"  Client ID: {settings.linkedin.client_id[:20]}...")

    # Initialize API client
    api = LinkedInAPI()

    # Generate authorization URL
    state = "linkedin_oauth_" + str(hash(str(settings.linkedin.client_id)))[:10]
    auth_url = api.get_authorization_url(state=state)

    print(f"\n📋 Step 1: Authorize the application")
    print(f"\nOpening browser to LinkedIn authorization page...")
    print(f"If the browser doesn't open, visit this URL:\n{auth_url}\n")

    # Open browser
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        logger.warning(f"Could not open browser: {e}")

    # Start local HTTP server to receive callback
    print("📋 Step 2: Waiting for authorization callback...")
    print("(After approving, you'll be redirected back here)\n")

    server = ReuseHTTPServer(("localhost", 8000), OAuthCallbackHandler)

    # Run server in thread with timeout
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()
    server_thread.join(timeout=300)  # 5 minute timeout

    # Close server properly
    try:
        server.server_close()
    except Exception as e:
        logger.warning(f"Error closing server: {e}")

    if not OAuthCallbackHandler.authorization_code:
        print("\n✗ Timeout waiting for authorization")
        print("Please try again and approve the app within 5 minutes.")
        return False

    # Exchange code for token
    print("📋 Step 3: Exchanging authorization code for access token...")
    token_data = api.exchange_code_for_token(OAuthCallbackHandler.authorization_code)

    if not token_data:
        print("\n✗ Failed to obtain access token")
        print("Please check your credentials and try again.")
        return False

    print("\n✓ Successfully obtained access token")
    print(f"  Expires: {token_data['expires_at']}")

    # Get user info to obtain URN
    print("\n📋 Step 4: Fetching user profile information...")
    user_info = api.get_user_info()

    if not user_info:
        print("\n✗ Failed to get user information")
        print("Token obtained but cannot retrieve user URN.")
        return False

    print("\n✓ Successfully retrieved user profile")
    print(f"  Name: {user_info.get('name', 'Unknown')}")
    print(f"  Email: {user_info.get('email', 'Unknown')}")
    print(f"  URN: {api.user_urn}")

    # Save tokens to .env
    print("\n📋 Step 5: Saving tokens to .env file...")
    update_env_file(token_data, api.user_urn)

    print("\n" + "=" * 80)
    print("✓ Authentication Complete!")
    print("=" * 80)
    print("\nYou can now use the LinkedIn API to publish posts.")
    print("\nNext steps:")
    print("  1. Test your setup: python scripts/test_linkedin_api.py")
    print("  2. Publish a post: python -m src.publish_cli")
    print()

    return True


def main():
    """Main entry point"""
    try:
        success = run_oauth_flow()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n✗ Authentication cancelled by user\n")
        return 1
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        print(f"\n✗ Error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
