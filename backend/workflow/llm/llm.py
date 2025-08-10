import copy
import os
import warnings
from functools import partial
from typing import Any, Callable, AsyncGenerator
from enum import Enum

from workflow.core.config import LLMConfig

# Suppress warnings during LiteLLM import
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm

from litellm import ChatCompletionMessageToolCall, ModelInfo, PromptTokensDetails
from litellm import Message as LiteLLMMessage
from litellm import acompletion as litellm_acompletion

from litellm.cost_calculator import completion_cost as litellm_completion_cost
from litellm.exceptions import (
    RateLimitError,
)
from litellm.types.utils import CostPerToken, ModelResponse, Usage
from litellm.utils import create_pretrained_tokenizer

from workflow.core.exceptions import LLMNoResponseError
from workflow.core.logger import usebase_logger as logger
from workflow.core.message import Message
from workflow.llm.debug_mixin import DebugMixin
from workflow.llm.fn_call_converter import (
    STOP_WORDS,
    convert_fncall_messages_to_non_fncall_messages,
    convert_non_fncall_messages_to_fncall_messages,
)
from workflow.llm.metrics import Metrics
from workflow.llm.retry_mixin import RetryMixin


__all__ = ['LLM']

# TODO(OBSERVABILITY): Observability is now set up in the LLM class initialization


class Model(Enum):
    """OpenAI models only"""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4 = "gpt-4"
    GPT_35_TURBO = "gpt-3.5-turbo"
    # GPT_5 = "gpt-5"  # Uncomment when GPT-5 is available


# tuple of exceptions to retry on
LLM_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
    RateLimitError,
    LLMNoResponseError,
)

# OpenAI models don't use cache prompts in the same way
CACHE_PROMPT_SUPPORTED_MODELS = []

# OpenAI models that support function calling
FUNCTION_CALLING_SUPPORTED_MODELS = [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4-turbo',
    'gpt-4',
    'gpt-3.5-turbo',
    'gpt-5',  # Future model
]

# OpenAI o1 models support reasoning effort
REASONING_EFFORT_SUPPORTED_MODELS = [
    'o1',
    'o1-mini',
    'o1-preview',
]

# OpenAI o1 models don't support stop words
MODELS_WITHOUT_STOP_WORDS = [
    'o1',
    'o1-mini',
    'o1-preview',
]


class LLM(RetryMixin, DebugMixin):
    """The LLM class represents a Language Model instance.

    Attributes:
        config: an LLMConfig object specifying the configuration of the LLM.
    """

    def __init__(
        self,
        config: LLMConfig,
        metrics: Metrics | None = None,
        retry_listener: Callable[[int, int], None] | None = None,
    ):
        """Initializes the LLM. If LLMConfig is passed, its values will be the fallback.

        Passing simple parameters always overrides config.

        Args:
            config: The LLM configuration.
            metrics: The metrics to use.
        """
        # Setup observability with Langfuse
        litellm.success_callback.append("langfuse")
        litellm.failure_callback.append("langfuse")

        self._tried_model_info = False
        self.metrics: Metrics = (
            metrics
            if metrics is not None
            else Metrics(model_name=Model.GPT_4O.value)
        )
        self.cost_metric_supported: bool = True
        self.config: LLMConfig = copy.deepcopy(config)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model_info: ModelInfo | None = None
        self.retry_listener = retry_listener
        if self.config.log_completions:
            if self.config.log_completions_folder is None:
                raise RuntimeError(
                    'log_completions_folder is required when log_completions is enabled'
                )
            os.makedirs(self.config.log_completions_folder, exist_ok=True)

        # which is used in partial function
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')

        if self.is_caching_prompt_active():
            logger.debug('LLM: caching prompt enabled')
        if self.is_function_calling_active():
            logger.debug('LLM: model supports function calling')

        # if using a custom tokenizer, make sure it's loaded and accessible in the format expected by litellm
        if self.config.custom_tokenizer is not None:
            self.tokenizer = create_pretrained_tokenizer(self.config.custom_tokenizer)
        else:
            self.tokenizer = None

        self._completion = partial(
            litellm_acompletion,
            base_url=self.config.base_url,
            api_version=self.config.api_version,
            custom_llm_provider=self.config.custom_llm_provider,
            timeout=self.config.timeout,
            drop_params=self.config.drop_params,
            seed=self.config.seed,
        )

        self._completion_unwrapped = self._completion

        async def _completion_generator(
            self, *args, stream: bool, **kwargs
        ) -> AsyncGenerator[Any, None]:
            """
            CORE LOOP:
            1) Call self._completion_unwrapped(*args, **call_kwargs)
            2) Yield chunks (if stream) or the full response (if not)
            3) If finish_reason == 'length', massage messages + kwargs and loop
            """

            # work on a deep copy so we never mutate the caller's list
            messages = copy.deepcopy(kwargs["messages"])
            # make a mutable copy of all other kwargs for successive calls
            call_kwargs = copy.deepcopy(kwargs)
            call_kwargs["stream"] = stream
            call_kwargs["messages"] = messages

            full_text = ""
            reasoning_acc = ""
            thinking_signature = ""

            while True:
                try:
                    resp = await self._completion_unwrapped(*args, **call_kwargs)

                    if stream:
                        async for chunk in resp:
                            # 2a) STREAMING: gather partials
                            tb = getattr(
                                chunk.choices[0].delta, "thinking_blocks", None
                            )
                            if tb:
                                reasoning_acc += tb[0]["thinking"]
                                thinking_signature = tb[0]['signature']

                            content = chunk.choices[0].delta.content or ""
                            full_text += content

                            yield chunk

                        stop_reason = chunk.choices[0].finish_reason

                    else:
                        # 2b) NON‑STREAMING: single-shot resp
                        choice = resp.choices[0]
                        content = choice.message.content or ""
                        full_text += content

                        tb = getattr(choice.message, "thinking_blocks", None)
                        reasoning_acc = tb[0]["thinking"] if tb else reasoning_acc
                        thinking_signature = tb[0]['signature'] if tb else thinking_signature

                        # overwrite the message with the aggregated text
                        choice.message.content = full_text

                        yield resp
                        stop_reason = choice.finish_reason

                    # 3) if we filled up max_tokens, continue
                    if stop_reason != "length":
                        break

                    assistant_content = [{"type": "thinking", "thinking": reasoning_acc, "signature": thinking_signature}] if reasoning_acc else []
                    assistant_content.append({"type": "text", "text": full_text})

                    if messages[-1]['role'] != "assistant":
                        messages.append(
                            {"role": "assistant", "content": assistant_content}
                        )
                    else:
                        messages[-1]['content'] = assistant_content
                except Exception as e:
                    logger.error(f'Error during completion: {e}')
                    raise e

        async def completion_wrapper(
            *args,
            reasoning_effort: str | None = None,
            stream: bool = False,
            model: Model = Model.sonnet_3_7,
            **kwargs,
        ):
            kwargs['model'] = model.value
            kwargs['api_key'] = (
                self.anthropic_api_key
                if model == Model.sonnet_3_7
                else self.openai_api_key
            )
            if model == Model.sonnet_3_7:
                kwargs['max_completion_tokens'] = self.config.max_output_tokens

            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

            if stream:
                return _completion_generator(self, *args, stream=True, **kwargs)
            else:
                async for resp in _completion_generator(
                    self, *args, stream=False, **kwargs
                ):
                    continue
                return resp

        self._completion = completion_wrapper

    @property
    def completion(self) -> Callable[..., Any]:
        """
        LiteLLM completion (returns one aggregated Response).

        - reason: bool, if true, will return the reasoning blocks
        - stream: bool, if true, will stream the response
        """
        return self._completion

    def is_caching_prompt_active(self) -> bool:
        """Check if prompt caching is supported and enabled for current model.

        Returns:
            boolean: True if prompt caching is supported and enabled for the given model.
        """
        return True

    def is_function_calling_active(self) -> bool:
        """Returns whether function calling is supported and enabled for this LLM instance.

        The result is cached during initialization for performance.
        """
        return True

    def _post_completion(self, response: ModelResponse) -> float:
        """Post-process the completion response.

        Logs the cost and usage stats of the completion call.
        """
        try:
            cur_cost = self._completion_cost(response)
        except Exception:
            cur_cost = 0

        stats = ''
        if self.cost_metric_supported:
            # keep track of the cost
            stats = 'Cost: %.2f USD | Accumulated Cost: %.2f USD\n' % (
                cur_cost,
                self.metrics.accumulated_cost,
            )

        # Add latency to stats if available
        if self.metrics.response_latencies:
            latest_latency = self.metrics.response_latencies[-1]
            stats += 'Response Latency: %.3f seconds\n' % latest_latency.latency

        usage: Usage | None = response.get('usage')
        response_id = response.get('id', 'unknown')

        if usage:
            # keep track of the input and output tokens
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)

            if prompt_tokens:
                stats += 'Input tokens: ' + str(prompt_tokens)

            if completion_tokens:
                stats += (
                    (' | ' if prompt_tokens else '')
                    + 'Output tokens: '
                    + str(completion_tokens)
                    + '\n'
                )

            # read the prompt cache hit, if any
            prompt_tokens_details: PromptTokensDetails = usage.get(
                'prompt_tokens_details'
            )
            cache_hit_tokens = (
                prompt_tokens_details.cached_tokens
                if prompt_tokens_details and prompt_tokens_details.cached_tokens
                else 0
            )
            if cache_hit_tokens:
                stats += 'Input tokens (cache hit): ' + str(cache_hit_tokens) + '\n'

            # For Anthropic, the cache writes have a different cost than regular input tokens
            # but litellm doesn't separate them in the usage stats
            # we can read it from the provider-specific extra field
            model_extra = usage.get('model_extra', {})
            cache_write_tokens = model_extra.get('cache_creation_input_tokens', 0)
            if cache_write_tokens:
                stats += 'Input tokens (cache write): ' + str(cache_write_tokens) + '\n'

            # Record in metrics
            # We'll treat cache_hit_tokens as "cache read" and cache_write_tokens as "cache write"
            self.metrics.add_token_usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_read_tokens=cache_hit_tokens,
                cache_write_tokens=cache_write_tokens,
                response_id=response_id,
            )

        # log the stats
        if stats:
            logger.debug(stats)

        return cur_cost

    def get_token_count(self, messages: list[dict] | list[Message]) -> int:
        """Get the number of tokens in a list of messages. Use dicts for better token counting.

        Args:
            messages (list): A list of messages, either as a list of dicts or as a list of Message objects.
        Returns:
            int: The number of tokens.
        """
        # attempt to convert Message objects to dicts, litellm expects dicts
        if (
            isinstance(messages, list)
            and len(messages) > 0
            and isinstance(messages[0], Message)
        ):
            logger.info(
                'Message objects now include serialized tool calls in token counting'
            )
            messages = self.format_messages_for_llm(messages)  # type: ignore

        # try to get the token count with the default litellm tokenizers
        # or the custom tokenizer if set for this LLM configuration
        try:
            return int(
                litellm.token_counter(
                    model=self.config.model,
                    messages=messages,
                    custom_tokenizer=self.tokenizer,
                )
            )
        except Exception as e:
            # limit logspam in case token count is not supported
            logger.error(
                f'Error getting token count for\n model {self.config.model}\n{e}'
                + (
                    f'\ncustom_tokenizer: {self.config.custom_tokenizer}'
                    if self.config.custom_tokenizer is not None
                    else ''
                )
            )
            return 0

    def _is_local(self) -> bool:
        """Determines if the system is using a locally running LLM.

        Returns:
            boolean: True if executing a local model.
        """
        if self.config.base_url is not None:
            for substring in ['localhost', '127.0.0.1' '0.0.0.0']:
                if substring in self.config.base_url:
                    return True
        elif self.config.model is not None:
            if self.config.model.startswith('ollama'):
                return True
        return False

    def _completion_cost(self, response: Any) -> float:
        """Calculate completion cost and update metrics with running total.

        Calculate the cost of a completion response based on the model. Local models are treated as free.
        Add the current cost into total cost in metrics.

        Args:
            response: A response from a model invocation.

        Returns:
            number: The cost of the response.
        """
        if not self.cost_metric_supported:
            return 0.0

        extra_kwargs = {}
        if (
            self.config.input_cost_per_token is not None
            and self.config.output_cost_per_token is not None
        ):
            cost_per_token = CostPerToken(
                input_cost_per_token=self.config.input_cost_per_token,
                output_cost_per_token=self.config.output_cost_per_token,
            )
            logger.debug(f'Using custom cost per token: {cost_per_token}')
            extra_kwargs['custom_cost_per_token'] = cost_per_token

        # try directly get response_cost from response
        _hidden_params = getattr(response, '_hidden_params', {})
        cost = _hidden_params.get('additional_headers', {}).get(
            'llm_provider-x-litellm-response-cost', None
        )
        if cost is not None:
            cost = float(cost)
            logger.debug(f'Got response_cost from response: {cost}')

        try:
            if cost is None:
                try:
                    cost = litellm_completion_cost(
                        completion_response=response, **extra_kwargs
                    )
                except Exception as e:
                    logger.error(f'Error getting cost from litellm: {e}')

            if cost is None:
                _model_name = '/'.join(self.config.model.split('/')[1:])
                cost = litellm_completion_cost(
                    completion_response=response, model=_model_name, **extra_kwargs
                )
                logger.debug(
                    f'Using fallback model name {_model_name} to get cost: {cost}'
                )
            self.metrics.add_cost(float(cost))
            return float(cost)
        except Exception:
            self.cost_metric_supported = False
            logger.debug('Cost calculation not supported for this model.')
        return 0.0

    def __str__(self) -> str:
        if self.config.api_version:
            return f'LLM(model={self.config.model}, api_version={self.config.api_version}, base_url={self.config.base_url})'
        elif self.config.base_url:
            return f'LLM(model={self.config.model}, base_url={self.config.base_url})'
        return f'LLM(model={self.config.model})'

    def __repr__(self) -> str:
        return str(self)

    def reset(self) -> None:
        self.metrics.reset()

    def format_messages_for_llm(self, messages: Message | list[Message]) -> list[dict]:
        if isinstance(messages, Message):
            messages = [messages]

        # set flags to know how to serialize the messages
        # for message in messages:
        #     message.cache_enabled = self.is_caching_prompt_active()
        #     message.function_calling_enabled = self.is_function_calling_active()
        last_msg = messages[-1].serialize_for_llm()
        if isinstance(messages[-1].content, str):
            last_msg['content'] = [
                {
                    "type": "text",
                    "text": last_msg['content'],
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            if last_msg['content'][-1].get('type') == 'text':
                last_msg['content'][-1]['cache_control'] = {"type": "ephemeral"}

        # let pydantic handle the serialization
        return [message.serialize_for_llm() for message in messages[:-1]] + [last_msg]
