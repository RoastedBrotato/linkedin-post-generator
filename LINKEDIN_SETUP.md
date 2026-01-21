# LinkedIn API Setup Guide

This guide walks you through setting up LinkedIn API access for the LinkedIn Post Generator.

## Overview

The LinkedIn Post Generator uses the LinkedIn API v2 to publish approved posts to your LinkedIn profile. This requires:
- OAuth 2.0 authentication (3-legged flow)
- Access to the UGC Posts API
- Required scopes: `w_member_social`, `r_liteprofile`, `openid`, `profile`, `email`

## Prerequisites

- A LinkedIn account
- A LinkedIn Developer account

---

## Step 1: Create a LinkedIn App

1. **Go to LinkedIn Developer Portal**
   - Visit: https://www.linkedin.com/developers/apps
   - Sign in with your LinkedIn account

2. **Create New App**
   - Click "Create app"
   - Fill in the required information:
     - **App name**: LinkedIn Post Generator (or your preferred name)
     - **LinkedIn Page**: Associate with your personal page or company page
     - **Privacy policy URL**: Can use a placeholder for personal projects
     - **App logo**: Upload a simple logo (optional)
   - Agree to LinkedIn API Terms of Use
   - Click "Create app"

3. **Note Your Credentials**
   After creation, go to the "Auth" tab and note:
   - **Client ID**: Your app's client ID
   - **Client Secret**: Your app's client secret (keep this secure!)

---

## Step 2: Configure OAuth Settings

1. **Add Redirect URLs**
   - In the "Auth" tab, scroll to "OAuth 2.0 settings"
   - Add redirect URL: `http://localhost:8000/callback`
   - This is used for the OAuth authorization flow
   - Click "Update"

2. **Request API Products**
   - Go to the "Products" tab
   - Request access to:
     - **Sign In with LinkedIn using OpenID Connect**
     - **Share on LinkedIn**
   - Click "Request access" for each product
   - LinkedIn will review your request (usually approved within a few hours to days)

3. **Wait for Approval**
   - Check your email for approval notifications
   - You can also check the "Products" tab for approval status
   - ⚠️ You cannot publish posts until these products are approved

---

## Step 3: Verify Your Scopes

Once your products are approved, go to the "Auth" tab and verify you have these OAuth 2.0 scopes:

- ✅ `openid` - Get your LinkedIn ID
- ✅ `profile` - Get your profile information
- ✅ `email` - Get your email address
- ✅ `w_member_social` - Write posts on your behalf

These scopes should appear automatically after product approval.

---

## Step 4: Configure Your Application

1. **Update .env file**
   Add your LinkedIn credentials to `.env`:

   ```bash
   # LinkedIn API Configuration
   LINKEDIN_CLIENT_ID=your_client_id_here
   LINKEDIN_CLIENT_SECRET=your_client_secret_here
   LINKEDIN_REDIRECT_URI=http://localhost:8000/callback

   # These will be populated after first OAuth flow
   LINKEDIN_ACCESS_TOKEN=
   LINKEDIN_REFRESH_TOKEN=
   LINKEDIN_TOKEN_EXPIRES_AT=
   LINKEDIN_USER_URN=
   ```

2. **Keep credentials secure**
   - Never commit `.env` to git
   - `.env` is already in `.gitignore`

---

## Step 5: Authenticate (First Time Only)

Run the OAuth authentication script to get your access token:

```bash
source venv/bin/activate
python scripts/linkedin_oauth.py
```

This will:
1. Open your browser to LinkedIn authorization page
2. Ask you to approve the app
3. Redirect back to localhost with an authorization code
4. Exchange the code for an access token
5. Save the token to `.env` automatically

---

## Step 6: Test Your Setup

Test that your LinkedIn API is working:

```bash
python scripts/test_linkedin_api.py
```

This will:
- Verify your access token is valid
- Get your LinkedIn profile information
- Display your author URN (needed for posting)

---

## Token Management

**Access Token Lifespan:**
- LinkedIn access tokens last **60 days**
- Tokens are automatically refreshed when possible
- You'll need to re-authenticate when tokens expire

**Token Storage:**
- Tokens are stored in `.env` file
- Never share your `.env` file
- Use environment variables in production

---

## Publishing Posts

Once authenticated, you can publish approved posts:

```bash
python -m src.publish_cli
```

Or use the publishing methods directly:

```python
from src.linkedin_api import LinkedInAPI
from src.database import Database

db = Database()
api = LinkedInAPI()

# Get approved posts
approved_posts = db.get_posts(status="approved")

# Publish a post
if approved_posts:
    post = approved_posts[0]
    result = api.publish_post(
        text=post['content'],
        post_id=post['id']
    )

    if result:
        print(f"Published! Post URL: {result['post_url']}")
```

---

## Rate Limits

LinkedIn API has the following rate limits:

- **Community Management APIs**: 500 requests per user per day
- **Posts**: No specific limit documented, but recommended to space posts
- **Best Practice**: Don't post more than 3-5 times per day

The LinkedIn Post Generator automatically handles rate limiting.

---

## Troubleshooting

### "Access token is invalid or expired"
- Run `python scripts/linkedin_oauth.py` to re-authenticate

### "Products not approved yet"
- Check the "Products" tab in LinkedIn Developer Portal
- Wait for approval (can take 1-3 days)
- You may need to provide additional information about your app usage

### "Invalid redirect URI"
- Ensure `http://localhost:8000/callback` is added in OAuth settings
- Check that `.env` has matching `LINKEDIN_REDIRECT_URI`

### "Insufficient privileges"
- Verify `w_member_social` scope is available
- Ensure "Share on LinkedIn" product is approved

### "Cannot resolve author URN"
- Run the test script to get your URN: `python scripts/test_linkedin_api.py`
- URN format should be: `urn:li:person:XXXXXXXXXX`

---

## API Documentation References

- [LinkedIn OAuth 2.0 Authentication](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [3-Legged OAuth Flow](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow)
- [UGC Posts API](https://learn.microsoft.com/en-us/linkedin/compliance/integrations/shares/ugc-post-api)
- [Developer Portal](https://www.linkedin.com/developers/)

---

## Security Best Practices

1. **Never commit credentials**
   - Keep `.env` in `.gitignore`
   - Use environment variables in production

2. **Rotate tokens regularly**
   - Re-authenticate every 30-45 days
   - Monitor token expiration

3. **Limit scope permissions**
   - Only request scopes you need
   - Current scopes are minimal for posting

4. **Monitor API usage**
   - Check Developer Portal for usage metrics
   - Stay within rate limits

---

## Next Steps

After completing setup:
1. ✅ Test authentication with `scripts/linkedin_oauth.py`
2. ✅ Verify setup with `scripts/test_linkedin_api.py`
3. ✅ Generate and approve some posts with `src/review_cli.py`
4. ✅ Publish your first post with `src/publish_cli.py`

If you encounter any issues, check the troubleshooting section or refer to the official LinkedIn API documentation.
