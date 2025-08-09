from common.config.config import Config
from workflow.core.controller import EventController

# 使用这个命令初始化配置
app_config = Config.get_app_config()

if __name__ == '__main__':
    event_controller = EventController()
    event_controller.run_controller()
