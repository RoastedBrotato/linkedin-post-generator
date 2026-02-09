"""
LLM integration for LinkedIn post generation.

Supports local LLM (Ollama) with OpenAI as optional fallback.
"""

import ollama
from typing import Optional, Dict, Any, List
from src.logger import logger
from src.post_templates import get_post_template_prompt
from config.settings import get_settings

settings = get_settings()


class LLMClient:
    """Client for generating LinkedIn posts using LLM"""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            model: Model name to use (defaults to config)
        """
        self.provider = settings.llm.provider
        self.model = model or settings.llm.model
        self.temperature = settings.llm.temperature
        self.max_tokens = settings.llm.max_tokens

        logger.info(f"Initialized LLM client: provider={self.provider}, model={self.model}")

    def generate_post(
        self,
        trend: Dict[str, Any],
        post_format: str = "standard",
        system_prompt: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a LinkedIn post from a trend.

        Args:
            trend: Trend dictionary with title, description, url, etc.
            post_format: Post format type (standard, insight, story, etc.)
            system_prompt: Optional custom system prompt
            max_retries: Number of retry attempts on failure

        Returns:
            Dict with 'content', 'hashtags', 'sources', 'post_format' or None on failure
        """
        if not system_prompt:
            system_prompt = self._get_default_system_prompt()

        user_prompt = self._build_user_prompt(trend, post_format)

        for attempt in range(max_retries):
            try:
                logger.info(f"Generating post for trend: {trend.get('title', 'Unknown')[:50]}...")

                if self.provider == "ollama":
                    response = self._generate_ollama(system_prompt, user_prompt)
                elif self.provider == "openai":
                    response = self._generate_openai(system_prompt, user_prompt)
                else:
                    logger.error(f"Unknown provider: {self.provider}")
                    return None

                if response:
                    parsed = self._parse_post_response(response, trend, post_format)
                    if parsed:
                        logger.info(f"Successfully generated {post_format} post")
                        return parsed

                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed, retrying...")

            except Exception as e:
                logger.error(f"Error generating post (attempt {attempt + 1}): {e}")

        logger.error("Failed to generate post after all retries")
        return None

    def generate_comment(
        self,
        post_text: str,
        max_chars: int = 240,
        max_retries: int = 2
    ) -> Optional[str]:
        """Generate a short, single-line LinkedIn comment for a given post."""
        system_prompt = (
            "You write concise, professional LinkedIn comments about AI/tech posts. "
            "Comments must be a single line, specific to the post, and invite light engagement. "
            "No emojis, no hashtags, no bullet points."
        )
        user_prompt = (
            "Write a single-line LinkedIn comment (max "
            f"{max_chars} characters) that reacts thoughtfully to this post:\n\n"
            f"{post_text.strip()}\n\n"
            "Return only the comment text."
        )

        for attempt in range(max_retries):
            try:
                if self.provider == "ollama":
                    response = ollama.chat(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        options={
                            "temperature": max(0.2, min(0.7, self.temperature)),
                            "num_predict": min(200, self.max_tokens),
                        },
                    )
                    content = response["message"]["content"]
                elif self.provider == "openai":
                    logger.error("OpenAI provider not yet implemented for comments")
                    content = None
                else:
                    logger.error(f"Unknown provider: {self.provider}")
                    content = None

                if not content:
                    raise ValueError("Empty LLM response")

                # Enforce single line and length
                comment = " ".join(content.strip().splitlines()).strip()
                if len(comment) > max_chars:
                    comment = comment[:max_chars].rstrip()

                if comment:
                    return comment

            except Exception as e:
                logger.error(f"Error generating comment (attempt {attempt + 1}): {e}")

        logger.error("Failed to generate comment after all retries")
        return None

    def _generate_ollama(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Generate using Ollama"""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            )

            return response['message']['content']

        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            return None

    def _generate_openai(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Generate using OpenAI (fallback)"""
        # TODO: Implement OpenAI integration if needed
        logger.error("OpenAI provider not yet implemented")
        return None

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for LinkedIn post generation"""
        return """You are an AI assistant that creates engaging LinkedIn posts about AI and technology trends.

Your posts should:
- Be professional but conversational
- Start with a hook that grabs attention
- Provide valuable insights or takeaways
- Include relevant context and facts from the source
- Be 200-600 words (2-4 short paragraphs)
- End with a thought-provoking question or call-to-action
- Include 3-5 relevant hashtags
- Always cite the source URL

Style guidelines:
- Use short paragraphs (2-3 sentences max)
- Write in first person occasionally ("I think", "In my view")
- Be authentic and avoid corporate jargon
- Use line breaks for readability
- Don't use emojis unless specifically requested

Output rules (follow strictly):
- Respond with ONLY the template below (no extra commentary before or after).
- Keep the labels exactly as shown.
- Populate each section with content.

Template (copy exactly, then fill in):

POST_CONTENT:
[Your LinkedIn post content here]

HASHTAGS:
#AI #MachineLearning #Technology

SOURCE:
[Original article URL]

CONFIDENCE: [High/Medium/Low]
"""

    def _build_user_prompt(self, trend: Dict[str, Any], post_format: str = "standard") -> str:
        """Build user prompt from trend data"""
        # If using a template, get the template-specific prompt
        if post_format != "standard":
            return get_post_template_prompt(post_format, trend)

        # Otherwise use the default/standard format
        title = trend.get('title', 'No title')
        description = trend.get('description', 'No description')
        url = trend.get('url', '')
        category = trend.get('category', 'tech').upper()
        relevance = trend.get('relevance_score', 0)

        # Get source info
        metadata = trend.get('metadata', {})
        source_name = (
            metadata.get('feed_name') or
            f"r/{metadata.get('subreddit')}" if metadata.get('subreddit') else
            metadata.get('repo_name') or
            'Hacker News'
        )

        prompt = f"""Create a LinkedIn post about this {category} trend:

Title: {title}

Description: {description}

Source: {source_name}
URL: {url}
Relevance Score: {relevance:.2f}

Please write an engaging LinkedIn post that:
1. Explains why this trend matters
2. Provides insights or analysis
3. Includes the source URL for credibility
4. Ends with a question to encourage engagement

Remember to follow the format specified in the system prompt.
"""
        return prompt

    def _parse_post_response(self, response: str, trend: Dict[str, Any], post_format: str = "standard") -> Optional[Dict[str, Any]]:
        """Parse LLM response into structured post data"""
        try:
            # Extract sections
            sections = {}
            current_section = None
            content_lines = []

            for line in response.split('\n'):
                line_stripped = line.strip()

                if line_stripped.startswith('POST_CONTENT:'):
                    current_section = 'content'
                    content_lines = []
                elif line_stripped.startswith('HASHTAGS:'):
                    if current_section == 'content':
                        sections['content'] = '\n'.join(content_lines).strip()
                    current_section = 'hashtags'
                    content_lines = []
                elif line_stripped.startswith('SOURCE:'):
                    if current_section == 'hashtags':
                        sections['hashtags'] = ' '.join(content_lines).strip()
                    current_section = 'source'
                    content_lines = []
                elif line_stripped.startswith('CONFIDENCE:'):
                    if current_section == 'source':
                        sections['source'] = ' '.join(content_lines).strip()
                    current_section = 'confidence'
                    content_lines = []
                elif current_section and line_stripped:
                    content_lines.append(line_stripped)

            # Handle last section
            if current_section == 'confidence' and content_lines:
                sections['confidence'] = ' '.join(content_lines).strip()

            # Validate required sections
            if 'content' not in sections or not sections['content']:
                logger.warning("No content found in LLM response, falling back to heuristic parsing")
                return self._heuristic_parse_response(response, trend, post_format)

            # Extract hashtags
            hashtags_text = sections.get('hashtags', '')
            hashtags = [tag.strip() for tag in hashtags_text.split() if tag.startswith('#')]

            # Ensure source URL is included
            source_url = sections.get('source', trend.get('url', '')).strip()
            if not source_url:
                source_url = trend.get('url', '')

            return {
                'content': sections['content'],
                'hashtags': hashtags[:5],  # Limit to 5 hashtags
                'source_url': source_url,
                'confidence': sections.get('confidence', 'Medium'),
                'trend_id': trend.get('id'),
                'trend_title': trend.get('title'),
                'trend_category': trend.get('category'),
                'post_format': post_format,
            }

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return self._heuristic_parse_response(response, trend)

    def _heuristic_parse_response(self, response: str, trend: Dict[str, Any], post_format: str = "standard") -> Optional[Dict[str, Any]]:
        """Fallback parsing when the LLM doesn't follow the strict format."""
        import re

        text = (response or "").strip()
        if not text:
            return None

        # Extract hashtags and source URL if present
        hashtags = re.findall(r"#[A-Za-z0-9_]+", text)
        url_match = re.search(r"https?://\S+", text)
        source_url = url_match.group(0) if url_match else trend.get("url", "")

        return {
            "content": text,
            "hashtags": hashtags[:5],
            "source_url": source_url,
            "confidence": "Medium",
            "trend_id": trend.get("id"),
            "trend_title": trend.get("title"),
            "trend_category": trend.get("category"),
            "post_format": post_format,
        }

    def health_check(self) -> bool:
        """Check if LLM service is available"""
        try:
            if self.provider == "ollama":
                # Try to list models
                models = ollama.list()
                logger.info(f"Ollama health check: {len(models.get('models', []))} models available")
                return True
            else:
                logger.warning(f"Health check not implemented for provider: {self.provider}")
                return False

        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False

    def test_generation(self) -> bool:
        """Test LLM with a simple prompt"""
        try:
            logger.info("Running LLM test generation...")

            test_trend = {
                'title': 'Test: AI breakthrough in natural language processing',
                'description': 'Researchers announce new transformer model',
                'url': 'https://example.com/test',
                'category': 'ai',
                'relevance_score': 0.9,
                'metadata': {'feed_name': 'Test Source'}
            }

            result = self.generate_post(test_trend)

            if result and result.get('content'):
                logger.info("✓ Test generation successful")
                logger.info(f"Generated {len(result['content'])} characters")
                return True
            else:
                logger.error("✗ Test generation failed")
                return False

        except Exception as e:
            logger.error(f"Test generation error: {e}")
            return False
