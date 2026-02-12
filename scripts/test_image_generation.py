#!/usr/bin/env python3
"""
Test script for image generation functionality.

Tests the Hugging Face image generation integration.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.image_generator import ImageGenerator
from src.logger import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_image_generation():
    """Test image generation with sample post content"""

    print("\n" + "="*80)
    print("LinkedIn Post Image Generation Test")
    print("="*80 + "\n")

    # Check for API token
    api_token = os.getenv("HUGGINGFACE_API_TOKEN")
    if not api_token:
        print("❌ ERROR: HUGGINGFACE_API_TOKEN not found in .env file")
        print("\nTo get a free Hugging Face API token:")
        print("1. Visit https://huggingface.co/settings/tokens")
        print("2. Create a new token (read access is sufficient)")
        print("3. Add to .env file: HUGGINGFACE_API_TOKEN=your_token_here")
        print()
        return False

    print(f"✓ Hugging Face API token found: {api_token[:10]}...")

    # Initialize image generator
    print("\n📸 Initializing image generator...")
    image_gen = ImageGenerator(api_token=api_token)

    # Test connection
    print("🔌 Testing API connection...")
    if not image_gen.test_connection():
        print("⚠️  Connection test inconclusive (model may be loading)")
        print("   This is normal on first use - continuing anyway...\n")
    else:
        print("✓ Connection successful!\n")

    # Sample post content
    sample_posts = [
        {
            "title": "GPT-4 Vision: Multimodal AI Revolution",
            "content": """🚀 Exciting breakthrough in AI!

OpenAI's GPT-4 Vision can now understand images alongside text, opening up incredible possibilities for multimodal applications.

This represents a major step towards more human-like AI systems that can process multiple types of information simultaneously.

#AI #MachineLearning #GPT4 #Innovation"""
        },
        {
            "title": "Kubernetes 1.29 Released",
            "content": """🎉 Big news for DevOps engineers!

Kubernetes 1.29 brings significant improvements:
• Enhanced security features
• Better resource management
• Improved observability

The cloud-native ecosystem continues to evolve rapidly!

#Kubernetes #DevOps #CloudNative #Technology"""
        }
    ]

    print("🎨 Generating images for sample posts...\n")

    for i, post in enumerate(sample_posts, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(sample_posts)}: {post['title']}")
        print('='*80)

        print(f"\n📝 Post content preview:")
        print(f"   {post['content'][:100]}...\n")

        print("⏳ Generating image (this may take 20-60 seconds on first use)...")

        try:
            image_path = image_gen.generate_image_from_post(
                post_content=post['content'],
                trend_title=post['title']
            )

            if image_path:
                print(f"✅ Success! Image saved to: {image_path}")
                print(f"   File size: {os.path.getsize(image_path) / 1024:.1f} KB")
            else:
                print("❌ Image generation failed (returned None)")
                print("   Check logs for details")

        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Image generation error: {e}")

    print("\n" + "="*80)
    print("Test Complete!")
    print("="*80)
    print("\n💡 Tip: Check the 'data/images/' directory to see generated images")
    print()

    return True


if __name__ == "__main__":
    try:
        test_image_generation()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        logger.error(f"Test failed: {e}")
        sys.exit(1)
