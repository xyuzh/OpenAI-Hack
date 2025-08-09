import os
from dataclasses import dataclass, field

from jinja2 import Template



@dataclass
class RuntimeInfo:
    date: str
    available_hosts: dict[str, int] = field(default_factory=dict)
    additional_agent_instructions: str = ''


@dataclass
class RepositoryInfo:
    """Information about a GitHub repository that has been cloned."""

    repo_name: str | None = None
    repo_directory: str | None = None


class PromptManager:
    """
    Manages prompt templates and includes information from the user's workspace micro-agents and global micro-agents.

    This class is dedicated to loading and rendering prompts (system prompt, user prompt).

    Attributes:
        prompt_dir: Directory containing prompt templates.
    """

    def __init__(
        self,
        prompt_dir: str,
    ):
        self.prompt_dir: str = prompt_dir
        try:
            self.user_template: Template = self._load_template('user_prompt')
        except FileNotFoundError:
            self.user_template = None

    def _load_template(self, template_name: str) -> Template:
        if self.prompt_dir is None:
            raise ValueError('Prompt directory is not set')
        template_path = os.path.join(self.prompt_dir, f'{template_name}.j2')
        if not os.path.exists(template_path):
            raise FileNotFoundError(f'Prompt file {template_path} not found')
        with open(template_path, 'r') as file:
            return Template(file.read())

    def get_system_message(self) -> str:
        system_prompt_template = self.load_prompt_template('system_prompt')
        return system_prompt_template.render().strip()

    def load_prompt_template(self, template_name: str) -> Template:
        return self._load_template(template_name)

    def get_example_user_message(self) -> str:
        """This is an initial user message that can be provided to the agent
        before *actual* user instructions are provided.

        It can be used to provide a demonstration of how the agent
        should behave in order to solve the user's task. And it may
        optionally contain some additional context about the user's task.
        These additional context will convert the current generic agent
        into a more specialized agent that is tailored to the user's task.
        """

        return self.user_template.render().strip()

    def build_workspace_context(
        self,
        repository_info: RepositoryInfo | None,
        runtime_info: RuntimeInfo | None,
        repo_instructions: str = '',
    ) -> str:
        """Renders the additional info template with the stored repository/runtime info."""
        return self.additional_info_template.render(
            repository_info=repository_info,
            repository_instructions=repo_instructions,
            runtime_info=runtime_info,
        ).strip()
