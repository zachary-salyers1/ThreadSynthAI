"""Configuration settings for the AI thread generator."""
from typing import Dict
from dataclasses import dataclass

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

# Default configuration
default_config = AIConfig()

def get_config() -> AIConfig:
    """Get the current AI configuration."""
    return default_config

def update_config(
    model_name: str = None,
    temperature: float = None,
    max_tokens: int = None,
    chunk_size: int = None,
    chunk_overlap: int = None,
    max_chunks: int = None,
    prompts: Dict[str, str] = None
) -> AIConfig:
    """Update the AI configuration with new values."""
    global default_config
    
    if model_name is not None:
        default_config.model_name = model_name
    if temperature is not None:
        default_config.temperature = temperature
    if max_tokens is not None:
        default_config.max_tokens = max_tokens
    if chunk_size is not None:
        default_config.chunk_size = chunk_size
    if chunk_overlap is not None:
        default_config.chunk_overlap = chunk_overlap
    if max_chunks is not None:
        default_config.max_chunks = max_chunks
    if prompts is not None:
        default_config.prompts.update(prompts)
    
    return default_config
