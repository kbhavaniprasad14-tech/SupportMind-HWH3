import os
from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()


class GroqProvider:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError('Groq is not configured')

        try:
            response = httpx.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt},
                    ],
                    'temperature': 0.3,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            return payload['choices'][0]['message']['content']
        except Exception as exc:
            raise RuntimeError('Groq generation failed') from exc
