"""Configuration settings for the AI thread generator."""
import json
import os
from typing import Dict, Optional
from dataclasses import dataclass, asdict

CONFIG_FILE = "config.json"

@dataclass
class AIConfig:
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000
    
    # Document processing settings
    chunk_size: int = 2000
    chunk_overlap: int = 100
    max_chunks: int = 10
    
    # Prompt templates
    prompts: Dict[str, str] = None
    
    def __post_init__(self):
        if self.prompts is None:
            self.prompts = {
                "title": "Summarize the following content into a thread title that would grab attention on social media: {content}",
                "thread": "Create a single engaging thread post from this content. Format it as a thread with line breaks between key points, use emojis where appropriate, and make it conversational: {content}"
            }
    
    def validate(self):
        """Validate configuration values."""
        if self.temperature < 0 or self.temperature > 1:
            raise ValueError("Temperature must be between 0 and 1")
        if self.max_tokens < 1:
            raise ValueError("Max tokens must be positive")
        if self.chunk_size < 1:
            raise ValueError("Chunk size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("Chunk overlap cannot be negative")
        if self.max_chunks < 1:
            raise ValueError("Max chunks must be positive")
        if not isinstance(self.prompts, dict) or "title" not in self.prompts or "thread" not in self.prompts:
            raise ValueError("Prompts must contain 'title' and 'thread' templates")

# Default configuration
default_config = AIConfig()

def save_config(config: AIConfig):
    """Save configuration to JSON file."""
    config.validate()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(asdict(config), f, indent=2)

def get_config() -> AIConfig:
    """Get the current AI configuration."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config_dict = json.load(f)
            config = AIConfig(**config_dict)
            config.validate()
            return config
    return default_config

def update_config(
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    max_chunks: Optional[int] = None,
    prompts: Optional[Dict[str, str]] = None
) -> AIConfig:
    """Update the AI configuration with new values."""
    config = get_config()
    
    if model_name is not None:
        config.model_name = model_name
    if temperature is not None:
        config.temperature = temperature
    if max_tokens is not None:
        config.max_tokens = max_tokens
    if chunk_size is not None:
        config.chunk_size = chunk_size
    if chunk_overlap is not None:
        config.chunk_overlap = chunk_overlap
    if max_chunks is not None:
        config.max_chunks = max_chunks
    if prompts is not None:
        config.prompts.update(prompts)
    
    save_config(config)
    return config
