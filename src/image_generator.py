"""
Image generation for LinkedIn posts using Hugging Face Inference API.

Uses Stable Diffusion models via Hugging Face's free inference API.
"""

import os
import requests
from typing import Optional
from pathlib import Path
from datetime import datetime

from src.logger import logger
from config.settings import get_settings


class ImageGenerator:
    """Generate images for LinkedIn posts using Hugging Face Inference API."""

    # Stable Diffusion model - free to use via HF Inference API
    DEFAULT_MODEL = "stabilityai/stable-diffusion-2-1"

    # Alternative models you can try:
    # - "runwayml/stable-diffusion-v1-5"
    # - "CompVis/stable-diffusion-v1-4"
    # - "stabilityai/stable-diffusion-xl-base-1.0" (higher quality, slower)

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize image generator.

        Args:
            api_token: Hugging Face API token (free at huggingface.co)
        """
        self.settings = get_settings()
        self.api_token = api_token or os.getenv("HUGGINGFACE_API_TOKEN")

        if not self.api_token:
            logger.warning(
                "No Hugging Face API token found. Image generation will fail. "
                "Get a free token at https://huggingface.co/settings/tokens"
            )

        self.api_url = f"https://api-inference.huggingface.co/models/{self.DEFAULT_MODEL}"
        self.output_dir = Path("data/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized ImageGenerator with model: {self.DEFAULT_MODEL}")

    def generate_image_from_post(
        self,
        post_content: str,
        trend_title: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Generate an image for a LinkedIn post.

        Args:
            post_content: The post text content
            trend_title: Optional trend title for context
            max_retries: Number of retry attempts if generation fails

        Returns:
            Path to saved image file or None on failure
        """
        if not self.api_token:
            logger.error("Cannot generate image: No Hugging Face API token available")
            return None

        # Generate image prompt from post content
        image_prompt = self._create_image_prompt(post_content, trend_title)

        logger.info(f"Generating image with prompt: {image_prompt[:100]}...")

        # Try to generate the image with retries
        for attempt in range(max_retries):
            try:
                image_data = self._call_huggingface_api(image_prompt)

                if image_data:
                    # Save the image
                    image_path = self._save_image(image_data)
                    if image_path:
                        logger.info(f"✓ Successfully generated and saved image: {image_path}")
                        return str(image_path)

                logger.warning(f"Image generation attempt {attempt + 1}/{max_retries} failed")

            except Exception as e:
                logger.error(f"Error generating image (attempt {attempt + 1}/{max_retries}): {e}")

        logger.error("Failed to generate image after all retries")
        return None

    def _create_image_prompt(self, post_content: str, trend_title: Optional[str] = None) -> str:
        """
        Create an effective image prompt from post content.

        Args:
            post_content: The LinkedIn post text
            trend_title: Optional trend title for context

        Returns:
            Optimized prompt for Stable Diffusion
        """
        # Extract key concepts from the post
        # Remove hashtags and URLs
        import re
        clean_content = re.sub(r'#\w+', '', post_content)
        clean_content = re.sub(r'http\S+', '', clean_content)
        clean_content = re.sub(r'Source:\s*', '', clean_content)

        # Use trend title as primary subject if available
        subject = trend_title if trend_title else clean_content[:200]

        # Create a professional, tech-focused prompt
        prompt = f"""Professional technology illustration: {subject}.
Modern, clean design. Tech industry aesthetic.
High quality, professional photography style.
Relevant to AI, software development, and technology trends.
No text, no words, no letters in the image."""

        # Limit prompt length
        prompt = prompt[:500]

        return prompt

    def _call_huggingface_api(self, prompt: str, timeout: int = 60) -> Optional[bytes]:
        """
        Call Hugging Face Inference API to generate image.

        Args:
            prompt: Text prompt for image generation
            timeout: Request timeout in seconds

        Returns:
            Image data as bytes or None on failure
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": prompt,
            "options": {
                "wait_for_model": True  # Wait if model is loading
            }
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=timeout
            )

            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                # Model is loading, this is expected on first call
                logger.info("Model is loading, waiting...")
                return None
            else:
                error_msg = response.text
                logger.error(f"Hugging Face API error {response.status_code}: {error_msg}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Error calling Hugging Face API: {e}")
            return None

    def _save_image(self, image_data: bytes) -> Optional[Path]:
        """
        Save generated image to disk.

        Args:
            image_data: Image binary data

        Returns:
            Path to saved image or None on failure
        """
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_post_{timestamp}.png"
            filepath = self.output_dir / filename

            # Save image
            with open(filepath, "wb") as f:
                f.write(image_data)

            logger.info(f"Saved image to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Test connection to Hugging Face API.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.api_token:
            logger.error("No API token available for testing")
            return False

        try:
            logger.info("Testing Hugging Face API connection...")
            test_prompt = "A simple test image of technology"
            result = self._call_huggingface_api(test_prompt)

            if result:
                logger.info("✓ Hugging Face API connection successful")
                return True
            else:
                logger.warning("API responded but no image data received (model may be loading)")
                return False

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
