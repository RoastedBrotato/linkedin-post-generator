# Reddit API Setup Guide

## Step 1: Create a Reddit App

1. Go to https://www.reddit.com/prefs/apps
2. Scroll to the bottom and click **"create another app..."**
3. Fill in the form:
   - **name**: `linkedin-post-generator` (or any name you prefer)
   - **App type**: Select **"script"** (important!)
   - **description**: `Trend aggregator for LinkedIn posts`
   - **about url**: Leave blank
   - **redirect uri**: `http://localhost:8080` (not used for script apps, but required)
4. Click **"create app"**

## Step 2: Get Your Credentials

After creating the app, you'll see:
- **client_id**: A string under "personal use script" (looks like: `abc123XYZ456`)
- **secret**: The longer string labeled "secret" (looks like: `abc123-XYZ456def789...`)

## Step 3: Update .env File

Add these lines to your `.env` file:

```bash
# Reddit API Configuration
TRENDS_REDDIT_CLIENT_ID=your_client_id_here
TRENDS_REDDIT_CLIENT_SECRET=your_client_secret_here
TRENDS_REDDIT_USER_AGENT=linkedin-post-generator/1.0 by /u/your_reddit_username
```

**Important**: Replace:
- `your_client_id_here` with the client_id from Step 2
- `your_client_secret_here` with the secret from Step 2
- `your_reddit_username` with your actual Reddit username

## Example

If your credentials are:
- client_id: `abc123XYZ456`
- secret: `def789-GHI012jkl345`
- username: `john_doe`

Your `.env` entries would be:
```bash
TRENDS_REDDIT_CLIENT_ID=abc123XYZ456
TRENDS_REDDIT_CLIENT_SECRET=def789-GHI012jkl345
TRENDS_REDDIT_USER_AGENT=linkedin-post-generator/1.0 by /u/john_doe
```

## Step 4: Test the Integration

After updating `.env`, run:
```bash
python test_fetch_trends.py
```

You should now see Reddit trends being fetched successfully!

## Troubleshooting

**401 Unauthorized Error**:
- Double-check your client_id and client_secret
- Make sure you selected "script" as the app type
- Verify there are no extra spaces in your .env file

**Rate Limiting**:
- Reddit allows 60 requests per minute
- The code automatically limits to 10 items per subreddit to stay within limits

**No Trends Found**:
- This is normal if subreddits don't have relevant AI/tech posts
- The code filters by keywords, so only relevant posts are returned
