from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field
from typing import Literal


# TODO: remove or enhance the design with the following spec
_design_spec_description = """Design specification for the project:
- Color palette (primary, secondary, accent colors with hex codes)
**Color Philosophy**: Create an unexpected, harmonious palette that balances boldness with usability. Avoid generic corporate colors (standard blues, greens, oranges).

**Primary Palette**: 
- Hero color: Choose a distinctive, memorable hue (consider: rich burgundies, deep teals, warm terracottas, sage greens, or dusty purples)
- Supporting primary: A complementary shade that creates visual tension

**Neutral Foundation**:
- Instead of pure white/gray, use warmer or cooler tinted neutrals (ivory, charcoal, warm gray, cool slate)
- Include at least one "almost black" for depth

**Accent Strategy**:
- One vibrant accent that creates energy (consider: coral, chartreuse, electric violet, golden yellow)
- One muted accent for subtlety

**Technical Requirements**:
- Provide hex codes
- Ensure WCAG AA contrast ratios
- Include one gradient combination using the palette

**Mood Direction**: [Specify one: Sophisticated warmth / Editorial elegance / Retro-futuristic / Organic luxury / Neo-brutalist / Soft minimalism]

**Inspiration Reference**: [Add specific reference like: "Inspired by desert sunsets" or "1970s Italian design" or "Contemporary art galleries"]"""

_requirement_doc_description = """Technical requirements and feature specifications:
- If database is needed, specify how to integrate into the project
- All packages that should be installed
- All the features that should be implemented
- **IMPORTANT** If database is needed, specify the prisma schema here"""


class UseTemplateParam(BaseModel):
    """
    Choose the web framework to use for the project
    """
    web_framework: Literal["vite", "nextjs"] = Field(
        ..., description="The type of template to use"
    )
    web_app_name: str = Field(..., description="The name of the web app in snake_case")


UseTemplateTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='use_template',
        description="Choose the web framework to use for the project",
        parameters=UseTemplateParam.model_json_schema(),
    ),
)
