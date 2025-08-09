import os

from jinja2 import Template

from common.utils.logger_utils import get_logger

logger = get_logger("common.utils.template_utils")


def render_template(prompt_name: str, prompt_dir: str, **kwargs) -> str:
    """渲染模板"""
    prompt_path = os.path.join(
        prompt_dir, f"{prompt_name}.j2")

    try:
        with open(prompt_path, 'r') as file:
            template = Template(file.read())
            result = template.render(**kwargs)

            logger.debug(f"{prompt_name}渲染结果：{result}")
            return result
    except Exception as e:
        logger.error(f"渲染{prompt_name}出错：{str(e)}")
        raise
