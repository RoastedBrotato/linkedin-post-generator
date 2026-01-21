"""
LinkedIn API client for OAuth authentication and post publishing.

Implements OAuth 2.0 flow and UGC Posts API v2 integration.
"""

import requests
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from src.logger import logger
from src.database import Database
from config.settings import get_settings

settings = get_settings()


class LinkedInAPI:
    """Client for LinkedIn API v2 with OAuth 2.0 support"""

    # API endpoints
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    API_BASE_URL = "https://api.linkedin.com/v2"
    UGC_POSTS_URL = f"{API_BASE_URL}/ugcPosts"
    USER_INFO_URL = f"{API_BASE_URL}/userinfo"

    # Required scopes for posting
    SCOPES = [
        "openid",
        "profile",
        "email",
        "w_member_social"
    ]

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize LinkedIn API client.

        Args:
            db: Database instance for storing publishing history
        """
        self.db = db or Database()
        self.client_id = settings.linkedin.client_id
        self.client_secret = settings.linkedin.client_secret
        self.redirect_uri = settings.linkedin.redirect_uri

        # Token management
        self.access_token = settings.linkedin.access_token
        self.refresh_token = settings.linkedin.refresh_token
        self.token_expires_at = settings.linkedin.token_expires_at
        self.user_urn = settings.linkedin.user_urn

        # Rate limiting (simple implementation)
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests

        logger.info("Initialized LinkedIn API client")

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get the OAuth authorization URL for user to visit.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.SCOPES),
        }

        if state:
            params["state"] = state

        url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info("Generated authorization URL")
        return url

    def exchange_code_for_token(self, authorization_code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token.

        Args:
            authorization_code: Code received from OAuth callback

        Returns:
            Token data dict or None on failure
        """
        try:
            logger.info("Exchanging authorization code for access token")

            data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            response = requests.post(
                self.TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                token_data = response.json()

                # Calculate expiration time
                expires_in = token_data.get("expires_in", 5183999)  # LinkedIn default: 60 days
                expires_at = datetime.now() + timedelta(seconds=expires_in)

                # Store tokens
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                self.token_expires_at = expires_at.isoformat()

                logger.info(f"Successfully obtained access token (expires: {expires_at})")

                return {
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "expires_at": self.token_expires_at,
                    "expires_in": expires_in,
                }
            else:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error exchanging authorization code: {e}")
            return None

    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using refresh token.

        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token:
            logger.warning("No refresh token available")
            return False

        try:
            logger.info("Refreshing access token")

            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            response = requests.post(
                self.TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                token_data = response.json()

                expires_in = token_data.get("expires_in", 5183999)
                expires_at = datetime.now() + timedelta(seconds=expires_in)

                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token", self.refresh_token)
                self.token_expires_at = expires_at.isoformat()

                logger.info(f"Successfully refreshed access token (expires: {expires_at})")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return False

    def is_token_expired(self) -> bool:
        """
        Check if access token is expired or will expire soon.

        Returns:
            True if expired or expiring within 1 day
        """
        if not self.token_expires_at:
            return True

        try:
            expires_at = datetime.fromisoformat(self.token_expires_at)
            # Consider expired if less than 1 day remaining
            buffer = timedelta(days=1)
            return datetime.now() >= (expires_at - buffer)
        except Exception:
            return True

    def ensure_valid_token(self) -> bool:
        """
        Ensure we have a valid access token, refreshing if needed.

        Returns:
            True if valid token available, False otherwise
        """
        if not self.access_token:
            logger.error("No access token available. Please authenticate first.")
            return False

        if self.is_token_expired():
            logger.info("Access token expired, attempting refresh")
            if not self.refresh_access_token():
                logger.error("Token refresh failed. Please re-authenticate.")
                return False

        return True

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get authenticated user's profile information.

        Returns:
            User info dict or None on failure
        """
        if not self.ensure_valid_token():
            return None

        try:
            self._rate_limit()

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(self.USER_INFO_URL, headers=headers)

            if response.status_code == 200:
                user_info = response.json()

                # Extract and store user URN
                if "sub" in user_info:
                    self.user_urn = f"urn:li:person:{user_info['sub']}"
                    logger.info(f"Retrieved user URN: {self.user_urn}")

                return user_info
            else:
                logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    def publish_post(
        self,
        text: str,
        post_id: Optional[int] = None,
        visibility: str = "PUBLIC"
    ) -> Optional[Dict[str, Any]]:
        """
        Publish a text post to LinkedIn.

        Args:
            text: Post content
            post_id: Optional database post ID for tracking
            visibility: Post visibility (PUBLIC, CONNECTIONS, LOGGED_IN)

        Returns:
            Dict with post_url and linkedin_post_id or None on failure
        """
        if not self.ensure_valid_token():
            logger.error("Cannot publish: Invalid or missing access token")
            return None

        if not self.user_urn:
            logger.info("User URN not set, fetching user info")
            user_info = self.get_user_info()
            if not user_info:
                logger.error("Cannot publish: Failed to get user URN")
                return None

        try:
            self._rate_limit()

            logger.info(f"Publishing post to LinkedIn (length: {len(text)} chars)")

            # Build post data according to UGC Posts API v2
            post_data = {
                "author": self.user_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility
                }
            }

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }

            response = requests.post(
                self.UGC_POSTS_URL,
                headers=headers,
                json=post_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                linkedin_post_id = result.get("id", "")

                # Construct post URL
                # LinkedIn post URLs: https://www.linkedin.com/feed/update/{urn}
                post_url = f"https://www.linkedin.com/feed/update/{linkedin_post_id}" if linkedin_post_id else None

                logger.info(f"✓ Successfully published post to LinkedIn: {linkedin_post_id}")

                # Update database if post_id provided
                if post_id:
                    self._update_post_status(post_id, linkedin_post_id, post_url)

                return {
                    "linkedin_post_id": linkedin_post_id,
                    "post_url": post_url,
                    "published_at": datetime.now().isoformat()
                }
            else:
                logger.error(f"Failed to publish post: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error publishing post: {e}")
            return None

    def _update_post_status(
        self,
        post_id: int,
        linkedin_post_id: str,
        post_url: Optional[str]
    ):
        """
        Update database after successful publishing.

        Args:
            post_id: Database post ID
            linkedin_post_id: LinkedIn's post ID
            post_url: LinkedIn post URL
        """
        try:
            # Update post status
            self.db.update_post(
                post_id,
                status="published",
                published_at=datetime.now().isoformat()
            )

            # Record in publishing history
            self.db.add_publishing_history(
                post_id=post_id,
                platform="linkedin",
                platform_post_id=linkedin_post_id,
                post_url=post_url or "",
                status="success",
                metadata={
                    "published_at": datetime.now().isoformat(),
                    "visibility": "PUBLIC"
                }
            )

            logger.info(f"Updated database for post {post_id}")

        except Exception as e:
            logger.error(f"Error updating database after publishing: {e}")

    def _rate_limit(self):
        """Simple rate limiting to avoid hitting API limits"""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def validate_setup(self) -> Dict[str, bool]:
        """
        Validate LinkedIn API setup and credentials.

        Returns:
            Dict with validation results
        """
        results = {
            "has_client_id": bool(self.client_id),
            "has_client_secret": bool(self.client_secret),
            "has_access_token": bool(self.access_token),
            "token_valid": False,
            "can_get_user_info": False,
            "user_urn_available": bool(self.user_urn),
        }

        if results["has_access_token"]:
            results["token_valid"] = not self.is_token_expired()

            if results["token_valid"]:
                user_info = self.get_user_info()
                results["can_get_user_info"] = user_info is not None
                results["user_urn_available"] = bool(self.user_urn)

        return results
