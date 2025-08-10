import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# 创建一个临时logger用于初始化阶段
# 这里不使用get_logger因为可能循环引用
_temp_logger = logging.getLogger('common.config')
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
_temp_logger.addHandler(_handler)
_temp_logger.setLevel(logging.DEBUG)
# 防止日志向上传播
_temp_logger.propagate = False


class ConfigError(Exception):
    """自定义异常，用于配置加载和校验失败时抛出"""
    pass


class Config:
    """配置类，负责加载和管理配置"""

    _initialized = False
    _config_cache = {}  # 缓存已处理的配置

    @classmethod
    def load_config(cls):
        """
        加载配置

        按以下顺序加载配置：
        1. .env 通用配置
        2. 基于 ENV 环境变量加载特定环境配置 (.env.{env})
        3. 系统环境变量 (最高优先级)
        """
        if cls._initialized:
            _temp_logger.info("[配置加载] 配置已经加载，跳过")
            return

        _temp_logger.info("[配置加载] 开始加载配置...")

        # 备份系统环境变量，后续 restore 以保证系统环境变量优先级
        system_env_backup = dict(os.environ)

        # 获取项目根目录（上溯到 common 目录）
        project_root = Path(__file__).resolve().parent.parent

        # 1. 加载通用配置 (.env)
        env_path = project_root / '.env'
        if env_path.exists():
            _temp_logger.info(f"[配置加载] 加载通用配置: {env_path}")
            load_dotenv(dotenv_path=str(env_path), override=False)
        else:
            _temp_logger.warning(f"[配置加载] 警告: 通用配置文件不存在: {env_path}")

        # 2. 获取当前环境
        env = os.environ.get('ENV')
        _temp_logger.info(f"[配置加载] 当前环境: {env}")

        # 3. 如果 ENV 存在，则加载环境特定配置 (.env.{env})
        if env:
            env_specific_path = project_root / f'.env.{env}'
            if env_specific_path.exists():
                _temp_logger.info(f"[配置加载] 加载环境特定配置: {env_specific_path}")
                load_dotenv(dotenv_path=str(env_specific_path), override=True)
            else:
                _temp_logger.warning(
                    f"[配置加载] 警告: 环境特定配置文件不存在: {env_specific_path}")

        # 恢复系统环境变量的原始值，确保系统环境变量最高优先
        os.environ.clear()
        os.environ.update(system_env_backup)
        # 重新加载 .env 及环境特定文件后，系统环境变量覆盖
        if env_path.exists():
            load_dotenv(dotenv_path=str(env_path), override=False)
        if env and (project_root / f'.env.{env}').exists():
            load_dotenv(dotenv_path=str(
                project_root / f'.env.{env}'), override=True)
        os.environ.update(system_env_backup)

        # 打印已加载的配置（隐藏敏感信息）
        cls.print_config()

        # 清空缓存并标记已初始化
        cls._config_cache.clear()
        cls._initialized = True

        _temp_logger.info("[配置加载] 配置加载完成")

    @classmethod
    def _ensure_initialized(cls):
        """确保在获取配置前已调用 load_config"""
        if not cls._initialized:
            cls.load_config()

    @classmethod
    def _get_env(cls, key: str) -> str:
        """
        强制获取环境变量值，若不存在则抛出 ConfigError
        """
        cls._ensure_initialized()
        value = os.environ.get(key)
        if value is None or value.strip() == "":
            _temp_logger.error(f"[配置错误] 缺少必需的环境变量: {key}")
            raise ConfigError(f"Missing required environment variable: {key}")
        return value

    @classmethod
    def _get_env_int(cls, key: str) -> int:
        """
        强制获取环境变量，将其转换为整数，否则抛出 ConfigError
        """
        raw = cls._get_env(key)
        try:
            return int(raw)
        except (ValueError, TypeError):
            _temp_logger.error(f"[配置错误] 环境变量 {key} 不是有效的整数: {raw}")
            raise ConfigError(
                f"Environment variable '{key}' is not a valid integer")

    @classmethod
    def _get_env_bool(cls, key: str) -> bool:
        """
        强制获取环境变量，将其转换为布尔值，否则抛出 ConfigError
        仅接受 "true" 或 "false"（不区分大小写）
        """
        raw = cls._get_env(key).lower()
        if raw in ("true", "false"):
            return raw == "true"
        _temp_logger.error(f"[配置错误] 环境变量 {key} 不是有效的布尔值 (true/false): {raw}")
        raise ConfigError(
            f"Environment variable '{key}' is not a valid boolean (true/false)")

    @classmethod
    def get_app_config(cls) -> dict:
        """获取应用基础配置，若任意值缺失则抛出异常"""
        if 'app_config' in cls._config_cache:
            return cls._config_cache['app_config']

        _temp_logger.info("[应用配置] 获取应用基础配置...")

        app_name = cls._get_env('APP_NAME')
        app_version = cls._get_env('APP_VERSION')
        env = cls._get_env('ENV')

        _temp_logger.info(
            f"[应用配置] 应用名称: {app_name}, 版本: {app_version}, 环境: {env}")

        app_config = {
            'app_name': app_name,
            'app_version': app_version,
            'env': env
        }
        cls._config_cache['app_config'] = app_config
        return app_config

    @classmethod
    def get_broker_url(cls) -> str:
        """构建 RabbitMQ Broker URL，缺少任一项即抛出异常"""
        if 'broker_url' in cls._config_cache:
            return cls._config_cache['broker_url']

        _temp_logger.info("[RabbitMQ配置] 构建 Broker URL...")

        protocol = cls._get_env('RABBITMQ_PROTOCOL')
        host = cls._get_env('RABBITMQ_HOST')
        port = cls._get_env('RABBITMQ_PORT')
        username = cls._get_env('RABBITMQ_USERNAME')
        password = cls._get_env('RABBITMQ_PASSWORD')

        # 构建 broker_url
        broker_url = f"{protocol}://{username}:{password}@{host}:{port}"
        # 打印时隐藏密码
        safe_url = f"{protocol}://{username}:****@{host}:{port}"
        _temp_logger.info(f"[RabbitMQ配置] Broker URL: {safe_url}")

        cls._config_cache['broker_url'] = broker_url
        return broker_url

    @classmethod
    def get_celery_config(cls) -> dict:
        """获取 Celery 配置，若必需项缺失则抛出异常"""
        if 'celery_config' in cls._config_cache:
            return cls._config_cache['celery_config']

        _temp_logger.info("[Celery配置] 构建 Celery 配置...")

        broker_url = cls.get_broker_url()
        celery_config = {
            'broker_url': broker_url,
            # Don't use SSL for local RabbitMQ
            'broker_use_ssl': None
        }

        # 队列配置
        queue_name = cls._get_env('CELERY_QUEUE')
        exchange_name = cls._get_env('CELERY_EXCHANGE')
        routing_key = cls._get_env('CELERY_ROUTING_KEY')

        # 死信队列与 TTL
        dl_exchange = cls._get_env('CELERY_DL_EXCHANGE')
        dl_routing_key = cls._get_env('CELERY_DL_ROUTING_KEY')
        message_ttl = cls._get_env_int('CELERY_MESSAGE_TTL')
        create_missing_queues = cls._get_env_bool(
            'CELERY_TASK_CREATE_MISSING_QUEUES')

        # 构建队列相关字段
        queue_arguments = {
            'x-dead-letter-exchange': dl_exchange,
            'x-dead-letter-routing-key': dl_routing_key,
            'x-message-ttl': message_ttl,
            'x-queue-type': 'classic',
            'x-single-active-consumer': True
        }

        celery_config.update({
            'task_default_queue': queue_name,
            'task_default_exchange': exchange_name,
            'task_default_routing_key': routing_key,
            'task_create_missing_queues': create_missing_queues,
            'task_queues': {
                queue_name: {
                    'exchange': exchange_name,
                    'routing_key': routing_key,
                    'queue_arguments': queue_arguments,
                    'durable': True
                }
            }
        })

        _temp_logger.info(
            f"[Celery配置] 队列: {queue_name}, 交换机: {exchange_name}, 路由键: {routing_key}")
        _temp_logger.info(
            f"[Celery配置] 死信交换机: {dl_exchange}, 死信路由键: {dl_routing_key}")
        _temp_logger.info(f"[Celery配置] 消息 TTL: {message_ttl}ms")

        # 控制与事件交换机（可选）
        control_exchange = cls._get_env('CELERY_CONTROL_EXCHANGE')
        if control_exchange:
            celery_config['control_exchange'] = control_exchange
            _temp_logger.info(f"[Celery配置] 控制交换机: {control_exchange}")

        event_exchange = cls._get_env('CELERY_EVENT_EXCHANGE')
        if event_exchange:
            celery_config['event_exchange'] = event_exchange
            _temp_logger.info(f"[Celery配置] 事件交换机: {event_exchange}")

        # 序列化配置
        task_serializer = cls._get_env('CELERY_TASK_SERIALIZER')
        result_serializer = cls._get_env('CELERY_RESULT_SERIALIZER')
        accept_content = cls._get_env('CELERY_ACCEPT_CONTENT')

        celery_config.update({
            'task_serializer': task_serializer,
            'result_serializer': result_serializer,
            'accept_content': [accept_content]
        })
        _temp_logger.info(
            f"[Celery配置] 任务序列化器: {task_serializer}, 结果序列化器: {result_serializer}")

        # 时区与 UTC 设置
        timezone = cls._get_env('CELERY_TIMEZONE')
        enable_utc = cls._get_env_bool('CELERY_ENABLE_UTC')

        celery_config.update({
            'timezone': timezone,
            'enable_utc': enable_utc
        })
        _temp_logger.info(f"[Celery配置] 时区: {timezone}, 启用UTC: {enable_utc}")

        # Worker 相关（并发、预取、Task 数量、超时）
        worker_concurrency = cls._get_env_int('CELERY_WORKER_CONCURRENCY')
        celery_config['worker_concurrency'] = worker_concurrency
        _temp_logger.info(f"[Celery配置] Worker 并发数: {worker_concurrency}")

        prefetch_multiplier = cls._get_env_int(
            'CELERY_WORKER_PREFETCH_MULTIPLIER')
        celery_config['worker_prefetch_multiplier'] = prefetch_multiplier
        _temp_logger.info(f"[Celery配置] Worker 预取乘数: {prefetch_multiplier}")

        max_tasks_per_child = cls._get_env_int(
            'CELERY_WORKER_MAX_TASKS_PER_CHILD')
        celery_config['worker_max_tasks_per_child'] = max_tasks_per_child
        _temp_logger.info(f"[Celery配置] 每个子进程最大任务数: {max_tasks_per_child}")

        task_time_limit = cls._get_env_int('CELERY_TASK_TIME_LIMIT')
        celery_config['task_time_limit'] = task_time_limit
        _temp_logger.info(f"[Celery配置] 任务硬超时: {task_time_limit}秒")

        task_soft_time_limit = cls._get_env_int('CELERY_TASK_SOFT_TIME_LIMIT')
        celery_config['task_soft_time_limit'] = task_soft_time_limit
        _temp_logger.info(f"[Celery配置] 任务软超时: {task_soft_time_limit}秒")

        _temp_logger.info("[Celery配置] 配置构建完成")
        cls._config_cache['celery_config'] = celery_config
        return celery_config

    @classmethod
    def get_aws_app_sync_config(cls) -> dict:
        """获取 AWS AppSync 配置，若任一项缺失则抛出异常"""
        if 'aws_app_sync_config' in cls._config_cache:
            return cls._config_cache['aws_app_sync_config']

        _temp_logger.info("[AWS AppSync配置] 构建 AWS AppSync 配置...")

        http_domain = cls._get_env('AWS_APP_SYNC_HTTP_DOMAIN')
        websocket_domain = cls._get_env('AWS_APP_SYNC_WEBSOCKET_DOMAIN')
        api_key = cls._get_env('AWS_APP_SYNC_API_KEY')

        app_sync_config = {
            'http_domain': http_domain,
            'websocket_domain': websocket_domain,
            'api_key': api_key
        }
        _temp_logger.info(f"[AWS AppSync配置] HTTP域名: {http_domain}")
        _temp_logger.info(f"[AWS AppSync配置] WebSocket域名: {websocket_domain}")
        _temp_logger.info(f"[AWS AppSync配置] API密钥: {api_key[:4]}***")
        _temp_logger.info("[AWS AppSync配置] 配置构建完成")

        cls._config_cache['aws_app_sync_config'] = app_sync_config
        return app_sync_config

    @classmethod
    def get_workflow_config(cls) -> dict:
        """获取 Workflow 配置，若任一项缺失则抛出异常"""
        if 'workflow_config' in cls._config_cache:
            return cls._config_cache['workflow_config']

        _temp_logger.info("[Workflow配置] 构建 Workflow 配置...")

        anthropic_api_key = cls._get_env('ANTHROPIC_API_KEY')
        openai_api_key = cls._get_env('OPENAI_API_KEY')
        exa_api_key = cls._get_env('EXA_API_KEY')
        daytona_api_key = cls._get_env('DAYTONA_API_KEY')
        daytona_server_url = cls._get_env('DAYTONA_SERVER_URL')
        daytona_sandbox_target = cls._get_env('DAYTONA_SANDBOX_TARGET')
        e2b_api_key = cls._get_env('E2B_API_KEY')

        workflow_config = {
            'anthropic_api_key': anthropic_api_key,
            'openai_api_key': openai_api_key,
            'exa_api_key': exa_api_key,
            'daytona_api_key': daytona_api_key,
            'daytona_server_url': daytona_server_url,
            'daytona_sandbox_target': daytona_sandbox_target,
            'e2b_api_key': e2b_api_key
        }
        _temp_logger.info(
            f"[Workflow配置] Anthropic API Key: {anthropic_api_key[:4]}***")
        _temp_logger.info(f"[Workflow配置] OpenAI API Key: {openai_api_key[:4]}***")
        _temp_logger.info(f"[Workflow配置] Exa API Key: {exa_api_key[:4]}***")
        _temp_logger.info(
            f"[Workflow配置] Daytona API Key: {daytona_api_key[:4]}***")
        _temp_logger.info(f"[Workflow配置] E2B API Key: {e2b_api_key[:4]}***")
        _temp_logger.info("[Workflow配置] 配置构建完成")

        cls._config_cache['workflow_config'] = workflow_config
        return workflow_config

    @classmethod
    def get_usebase_server_boot_config(cls) -> dict:
        """获取 Usebase Server Boot 配置，若任一项缺失则抛出异常"""
        if 'usebase_server_boot_config' in cls._config_cache:
            return cls._config_cache['usebase_server_boot_config']

        _temp_logger.info(
            "[Usebase Server Boot配置] 构建 Usebase Server Boot 配置...")

        usebase_server_boot_base_url = cls._get_env(
            'USEBASE_SERVER_BOOT_BASE_URL')
        usebase_internal_api_key = cls._get_env('USEBASE_INTERNAL_API_KEY')

        usebase_server_boot_config = {
            'usebase_server_boot_base_url': usebase_server_boot_base_url,
            'usebase_internal_api_key': usebase_internal_api_key
        }
        _temp_logger.info(
            f"[Usebase Server Boot配置] Base URL: {usebase_server_boot_base_url}")
        _temp_logger.info(
            f"[Usebase Server Boot配置] API Key: {usebase_internal_api_key[:4]}***")
        _temp_logger.info("[Usebase Server Boot配置] 配置构建完成")

        cls._config_cache['usebase_server_boot_config'] = usebase_server_boot_config
        return usebase_server_boot_config

    @classmethod
    def get_redis_config(cls) -> dict:
        """获取 Redis 配置，若任一项缺失则抛出异常"""
        if 'redis_config' in cls._config_cache:
            return cls._config_cache['redis_config']

        _temp_logger.info("[Redis配置] 构建 Redis 配置...")

        redis_host = cls._get_env('REDIS_HOST')
        redis_port = cls._get_env('REDIS_PORT')
        # Redis 用户名和密码可以为空，但如果有值也必需非空字符串
        redis_username = os.environ.get('REDIS_USERNAME', "")
        redis_password = os.environ.get('REDIS_PASSWORD', "")
        redis_db = cls._get_env('REDIS_DB')

        redis_config = {
            'redis_host': redis_host,
            'redis_port': redis_port,
            'redis_username': redis_username,
            'redis_password': redis_password,
            'redis_db': redis_db
        }
        _temp_logger.info(f"[Redis配置] Host: {redis_host}")
        _temp_logger.info(f"[Redis配置] Port: {redis_port}")
        _temp_logger.info(f"[Redis配置] Username: {redis_username or '<empty>'}")
        if redis_password:
            _temp_logger.info(f"[Redis配置] Password: {redis_password[:4]}***")
        else:
            _temp_logger.info("[Redis配置] Password: <empty>")
        _temp_logger.info(f"[Redis配置] DB: {redis_db}")
        _temp_logger.info("[Redis配置] 配置构建完成")

        cls._config_cache['redis_config'] = redis_config
        return redis_config

    @classmethod
    def get_event_source_config(cls) -> dict:
        """获取 Event Source 配置，若任一项缺失则抛出异常"""
        if 'event_source_config' in cls._config_cache:
            return cls._config_cache['event_source_config']

        _temp_logger.info("[Event Source配置] 构建 Event Source 配置...")

        stream_prefix = cls._get_env('EVENT_SOURCE_STREAM_PREFIX')
        max_length = cls._get_env('EVENT_SOURCE_MAX_STREAM_LENGTH')
        read_count = cls._get_env('EVENT_SOURCE_STREAM_READ_COUNT')
        block_time = cls._get_env('EVENT_SOURCE_STREAM_BLOCK_TIME_MS')
        keep_alive = cls._get_env('EVENT_SOURCE_KEEP_ALIVE_INTERVAL')
        message_queue_max_size = cls._get_env('EVENT_SOURCE_MESSAGE_QUEUE_MAX_SIZE')
        timeout_minutes = cls._get_env('EVENT_SOURCE_TIMEOUT_MINUTES')
        connection_max_duration_minutes = cls._get_env('EVENT_SOURCE_CONNECTION_MAX_DURATION_MINUTES')
        event_source_stream_check_interval_seconds = cls._get_env('EVENT_SOURCE_STREAM_CHECK_INTERVAL_SECONDS')
        connection_timeout_check_interval_seconds = cls._get_env('EVENT_SOURCE_CONNECTION_TIMEOUT_CHECK_INTERVAL_SECONDS')

        event_source_config = {
            'event_source_stream_prefix': stream_prefix,
            'event_source_max_stream_length': max_length,
            'event_source_stream_read_count': read_count,
            'event_source_stream_block_time_ms': block_time,
            'event_source_keep_alive_interval': keep_alive,
            'event_source_message_queue_max_size': message_queue_max_size,
            'event_source_timeout_minutes': timeout_minutes,
            'event_source_connection_max_duration_minutes': connection_max_duration_minutes,
            'event_source_stream_check_interval_seconds': event_source_stream_check_interval_seconds,
            'event_source_connection_timeout_check_interval_seconds': connection_timeout_check_interval_seconds,
        }
        _temp_logger.info(
            f"[Event Source配置] Keep Alive Interval: {keep_alive}")
        _temp_logger.info(f"[Event Source配置] Stream Prefix: {stream_prefix}")
        _temp_logger.info(f"[Event Source配置] Max Stream Length: {max_length}")
        _temp_logger.info(f"[Event Source配置] Stream Read Count: {read_count}")
        _temp_logger.info(
            f"[Event Source配置] Stream Block Time MS: {block_time}")
        _temp_logger.info(
            f"[Event Source配置] Message Queue Max Size: {message_queue_max_size}")
        _temp_logger.info(
            f"[Event Source配置] Timeout Minutes: {timeout_minutes}")
        _temp_logger.info(
            f"[Event Source配置] Stream Check Interval Seconds: {event_source_stream_check_interval_seconds}")
        _temp_logger.info(
            f"[Event Source配置] Connection Max Duration Minutes: {connection_max_duration_minutes}")
        _temp_logger.info(
            f"[Event Source配置] Connection Timeout Check Interval Seconds: {connection_timeout_check_interval_seconds}")
        _temp_logger.info("[Event Source配置] 配置构建完成")

        cls._config_cache['event_source_config'] = event_source_config
        return event_source_config

    @classmethod
    def get_postgres_database_config(cls) -> dict:
        """获取 PostgreSQL 数据库配置，若任一项缺失则抛出异常"""
        if 'postgres_database_config' in cls._config_cache:
            return cls._config_cache['postgres_database_config']

        _temp_logger.info("[Database配置] 构建 Database 配置...")

        host = cls._get_env('POSTGRESQL_DATASOURCE_HOST')
        port = cls._get_env_int('POSTGRESQL_DATASOURCE_PORT')
        username = os.environ.get('POSTGRESQL_DATASOURCE_USERNAME')
        password = os.environ.get('POSTGRESQL_DATASOURCE_PASSWORD')
        langchain_state_db_name = cls._get_env(
            'POSTGRESQL_LANGCHAIN_STATE_DATABASE_NAME')

        # 构建 LangChain Checkpointer 使用的数据库连接 URL
        langchain_state_db_url = f"postgresql://{username}:{password}@{host}:{port}/{langchain_state_db_name}"

        db_config = {
            'langchain_state_db_url': langchain_state_db_url
        }

        _temp_logger.info(
            f"[Database配置] LangChain DB URL: {langchain_state_db_url.replace(password or '', '****')}")
        _temp_logger.info("[Database配置] 配置构建完成")

        cls._config_cache['postgres_database_config'] = db_config
        return db_config

    @classmethod
    def get_logging_config(cls) -> dict:
        """
        获取 Logging 配置，包括彩色日志支持
        """
        if 'logging_config' in cls._config_cache:
            return cls._config_cache['logging_config']

        _temp_logger.info("[Logging配置] 构建 Logging 配置...")

        logging_level = cls._get_env('LOGGING_LEVEL')
        logging_datefmt = cls._get_env('LOGGING_DATEFMT')
        logging_format = cls._get_env('LOGGING_FORMAT')
        logging_colors = cls._get_env('LOGGING_COLORS')

        logging_config = {
            'logging_level': logging_level,
            'logging_datefmt': logging_datefmt,
            'logging_format': logging_format,
            'logging_colors': logging_colors
        }

        _temp_logger.info(f"[Logging配置] Level: {logging_level}")
        _temp_logger.info(f"[Logging配置] Datefmt: {logging_datefmt}")
        _temp_logger.info(f"[Logging配置] Format: {logging_format}")
        _temp_logger.info(f"[Logging配置] Colors: {logging_colors}")
        _temp_logger.info("[Logging配置] 配置构建完成")

        cls._config_cache['logging_config'] = logging_config
        return logging_config

    @classmethod
    def print_config(cls):
        """打印当前配置信息，隐藏敏感信息"""
        _temp_logger.info("\n============= 配置信息 =============")
        _temp_logger.info(f"环境: {os.environ.get('ENV')}")
        _temp_logger.info(f"应用名称: {os.environ.get('APP_NAME')}")
        _temp_logger.info(f"应用版本: {os.environ.get('APP_VERSION')}")
        _temp_logger.info("====================================")

        # 按字母顺序打印环境变量
        for key in sorted(os.environ.keys()):
            if key.isupper():
                value = os.environ[key]
                # 判断是否包含敏感关键词
                sensitive_keywords = ["PASSWORD",
                                      "SECRET", "KEY", "TOKEN", "CREDENTIAL"]
                is_sensitive = any(
                    keyword in key for keyword in sensitive_keywords)
                if is_sensitive and value:
                    _temp_logger.info(f"{key}: {value[:4]}***")
                else:
                    _temp_logger.info(f"{key}: {value}")

        _temp_logger.info("====================================\n")

    @classmethod
    def get_health_status(cls) -> dict:
        """
        获取所有配置的健康状态
        Returns:
            Dict[str, Any]: 包含各个配置项加载状态的字典
        """
        cls._ensure_initialized()

        health_status = {
            "initialized": cls._initialized,
            "configs": {}
        }

        # 针对每个配置方法，捕获异常并记录状态
        config_methods = {
            "app_config": cls.get_app_config,
            "broker_url": cls.get_broker_url,
            "celery_config": cls.get_celery_config,
            "aws_app_sync_config": cls.get_aws_app_sync_config,
            "workflow_config": cls.get_workflow_config,
            "usebase_server_boot_config": cls.get_usebase_server_boot_config,
            "redis_config": cls.get_redis_config,
            "event_source_config": cls.get_event_source_config,
            "postgres_database_config": cls.get_postgres_database_config,
            "logging_config": cls.get_logging_config
        }

        for name, method in config_methods.items():
            try:
                method()
                health_status["configs"][name] = {"status": "ok"}
            except ConfigError as e:
                health_status["configs"][name] = {
                    "status": "error", "message": str(e)}

        overall = all(
            cfg["status"] == "ok" for cfg in health_status["configs"].values()
        )
        health_status["overall_status"] = "healthy" if overall else "unhealthy"

        return health_status
