"""
Post template definitions and LLM prompts for different post formats.

Supports various LinkedIn post styles to keep content diverse and engaging.
"""

from typing import Dict, List, Any


# Post format definitions
POST_FORMATS = {
    "standard": {
        "name": "Standard Post",
        "description": "Traditional informative post about the trend",
        "emoji": "📝",
        "example": "Just came across this interesting development in AI...",
    },
    "insight": {
        "name": "Insight & Analysis",
        "description": "Deep dive with insights and personal perspective",
        "emoji": "💡",
        "example": "Here's what this trend means for the future of tech...",
    },
    "story": {
        "name": "Personal Story",
        "description": "Share a related personal experience or anecdote",
        "emoji": "📖",
        "example": "This reminds me of when we first encountered...",
    },
    "question": {
        "name": "Thought-Provoking Question",
        "description": "Ask your network a question about the trend",
        "emoji": "❓",
        "example": "What's your take on this development?",
    },
    "hot_take": {
        "name": "Hot Take",
        "description": "Bold opinion or contrarian perspective",
        "emoji": "🔥",
        "example": "Unpopular opinion: This trend is overrated...",
    },
    "educational": {
        "name": "Educational/Tutorial",
        "description": "Teach something related to the trend",
        "emoji": "🎓",
        "example": "Here's what you need to know about...",
    },
    "list": {
        "name": "Listicle",
        "description": "Numbered list format (3-5 key points)",
        "emoji": "📋",
        "example": "5 reasons why this matters for developers:",
    },
}


def get_post_template_prompt(format_type: str, trend: Dict[str, Any]) -> str:
    """
    Get the LLM prompt for a specific post format.

    Args:
        format_type: The post format type (standard, insight, story, etc.)
        trend: Trend data dictionary

    Returns:
        Formatted prompt string for the LLM
    """

    base_context = f"""
You are writing a LinkedIn post about the following trend:

Title: {trend.get('title', '')}
Description: {trend.get('description', '')}
Source: {trend.get('source_name', '')}
URL: {trend.get('url', '')}

Your post should be:
- Professional yet conversational
- Engaging and authentic
- 150-250 words (LinkedIn optimal length)
- Include 2-3 relevant hashtags at the end
- Written in first person
"""

    format_prompts = {
        "standard": base_context + """
Write a standard LinkedIn post that:
- Introduces the trend clearly
- Explains why it's important or interesting
- Shares your perspective on it
- Ends with a call to action or question for engagement

Keep it informative and balanced. Don't use emojis in the main text.
""",

        "insight": base_context + """
Write an insightful analysis post that:
- Goes beyond surface-level observations
- Connects this trend to broader patterns or implications
- Shares a unique perspective or prediction
- Demonstrates deep understanding of the topic
- References your experience or expertise where relevant

This should position you as a thought leader. Use analytical language.
""",

        "story": base_context + """
Write a personal story post that:
- Opens with "This reminds me of..." or "I remember when..."
- Shares a relevant personal experience related to this trend
- Makes it relatable and human
- Connects the story back to the trend
- Ends with a reflection or lesson learned

Make it authentic and vulnerable. Use storytelling techniques.
""",

        "question": base_context + """
Write a thought-provoking question post that:
- Opens with a brief context about the trend (1-2 sentences)
- Poses a genuine, interesting question to your network
- The question should encourage diverse responses
- Optionally shares your initial thoughts
- Invites people to comment with their perspectives

The goal is to spark conversation. End with the question.
""",

        "hot_take": base_context + """
Write a bold opinion post that:
- Opens with "Unpopular opinion:" or "Hot take:" or "Controversial, but..."
- States a contrarian or strong perspective on the trend
- Backs it up with reasoning (not just being contrarian for clicks)
- Acknowledges counterarguments briefly
- Ends with "What do you think?" or similar engagement hook

Be bold but not inflammatory. Show conviction while staying professional.
""",

        "educational": base_context + """
Write an educational post that:
- Opens with "Here's what you need to know about..." or "Let me break down..."
- Teaches something valuable related to the trend
- Uses simple, clear explanations
- Breaks down complex concepts
- Ends with a key takeaway or next step

Make it accessible to someone new to the topic. Use teaching language.
""",

        "list": base_context + """
Write a listicle post that:
- Opens with a hook like "5 things about [trend]:" or "Here are 3 reasons why [trend] matters:"
- Lists 3-5 specific, actionable, or interesting points
- Each point should be 1-2 sentences
- Use numbers (1., 2., 3., etc.) or bullet points
- Ends with a concluding thought or question

Keep it scannable and punchy. Each point should stand on its own.
""",
    }

    return format_prompts.get(format_type, format_prompts["standard"])


def get_all_format_options() -> List[Dict[str, str]]:
    """
    Get all available post formats for UI display.

    Returns:
        List of format dictionaries with id, name, description, emoji
    """
    return [
        {
            "id": format_id,
            "name": format_data["name"],
            "description": format_data["description"],
            "emoji": format_data["emoji"],
            "example": format_data["example"],
        }
        for format_id, format_data in POST_FORMATS.items()
    ]


def get_format_name(format_id: str) -> str:
    """Get the display name for a format ID."""
    return POST_FORMATS.get(format_id, {}).get("name", "Standard Post")
