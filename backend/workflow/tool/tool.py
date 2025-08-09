from litellm import ChatCompletionToolParam
from workflow.tool.web_search.tool import WebSearchTool
from workflow.tool.file_write.tool import FilesCreationTool
from workflow.tool.file_edit.tool import FileEditTool
from workflow.tool.multi_edit.tool import MultiEditTool
from workflow.tool.todo_read.tool import TodoReadTool
from workflow.tool.todo_write.tool import TodoWriteTool
from workflow.tool.web_search.tool import WebSearchTool
from workflow.tool.bash.tool import BashTool
from workflow.tool.file_read.tool import FileReadTool
from workflow.tool.glob.tool import GlobTool
from workflow.tool.ls.tool import LsTool
from workflow.tool.grep.tool import GrepTool

class ToolGroup:
    def __init__(self, name: str, desc: str, tools: list[ChatCompletionToolParam]):
        self.name = name
        self.desc = desc
        self.tools = tools



class AgentTools:
    def __init__(self):
        web_search_tool_group = ToolGroup(
            name="Web Search",
            desc="Search the web for information",
            tools=[WebSearchTool]
        )
        self._tools = [
            FilesCreationTool,
            FileEditTool,
            MultiEditTool,
            TodoReadTool,
            TodoWriteTool,
            WebSearchTool,
            BashTool,
            FileReadTool,
            GlobTool,
            LsTool,
            GrepTool,
        ]

    @property
    def tools(self):
        return self._tools

    def tool_groups_description(self) -> str:
        return "\n".join(
            [
                f'''
                    Tool name: {tool["function"]["name"]}
                    Tool description: {tool["function"].get("description", "No description available")}
                '''
                for tool in self.tools
            ]
        )
