"""Local LLM integration module"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class LocalLLMClient:
    """Client for interacting with local LLM (Ollama, vLLM, etc.)"""
    
    def __init__(self, api_url: str = None, model: str = None):
        self.api_url = api_url or os.getenv("LLM_API_URL", "http://localhost:11434")
        self.model = model or os.getenv("LLM_MODEL", "llama2")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", 0.7))
    
    def generate(self, prompt: str) -> Optional[str]:
        """Generate text using local LLM"""
        try:
            logger.info(f"Generating with model: {self.model}")
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("response")
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return None
    
    def health_check(self) -> bool:
        """Check if LLM service is available"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False
