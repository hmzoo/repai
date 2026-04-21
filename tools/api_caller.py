"""
API caller tool - makes HTTP requests to external APIs
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin


class APIClient:
    """Generic API client for making HTTP requests"""
    
    def __init__(self, base_url: str, headers: Optional[Dict] = None, timeout: int = 30):
        self.base_url = base_url
        self.headers = headers or {}
        self.timeout = timeout
    
    def call(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an API call
        
        Args:
            endpoint: API endpoint (relative to base_url)
            method: HTTP method (GET, POST, etc.)
            data: Request body
            params: Query parameters
            **kwargs: Additional requests parameters
        
        Returns:
            {
                "success": bool,
                "status_code": int,
                "data": dict | None,
                "error": str | None,
                "execution_time": float
            }
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        start_time = time.time()
        
        try:
            headers = {**self.headers, **kwargs.get('headers', {})}
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout,
                **{k: v for k, v in kwargs.items() if k != 'headers'}
            )
            
            execution_time = time.time() - start_time
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "data": response_data,
                "error": None if response.ok else f"HTTP {response.status_code}",
                "execution_time": execution_time
            }
        
        except requests.exceptions.Timeout:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": f"Request timeout after {self.timeout}s",
                "execution_time": execution_time
            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": str(e),
                "execution_time": execution_time
            }


class OpenAIClient(APIClient):
    """OpenAI API client"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", timeout: int = 30):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        super().__init__(
            base_url="https://api.openai.com/v1",
            headers=headers,
            timeout=timeout
        )
        self.model = model
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call OpenAI chat completion
        
        Args:
            messages: List of messages
            temperature: Model temperature
            max_tokens: Max tokens in response
        
        Returns:
            API response with structure:
            {
                "success": bool,
                "data": {
                    "choices": [
                        {"message": {"content": str}}
                    ],
                    ...
                }
            }
        """
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        return self.call("chat/completions", method="POST", data=data)
    
    def get_response(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """
        Convenience method to get just the response text
        """
        result = self.chat_completion(messages, **kwargs)
        if result['success'] and result['data'].get('choices'):
            return result['data']['choices'][0]['message']['content']
        return None


class GoogleGeminiClient(APIClient):
    """Google Gemini API client"""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: int = 30):
        super().__init__(
            base_url="https://generativelanguage.googleapis.com/v1beta",
            timeout=timeout
        )
        self.api_key = api_key
        self.model = model

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call Google Gemini generateContent

        Args:
            messages: List of {"role": "user"|"assistant", "content": str}
            temperature: Model temperature
            max_tokens: Max tokens in response

        Returns:
            Normalized response matching OpenAIClient format:
            {
                "success": bool,
                "data": {
                    "choices": [{"message": {"content": str}}]
                }
            }
        """
        # Convert messages to Gemini "contents" format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] != "assistant" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        thinking_budget = kwargs.pop("thinking_budget", 0)
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "thinkingConfig": {
                    "thinkingBudget": thinking_budget,
                },
            }
        }

        endpoint = f"models/{self.model}:generateContent"
        raw = self.call(endpoint, method="POST", data=data,
                        params={"key": self.api_key})

        # Normalize response to same shape as OpenAIClient
        if raw["success"]:
            try:
                parts = raw["data"]["candidates"][0]["content"].get("parts", [])
                text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
                text = "".join(text_parts).strip()
                if not text:
                    raise KeyError("No text content in Gemini response parts")
                raw["data"] = {"choices": [{"message": {"content": text}}]}
            except (KeyError, IndexError):
                raw["success"] = False
                raw["error"] = "Unexpected Gemini response structure"

        return raw

    def get_response(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """
        Convenience method to get just the response text
        """
        result = self.chat_completion(messages, **kwargs)
        if result["success"] and result["data"].get("choices"):
            return result["data"]["choices"][0]["message"]["content"]
        return None


def create_llm_client(provider: str, api_key: str, model: str = None, timeout: int = 30):
    """
    Factory: creates the right LLM client based on provider name.

    Args:
        provider: "google", "openai", or "anthropic"
        api_key:  API key for the provider
        model:    Optional model override
        timeout:  HTTP timeout in seconds

    Returns:
        An LLM client with a .get_response(messages) method
    """
    if provider == "google":
        return GoogleGeminiClient(api_key, model=model or "gemini-2.5-flash", timeout=timeout)
    if provider == "openai":
        return OpenAIClient(api_key, model=model or "gpt-4", timeout=timeout)
    raise ValueError(f"Unsupported LLM provider: '{provider}'. Use 'google' or 'openai'.")
