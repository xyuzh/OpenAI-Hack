from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field


_JOB_PLAN_DESCRIPTION = """
This tool is used to detect app building requests and create structured, actionable development plans.

Trigger conditions:
- User requests to build, create, or develop a web application
- User describes app features, functionality, or requirements
- User asks for help with app development or enhancement
- User provides app specifications or wireframes
- User requests modifications to an existing app concept

The tool converts user requirements into a phased, executable plan including:
1. Framework recommendation (Next.js vs Vite.js)
2. Core features and implementation phases
3. Technical specifications and architecture
4. Priority guidance
"""

_actionable_plan_desc = """Structured development plan containing:
1. Framework Recommendation:
    - Specify Next.js (for full-stack apps with SSR/SSG, API routes, SEO needs)
    - OR Vite.js
2. Development Phases:
    Phase 1 - Core Features (MVP):
    - List of essential features to implement
    - Basic UI/UX implementation
    - Core data models and API endpoints
    Phase 2 - Enhanced Features:
    - Advanced functionality
    - Performance optimizations
    - User experience improvements
    Phase 3 - Professional Features:
    - Scaling considerations
    - Analytics and monitoring
    - Advanced integrations
3. Technical Specifications:
    - Database requirements (if any)
4. Implementation Details:
    - Folder structure
    - Component architecture
    - State management approach
Format as clear, actionable tasks that an AI agent can execute step-by-step.
"""

class JobPlanParam(BaseModel):
    name: str = Field(..., description='Job name in snake_case')
    actionable_plan: str = Field(..., description=_actionable_plan_desc)

JobPlanTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='job_plan',
        description=_JOB_PLAN_DESCRIPTION,
        parameters=JobPlanParam.model_json_schema(),
    ),
)