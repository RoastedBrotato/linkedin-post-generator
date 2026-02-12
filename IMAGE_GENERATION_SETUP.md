# Image Generation Setup Guide

This guide explains how to set up and use the automatic image generation feature for LinkedIn posts.

## Overview

The LinkedIn Post Generator now automatically creates relevant images for each post using **Hugging Face's Stable Diffusion** models. Posts with images get significantly higher engagement on LinkedIn!

## Features

- **Automatic image generation** for every post
- **AI-powered relevance** - images match post content
- **Free to use** with Hugging Face's free API tier
- **Professional quality** - clean, modern tech aesthetic
- **Seamless integration** - images automatically attach when publishing

## Quick Start

### 1. Get Your Free Hugging Face API Token

1. Visit [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create a new access token:
   - Click "New token"
   - Name it (e.g., "linkedin-post-generator")
   - Select "Read" access (default)
   - Click "Generate"
3. Copy your token (starts with `hf_...`)

### 2. Add Token to Environment

Edit your `.env` file and add:

```bash
HUGGINGFACE_API_TOKEN=hf_your_token_here
```

### 3. Test Image Generation

Run the test script to verify everything works:

```bash
python scripts/test_image_generation.py
```

This will:
- Verify your API token
- Test the connection to Hugging Face
- Generate sample images
- Save them to `data/images/`

**Note:** The first image may take 30-60 seconds as the model loads. Subsequent images are faster (10-20 seconds).

### 4. Generate Posts with Images

Now when you generate posts, images will be created automatically:

```bash
# Generate a single post with image
python scripts/generate_post_from_trend.py --save-to-db

# Generate batch posts with images
python scripts/generate_sample_posts.py
```

### 5. Review and Publish

Use the review and publish CLI as usual. The CLI will show if a post has an image attached:

```bash
# Review posts
python src/review_cli.py

# Publish posts (images automatically included)
python src/publish_cli.py
```

## How It Works

1. **Post Generation**: After creating post text, the system generates an image prompt based on the content
2. **Image Creation**: Sends prompt to Hugging Face Stable Diffusion API
3. **Local Storage**: Saves generated image to `data/images/` directory
4. **Database Tracking**: Stores image path in the database with the post
5. **Publishing**: When publishing, LinkedIn API automatically uploads and attaches the image

## Image Prompt Generation

The system intelligently creates image prompts by:
- Extracting key concepts from post content
- Using trend titles as primary subjects
- Adding professional, tech-focused styling
- Removing text/hashtags to keep images clean

Example:
- **Post**: "GPT-4 Vision: Multimodal AI Revolution..."
- **Image Prompt**: "Professional technology illustration: GPT-4 Vision: Multimodal AI Revolution. Modern, clean design. Tech industry aesthetic..."

## Configuration

### Model Selection

The default model is `stabilityai/stable-diffusion-2-1`. To use a different model, edit `src/image_generator.py`:

```python
# Available alternatives:
# - runwayml/stable-diffusion-v1-5 (faster, slightly lower quality)
# - CompVis/stable-diffusion-v1-4 (faster)
# - stabilityai/stable-diffusion-xl-base-1.0 (higher quality, slower)

DEFAULT_MODEL = "stabilityai/stable-diffusion-2-1"
```

### Image Storage

Images are saved to `data/images/` with timestamped filenames:
```
data/images/linkedin_post_20260209_143052.png
```

## Troubleshooting

### "Model is loading" message

This is normal on first use. The Hugging Face API loads the model on-demand. Wait 30-60 seconds and it will complete.

### API rate limits

The free tier has rate limits:
- **Requests**: Limited per hour (usually sufficient for testing)
- **Concurrent**: 1 request at a time

If you hit limits:
1. Wait a few minutes
2. Consider upgrading to Hugging Face Pro ($9/month, unlimited API)

### Image generation fails

Check:
1. API token is correct in `.env`
2. Token has not expired
3. Internet connection is working
4. Check logs in `logs/` directory for detailed errors

### No image attached when publishing

Verify:
1. Image path is stored in database: Check `image_path` column
2. Image file exists at the path
3. File permissions allow reading

## Cost & Performance

### Hugging Face Free Tier

- **Cost**: Free ✅
- **Rate Limit**: ~100 requests/hour
- **Quality**: High (Stable Diffusion 2.1)
- **Speed**: 10-30 seconds per image

### Upgrading (Optional)

For production use with higher volume:

**Hugging Face Pro** ($9/month):
- Unlimited API calls
- Faster processing
- Priority access to models

## Alternative Image Sources

If you prefer not to use AI generation, you can manually set images:

1. Place images in `data/images/`
2. Update the post record:
   ```python
   db.update_post(post_id, image_path="data/images/my_custom_image.png")
   ```

## Best Practices

1. **Review images** before publishing - check they're relevant
2. **Use descriptive trend titles** - better titles = better images
3. **Monitor API usage** - stay within free tier limits
4. **Keep images professional** - the system prompts for professional aesthetics
5. **Test first** - run the test script before batch generation

## Examples

### Example 1: Tech Trend Post with Image

**Input**:
```
Title: "New TypeScript 5.0 Features"
Content: "TypeScript 5.0 brings decorators, const type parameters..."
```

**Generated Image**: Clean illustration of TypeScript logo with modern design elements

### Example 2: AI/ML Post with Image

**Input**:
```
Title: "LLaMA 2 Released for Commercial Use"
Content: "Meta releases LLaMA 2, democratizing access to powerful LLMs..."
```

**Generated Image**: Professional visualization of AI/ML concepts with tech aesthetic

## Support

If you encounter issues:
1. Check logs: `logs/app.log`
2. Run test script: `python scripts/test_image_generation.py`
3. Verify .env configuration
4. Check Hugging Face API status: [status.huggingface.co](https://status.huggingface.co)

## Next Steps

Now that image generation is set up:

1. ✅ Generate posts with images
2. ✅ Review in the CLI
3. ✅ Publish to LinkedIn with automatic image upload
4. ✅ Track engagement (posts with images get ~2-3x more engagement!)

Happy posting! 🚀
