import logging
import sys
from typing import Any, Dict

import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

from src.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    timestamper = TimeStamper(fmt="iso")
    
    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.contextvars.merge_contextvars,
    ]

    if settings.log_format == "json":
        renderer = JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Silence noisy loggers
    for logger_name in ["urllib3", "httpx", "httpcore"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.stdlib.get_logger(name)


class LogContext:
    """Context manager for adding context to logs."""

    def __init__(self, **kwargs: Any) -> None:
        self.context = kwargs
        self._tokens: Dict[str, Any] = {}

    def __enter__(self) -> None:
        for key, value in self.context.items():
            self._tokens[key] = structlog.contextvars.bind_contextvars(**{key: value})

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        for key in self.context:
            structlog.contextvars.unbind_contextvars(key)