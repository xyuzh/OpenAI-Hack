from litellm import ChatCompletionToolParam

class ToolGroup:
    def __init__(self, name: str, desc: str, tools: list[ChatCompletionToolParam]):
        self.name = name
        self.desc = desc
        self.tools = tools



class AgentTools:
    def __init__(self):
        # No tools registered by default; will be reintroduced later
        self._tools: list[ChatCompletionToolParam] = []

    @property
    def tools(self):
        return self._tools

    def tool_groups_description(self) -> str:
        return ""
