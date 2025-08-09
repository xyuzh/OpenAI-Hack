from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field

_SUGGEST_NEXT_STEPS_DESCRIPTION = """This tool is used to conclude the current development task and generate conversation prompts for continuing AI agent app development.

Each next step should be formatted as a clear, concise, actionable prompt that the user can directly copy and use as their next message in the conversation. These prompts should guide the AI to perform specific development tasks.

When creating prompt suggestions, consider:
1. **Feature Implementation**: "Implement [specific feature] that allows the agent to [capability], using [technical approach]"
3. **Integration Tasks**: "Create an API endpoint for [functionality] that integrates with [service/component] and handles [specific scenarios]"
4. **Testing & Debugging**: "Write comprehensive tests for [component] covering [edge cases], and add error handling for [scenarios]"
5. **Performance Optimization**: "Optimize the [process/component] by implementing [caching/indexing/algorithm] to reduce [latency/memory usage]"

Each prompt should:
- Start with a clear action verb (Implement, Create, Refactor, Add, Optimize, etc.)
- Include specific technical details and approaches
- Be self-contained with all necessary context
- Result in measurable improvements
- Be achievable in a single development session
"""


class SuggestNextStepsParam(BaseModel):
    next_steps: list[str] = Field(..., description="A prioritized list of 2-4 conversation prompts that the user can directly use as their next messages.")


SuggestNextStepsTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='suggest_next_steps',
        description=_SUGGEST_NEXT_STEPS_DESCRIPTION,
        parameters=SuggestNextStepsParam.model_json_schema(),
    ),
)
