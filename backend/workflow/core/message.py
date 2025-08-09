from enum import Enum
from typing import Any, Literal

from litellm import ChatCompletionMessageToolCall
from pydantic import BaseModel, Field, model_serializer, model_validator, ConfigDict


class ContentType(Enum):
    TEXT = 'text'
    IMAGE_URL = 'image_url'
    THINKING = 'thinking'


class Content(BaseModel):
    type: str
    cache_prompt: bool = False

    @model_serializer(mode='plain')
    def serialize_model(
        self,
    ) -> dict[str, str | dict[str, str]] | list[dict[str, str | dict[str, str]]]:
        raise NotImplementedError('Subclasses should implement this method.')


class TextContent(Content):
    type: str = ContentType.TEXT.value
    text: str

    @model_serializer(mode='plain')
    def serialize_model(self) -> dict[str, str | dict[str, str]]:
        data: dict[str, str | dict[str, str]] = {
            'type': self.type,
            'text': self.text,
        }

        return data


class ImageContent(Content):
    type: str = ContentType.IMAGE_URL.value
    image_urls: list[str]

    @model_serializer(mode='plain')
    def serialize_model(self) -> list[dict[str, str | dict[str, str]]]:
        images: list[dict[str, str | dict[str, str]]] = []
        for url in self.image_urls:
            images.append({'type': self.type, 'image_url': {'url': url}})

        return images


class ThinkingContent(Content):
    type: str = ContentType.THINKING.value
    thinking: str
    signature: str

    @model_serializer(mode='plain')
    def serialize_model(self) -> dict[str, str]:
        return {
            'type': self.type,
            'thinking': self.thinking,
            'signature': self.signature,
        }


class Message(BaseModel):
    # NOTE: this is not the same as EventSource
    # These are the roles in the LLM's APIs
    role: Literal['user', 'system', 'assistant', 'tool']
    content: list[TextContent | ImageContent | ThinkingContent] = Field(
        default_factory=list
    )
    cache_enabled: bool = Field(default=False)
    vision_enabled: bool = Field(default=True)
    # function calling
    function_calling_enabled: bool = Field(default=True)
    # - tool calls (from LLM)
    tool_calls: list[ChatCompletionMessageToolCall] | None = Field(default=None)
    # - tool execution result (to LLM)
    tool_call_id: str | None = Field(default=None)
    name: str | None = Field(default=None)  # name of the tool
    # force string serializer
    force_string_serializer: bool = Field(default=False)

    @model_validator(mode='before')
    @classmethod
    def ensure_force_string_serializer(cls, values):
        """Ensure force_string_serializer is always set, especially when loading from JSON."""
        if isinstance(values, dict):
            # Ensure all required fields have defaults - this prevents serialization warnings
            defaults = {
                'force_string_serializer': False,
                'cache_enabled': False,
                'vision_enabled': True,
                'function_calling_enabled': True,
                'tool_calls': None,
                'tool_call_id': None,
                'name': None,
                'content': [],
            }

            # Set defaults for any missing fields
            for key, default_value in defaults.items():
                if key not in values:
                    values[key] = default_value

            # Handle content processing
            if isinstance(values['content'], str):
                # Convert string content to TextContent list
                values['content'] = [
                    {'type': 'text', 'text': values['content'], 'cache_prompt': False}
                ]
            elif isinstance(values['content'], list):
                # Process each content item to ensure proper type reconstruction
                processed_content = []
                for item in values['content']:
                    if isinstance(item, dict):
                        # Handle different content types during deserialization
                        if item.get('type') == 'text':
                            processed_content.append(item)
                        elif item.get('type') == 'image_url':
                            # Reconstruct ImageContent format
                            if 'image_url' in item:
                                # Handle nested image_url structure
                                url = (
                                    item['image_url']['url']
                                    if isinstance(item['image_url'], dict)
                                    else item['image_url']
                                )
                                processed_content.append(
                                    {
                                        'type': 'image_url',
                                        'image_urls': [url],
                                        'cache_prompt': item.get('cache_prompt', False),
                                    }
                                )
                            elif 'image_urls' in item:
                                # Already in ImageContent format
                                processed_content.append(item)
                        elif item.get('type') == 'thinking':
                            processed_content.append(
                                {
                                    'type': 'thinking',
                                    'thinking': item['thinking'],
                                    'signature': item['signature'],
                                }
                            )
                        else:
                            # Keep unknown types as-is
                            processed_content.append(item)
                    else:
                        # Keep non-dict items as-is
                        processed_content.append(item)
                values['content'] = processed_content
        return values

    @classmethod
    def from_llm_response(cls, llm_response) -> 'Message':
        # Safely extract content and tool_calls without triggering LiteLLM serialization
        content_text = ''
        tool_calls = None
        thinking_blocks = None
        content = []

        if hasattr(llm_response, 'thinking_blocks') and llm_response.thinking_blocks:
            thinking_blocks = llm_response.thinking_blocks
            content.append(
                ThinkingContent(
                    thinking=thinking_blocks[0]['thinking'],
                    signature=thinking_blocks[0]['signature'],
                )
            )
            
        if hasattr(llm_response, 'content') and llm_response.content:
            content_text = str(llm_response.content)
            content.append(TextContent(text=content_text))

        if hasattr(llm_response, 'tool_calls') and llm_response.tool_calls:
            tool_calls = llm_response.tool_calls

        # Create Message object with ALL fields explicitly set (fixes serialization warnings)
        return cls(
            role='assistant',
            content=content,
            cache_enabled=True,
            vision_enabled=False,
            function_calling_enabled=bool(tool_calls),
            tool_calls=tool_calls,
            tool_call_id=None,
            name=None,
            force_string_serializer=False,
        )

    @classmethod
    def from_raw_content(
        cls,
        role: Literal['user', 'system', 'assistant', 'tool'],
        raw_content: list[dict[str, Any]],
    ) -> 'Message':
        content_objects = []
        content = raw_content[0]['content']
        if isinstance(content, str):
            content_objects.append(TextContent(text=content))
            return cls(
                role=role,
                content=content_objects,
                cache_enabled=True,
                vision_enabled=False,
                function_calling_enabled=False,
                tool_calls=None,
                tool_call_id=None,
                name=None,
                force_string_serializer=False,
            )

        has_images = False
        for item in content:
            if item["type"] == "text":
                content_objects.append(TextContent(text=item["text"]))
            elif item["type"] == "image_url":
                # Handle both direct URL string and nested URL object
                url = (
                    item["image_url"]["url"]
                    if isinstance(item["image_url"], dict)
                    else item["image_url"]
                )
                content_objects.append(ImageContent(image_urls=[url]))
                has_images = True

        return cls(
            role=role,
            content=content_objects,
            cache_enabled=True,
            vision_enabled=has_images,
            function_calling_enabled=False,
            tool_calls=None,
            tool_call_id=None,
            name=None,
            force_string_serializer=False,
        )

    @classmethod
    def from_tool_call(cls, tool_call, result) -> 'Message':
        return cls(
            role="tool",
            name=tool_call.function.name,
            content=([TextContent(text=result)] if isinstance(result, str) else result),
            tool_call_id=tool_call.id,
            cache_enabled=True,
            vision_enabled=False,
            function_calling_enabled=False,
            tool_calls=None,
            force_string_serializer=False,
        )

    @classmethod
    def from_invalid_tool_call(cls, tool_call) -> 'Message':
        return cls(
            role="tool",
            name=tool_call.function.name,
            content=[
                TextContent(
                    text='The function calling param failed validation, please regenerate'
                )
            ],
            tool_call_id=tool_call.id,
            cache_enabled=True,
            vision_enabled=False,
            function_calling_enabled=False,
            tool_calls=None,
            force_string_serializer=False,
        )

    @property
    def contains_image(self) -> bool:
        return any(isinstance(content, ImageContent) for content in self.content)

    def serialize_for_llm(self) -> dict[str, Any]:
        # We need two kinds of serializations:
        # - into a single string: for providers that don't support list of content items (e.g. no vision, no tool calls)
        # - into a list of content items: the new APIs of providers with vision/prompt caching/tool calls
        # NOTE: remove this when litellm or providers support the new API
        force_string = getattr(self, 'force_string_serializer', False)
        if not force_string and (
            self.cache_enabled or self.vision_enabled or self.function_calling_enabled
        ):
            return self._list_serializer()
        # some providers, like HF and Groq/llama, don't support a list here, but a single string
        return self._string_serializer()

    def _string_serializer(self) -> dict[str, Any]:
        # If there are images, we need to use the list serializer
        if self.contains_image:
            return self._list_serializer()

        # convert content to a single string
        content = '\n'.join(
            item.text for item in self.content if isinstance(item, TextContent)
        )
        message_dict: dict[str, Any] = {
            'content': content,
            'role': self.role,
            'cache_enabled': self.cache_enabled,
            'vision_enabled': self.vision_enabled,
            'function_calling_enabled': self.function_calling_enabled,
            'tool_call_id': self.tool_call_id,
            'name': self.name,
            'force_string_serializer': self.force_string_serializer,
        }

        # add tool call keys if we have a tool call or response
        return self._add_tool_call_keys(message_dict)

    def _list_serializer(self) -> dict[str, Any]:
        content: list[dict[str, Any]] = []
        role_tool_with_prompt_caching = False

        for item in self.content:
            if isinstance(item, TextContent):
                d = item.model_dump()
                if self.role == 'tool' and item.cache_prompt:
                    role_tool_with_prompt_caching = True
                    d.pop('cache_control', None)
                content.append(d)
            elif isinstance(item, ImageContent):
                # Always include image content when using list serializer
                d = item.model_dump()
                if self.role == 'tool' and item.cache_prompt:
                    role_tool_with_prompt_caching = True
                    if isinstance(d, list):
                        for d_item in d:
                            if isinstance(d_item, dict):
                                d_item.pop('cache_control', None)
                content.extend(d if isinstance(d, list) else [d])
            elif isinstance(item, ThinkingContent):
                content.append(item.model_dump())

        message_dict: dict[str, Any] = {
            'content': content,
            'role': self.role,
            'cache_enabled': self.cache_enabled,
            'vision_enabled': self.vision_enabled,
            'function_calling_enabled': self.function_calling_enabled,
            'tool_call_id': self.tool_call_id,
            'name': self.name,
            'force_string_serializer': self.force_string_serializer,
        }
        if role_tool_with_prompt_caching:
            message_dict['cache_control'] = {'type': 'ephemeral'}

        # add tool call keys if we have a tool call or response
        return self._add_tool_call_keys(message_dict)

    def _add_tool_call_keys(self, message_dict: dict[str, Any]) -> dict[str, Any]:
        """Add tool call keys if we have a tool call or response.

        NOTE: this is necessary for both native and non-native tool calling
        """
        # an assistant message calling a tool
        if self.tool_calls is not None:
            message_dict['tool_calls'] = [
                {
                    'id': tool_call.id,
                    'type': 'function',
                    'function': {
                        'name': tool_call.function.name,
                        'arguments': tool_call.function.arguments,
                    },
                }
                for tool_call in self.tool_calls
            ]

        # an observation message with tool response
        if self.tool_call_id is not None:
            assert (
                self.name is not None
            ), 'name is required when tool_call_id is not None'
            message_dict['tool_call_id'] = self.tool_call_id
            message_dict['name'] = self.name

        return message_dict
