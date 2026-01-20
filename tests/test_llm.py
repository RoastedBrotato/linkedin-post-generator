"""Tests for LLM integration"""

import pytest
from src.llm import LocalLLMClient


def test_llm_client_initialization():
    """Test LLM client initialization"""
    client = LocalLLMClient()
    assert client.model == "llama2"
    assert client.api_url == "http://localhost:11434"


def test_health_check():
    """Test LLM health check"""
    client = LocalLLMClient()
    # This will fail if Ollama is not running, which is expected
    is_healthy = client.health_check()
    assert isinstance(is_healthy, bool)
