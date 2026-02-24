#!/usr/bin/env python3
"""
PolyClaw Model Providers

Support for multiple LLM providers including local models.
Inspired by OpenClaw's model-agnostic architecture.

Supported providers:
- OpenAI (GPT-4, GPT-4o, etc.)
- Anthropic (Claude)
- Ollama (local models)
- vLLM (local inference server)
- Google (Gemini)
- Groq (fast inference)
"""

import os
import json
import logging
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator
from dataclasses import dataclass, field

logger = logging.getLogger("polyclaw.models")

POLYCLAW_DIR = Path.home() / ".polyclaw"
MODELS_CONFIG = POLYCLAW_DIR / "models.json"


@dataclass
class ModelConfig:
    """Model configuration."""
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    
    def to_dict(self) -> Dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }


@dataclass
class Message:
    """Chat message."""
    role: str  # "system", "user", "assistant"
    content: str
    
    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


@dataclass
class CompletionResponse:
    """LLM completion response."""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    raw_response: Dict = field(default_factory=dict)


class ModelProvider(ABC):
    """Abstract base class for model providers."""
    
    @abstractmethod
    def complete(self, messages: List[Message], **kwargs) -> CompletionResponse:
        """Generate a completion."""
        pass
    
    @abstractmethod
    def stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        """Stream a completion."""
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models."""
        pass


class OpenAIProvider(ModelProvider):
    """OpenAI API provider."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = config.base_url or "https://api.openai.com/v1"
    
    def complete(self, messages: List[Message], **kwargs) -> CompletionResponse:
        """Generate completion using OpenAI API."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[m.to_dict() for m in messages],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens)
            )
            
            return CompletionResponse(
                content=response.choices[0].message.content,
                model=self.config.model,
                provider="openai",
                tokens_used=response.usage.total_tokens if response.usage else 0,
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}")
            raise
    
    def stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        """Stream completion from OpenAI."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            
            stream = client.chat.completions.create(
                model=self.config.model,
                messages=[m.to_dict() for m in messages],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            raise
    
    def list_models(self) -> List[str]:
        """List available OpenAI models."""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo"
        ]


class AnthropicProvider(ModelProvider):
    """Anthropic API provider."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = config.base_url or "https://api.anthropic.com"
    
    def complete(self, messages: List[Message], **kwargs) -> CompletionResponse:
        """Generate completion using Anthropic API."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Extract system message
            system = ""
            chat_messages = []
            for m in messages:
                if m.role == "system":
                    system = m.content
                else:
                    chat_messages.append(m.to_dict())
            
            response = client.messages.create(
                model=self.config.model,
                system=system,
                messages=chat_messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature)
            )
            
            return CompletionResponse(
                content=response.content[0].text,
                model=self.config.model,
                provider="anthropic",
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason
            )
        except Exception as e:
            logger.error(f"Anthropic completion failed: {e}")
            raise
    
    def stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        """Stream completion from Anthropic."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            system = ""
            chat_messages = []
            for m in messages:
                if m.role == "system":
                    system = m.content
                else:
                    chat_messages.append(m.to_dict())
            
            with client.messages.stream(
                model=self.config.model,
                system=system,
                messages=chat_messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens)
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            raise
    
    def list_models(self) -> List[str]:
        """List available Anthropic models."""
        return [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229"
        ]


class OllamaProvider(ModelProvider):
    """
    Ollama local model provider.
    
    Run models locally with zero API costs.
    """
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.base_url = config.base_url or "http://localhost:11434"
    
    def complete(self, messages: List[Message], **kwargs) -> CompletionResponse:
        """Generate completion using Ollama."""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": [m.to_dict() for m in messages],
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens)
                    }
                },
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            return CompletionResponse(
                content=data["message"]["content"],
                model=self.config.model,
                provider="ollama",
                tokens_used=data.get("eval_count", 0),
                finish_reason="stop"
            )
        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            raise
    
    def stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        """Stream completion from Ollama."""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": [m.to_dict() for m in messages],
                    "stream": True,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature)
                    }
                },
                stream=True,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise
    
    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except:
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama library."""
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True
            )
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    logger.info(f"Pulling {model_name}: {status}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False
    
    @staticmethod
    def check_running() -> bool:
        """Check if Ollama is running."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


class GroqProvider(ModelProvider):
    """
    Groq fast inference provider.
    
    Very fast inference for supported models.
    """
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.api_key = config.api_key or os.environ.get("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1"
    
    def complete(self, messages: List[Message], **kwargs) -> CompletionResponse:
        """Generate completion using Groq."""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.model,
                    "messages": [m.to_dict() for m in messages],
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens)
                },
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            return CompletionResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.config.model,
                provider="groq",
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=data["choices"][0].get("finish_reason", "stop")
            )
        except Exception as e:
            logger.error(f"Groq completion failed: {e}")
            raise
    
    def stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        """Stream completion from Groq."""
        # Groq uses OpenAI-compatible API
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.model,
                    "messages": [m.to_dict() for m in messages],
                    "stream": True
                },
                stream=True,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str != "[DONE]":
                            data = json.loads(data_str)
                            content = data["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
        except Exception as e:
            logger.error(f"Groq streaming failed: {e}")
            raise
    
    def list_models(self) -> List[str]:
        """List available Groq models."""
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]


class ModelManager:
    """
    Manages multiple model providers with failover support.
    """
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "groq": GroqProvider
    }
    
    def __init__(self):
        self.current_config: Optional[ModelConfig] = None
        self.current_provider: Optional[ModelProvider] = None
        self.fallback_configs: List[ModelConfig] = []
        
        self._load_config()
    
    def _load_config(self):
        """Load model configuration."""
        if MODELS_CONFIG.exists():
            try:
                with open(MODELS_CONFIG) as f:
                    data = json.load(f)
                
                if "default" in data:
                    self.current_config = ModelConfig(**data["default"])
                    self._init_provider()
                
                if "fallbacks" in data:
                    self.fallback_configs = [ModelConfig(**c) for c in data["fallbacks"]]
            except Exception as e:
                logger.error(f"Failed to load model config: {e}")
        
        # Default to OpenAI if no config
        if not self.current_config:
            self.current_config = ModelConfig(provider="openai", model="gpt-4o-mini")
            self._init_provider()
    
    def _save_config(self):
        """Save model configuration."""
        POLYCLAW_DIR.mkdir(parents=True, exist_ok=True)
        
        data = {
            "default": self.current_config.to_dict() if self.current_config else None,
            "fallbacks": [c.to_dict() for c in self.fallback_configs]
        }
        
        with open(MODELS_CONFIG, "w") as f:
            json.dump(data, f, indent=2)
    
    def _init_provider(self):
        """Initialize the current provider."""
        if not self.current_config:
            return
        
        provider_class = self.PROVIDERS.get(self.current_config.provider)
        if provider_class:
            self.current_provider = provider_class(self.current_config)
    
    def set_model(self, provider: str, model: str, **kwargs):
        """Set the current model."""
        self.current_config = ModelConfig(provider=provider, model=model, **kwargs)
        self._init_provider()
        self._save_config()
    
    def complete(self, messages: List[Message], **kwargs) -> CompletionResponse:
        """Generate completion with fallback support."""
        if not self.current_provider:
            raise RuntimeError("No model provider configured")
        
        try:
            return self.current_provider.complete(messages, **kwargs)
        except Exception as e:
            logger.warning(f"Primary model failed: {e}")
            
            # Try fallbacks
            for fallback_config in self.fallback_configs:
                try:
                    provider_class = self.PROVIDERS.get(fallback_config.provider)
                    if provider_class:
                        provider = provider_class(fallback_config)
                        return provider.complete(messages, **kwargs)
                except Exception as fe:
                    logger.warning(f"Fallback {fallback_config.provider} failed: {fe}")
            
            raise
    
    def stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        """Stream completion."""
        if not self.current_provider:
            raise RuntimeError("No model provider configured")
        
        return self.current_provider.stream(messages, **kwargs)
    
    def list_all_models(self) -> Dict[str, List[str]]:
        """List models from all providers."""
        models = {}
        
        for name, provider_class in self.PROVIDERS.items():
            try:
                config = ModelConfig(provider=name, model="")
                provider = provider_class(config)
                models[name] = provider.list_models()
            except:
                models[name] = []
        
        return models
    
    def get_status(self) -> Dict:
        """Get model manager status."""
        return {
            "current": self.current_config.to_dict() if self.current_config else None,
            "ollama_running": OllamaProvider.check_running(),
            "fallbacks": len(self.fallback_configs)
        }


# Global instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get or create the global model manager."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


# Convenience functions
def chat(prompt: str, system: str = None, **kwargs) -> str:
    """Simple chat completion."""
    messages = []
    if system:
        messages.append(Message(role="system", content=system))
    messages.append(Message(role="user", content=prompt))
    
    response = get_model_manager().complete(messages, **kwargs)
    return response.content


def stream_chat(prompt: str, system: str = None, **kwargs) -> Generator[str, None, None]:
    """Simple streaming chat."""
    messages = []
    if system:
        messages.append(Message(role="system", content=system))
    messages.append(Message(role="user", content=prompt))
    
    return get_model_manager().stream(messages, **kwargs)


OLLAMA_SETUP = """
# Ollama Setup for Local Models

Run LLMs locally with zero API costs!

## Install Ollama

### macOS
```bash
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Start Ollama
```bash
ollama serve
```

## Pull Models
```bash
# Recommended for prediction market analysis
ollama pull llama3.2:3b      # Fast, good for simple tasks
ollama pull llama3.1:8b      # Balanced
ollama pull mistral          # Great reasoning
ollama pull codellama        # For code generation
ollama pull phi3             # Small and fast
```

## Configure PolyClaw

Add to ~/.polyclaw/models.json:
```json
{
  "default": {
    "provider": "ollama",
    "model": "llama3.1:8b",
    "temperature": 0.7
  },
  "fallbacks": [
    {
      "provider": "openai",
      "model": "gpt-4o-mini"
    }
  ]
}
```

Or use CLI:
```bash
polyclaw model set ollama llama3.1:8b
```

## Cost Savings

| Provider | Cost per 1M tokens |
|----------|-------------------|
| GPT-4o   | ~$10              |
| Claude   | ~$15              |
| Ollama   | $0 (local)        |

For prediction market analysis (high volume queries), 
Ollama can save hundreds of dollars per month!
"""
