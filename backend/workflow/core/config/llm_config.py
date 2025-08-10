from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, SecretStr, ValidationError

from workflow.core.logger import LOG_DIR
from workflow.core.logger import usebase_logger as logger


class LLMConfig(BaseModel):
    """Simplified configuration for OpenAI LLM models only.

    Attributes:
        model: The OpenAI model to use (default: gpt-4o, supports gpt-5 when available).
        api_key: The OpenAI API key.
        temperature: The temperature for the API (0.0 for deterministic, up to 2.0).
        top_p: The top p for the API.
        max_output_tokens: The maximum number of output tokens.
        num_retries: The number of retries to attempt.
        retry_min_wait: The minimum time to wait between retries, in seconds.
        retry_max_wait: The maximum time to wait between retries, in seconds.
        timeout: The timeout for the API call in seconds.
        max_message_chars: The max number of characters in the content sent to the LLM.
        log_completions: Whether to log LLM completions.
        log_completions_folder: The folder to log LLM completions to.
        seed: The seed for deterministic outputs.
    """

    # OpenAI specific settings
    model: str = Field(default='gpt-4o', description="OpenAI model name (gpt-4o, gpt-5, etc.)")
    api_key: SecretStr | None = Field(default=None, description="OpenAI API key")
    
    # Model parameters
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_output_tokens: int | None = Field(default=4096)
    seed: int | None = Field(default=None)
    
    # Retry and timeout settings
    num_retries: int = Field(default=4)
    retry_min_wait: int = Field(default=5)
    retry_max_wait: int = Field(default=30)
    timeout: int | None = Field(default=60)
    
    # Content limits
    max_message_chars: int = Field(default=30_000)
    
    # Logging
    log_completions: bool = Field(default=False)
    log_completions_folder: str = Field(default=os.path.join(LOG_DIR, 'completions'))
    
    # Vision capabilities (for multimodal models like gpt-4o)
    disable_vision: bool = Field(default=False)
    
    # Tool calling
    native_tool_calling: bool = Field(default=True)

    model_config = {'extra': 'forbid'}

    @classmethod
    def from_toml_section(cls, data: dict) -> dict[str, LLMConfig]:
        """
        Create a mapping of LLMConfig instances from a toml dictionary.
        Simplified to only support OpenAI models.
        
        Returns:
            dict[str, LLMConfig]: A mapping where the key "llm" corresponds to the configuration.
        """
        llm_mapping: dict[str, LLMConfig] = {}
        
        try:
            # Only create a single default config for OpenAI
            config = cls.model_validate(data)
            llm_mapping['llm'] = config
        except ValidationError:
            logger.warning('Cannot parse [llm] config from toml. Using defaults.')
            llm_mapping['llm'] = cls()
        
        return llm_mapping

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook to validate OpenAI configuration."""
        super().model_post_init(__context)
        
        # Validate that we're using an OpenAI model
        valid_models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo', 'gpt-5']
        if not any(self.model.startswith(prefix) for prefix in valid_models):
            logger.warning(f'Model {self.model} may not be a valid OpenAI model. Expected one of: {valid_models}')