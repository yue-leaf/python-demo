import json
import os
from datetime import datetime
from pathlib import Path

from loguru import logger
import sys

log_file = Path(os.getcwd()) / "logs" / f"agent_{datetime.now().strftime('%Y-%m-%d')}.log"
logger.add(log_file, enqueue=True, rotation="1 day", retention="7 days")


# 自定义序列化函数
def serialize(record):
    subset = {
        "datetime": record["time"].strftime("%Y-%m-%d %H:%M:%S"),
        "message": record["message"],
        "level": record["level"].name,
        "file": record["file"].name,
        "context": record["extra"],
    }
    return json.dumps(subset, ensure_ascii=False)


# 自定义 patching 函数
def patching(record):
    record["extra"]["serialized"] = serialize(record)


# 移除默认的控制台输出
logger.remove(0)
# 应用 patching
logger = logger.patch(patching)
# 配置标准输出 (sys.stderr) 为 JSON 格式
logger.add(sys.stderr, format="{extra[serialized]}", enqueue=True)


class Logger:
    @staticmethod
    def info(message, *args, **kwargs):
        context = {}
        logger_with_context = logger.bind(**context)
        if "%" in message and args and not kwargs:
            try:
                formatted_message = message % args
                logger_with_context.info(formatted_message)
            except (TypeError, ValueError) as e:
                logger_with_context.error("Invalid % format string: {}. Message: {}", e, message)
        else:
            # Handle {} style formatting or no formatting
            logger_with_context.info(message, *args, **kwargs)

    @staticmethod
    def error(message, *args, **kwargs):
        context = {}
        logger_with_context = logger.bind(**context)
        if "%" in message and args and not kwargs:
            try:
                formatted_message = message % args
                logger_with_context.info(formatted_message)
            except (TypeError, ValueError) as e:
                logger_with_context.error("Invalid % format string: {}. Message: {}", e, message)
        else:
            # Handle {} style formatting or no formatting
            logger_with_context.error(message, *args, **kwargs)


if __name__ == '__main__':
    msg = "world"
    Logger.info(f"Hello, {msg}!")
