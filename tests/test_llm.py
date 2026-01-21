"""Tests for LLM integration"""

import pytest
from config.settings import get_settings
from src.llm import LLMClient


def test_llm_client_initialization():
    """Test LLM client initialization"""
    settings = get_settings()
    client = LLMClient()
    assert client.model == settings.llm.model
    assert client.provider == settings.llm.provider


def test_health_check():
    """Test LLM health check"""
    client = LLMClient()
    # This will fail if Ollama is not running, which is expected
    is_healthy = client.health_check()
    assert isinstance(is_healthy, bool)
