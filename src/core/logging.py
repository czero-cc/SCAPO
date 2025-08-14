import logging
import sys
from typing import Any, Dict
from datetime import datetime

import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level
from structlog.typing import EventDict, WrappedLogger

from src.core.config import settings


class PrettyConsoleRenderer:
    """Custom console renderer for pretty terminal output."""
    
    # ANSI color codes
    COLORS = {
        'info': '\033[36m',      # Cyan
        'warning': '\033[33m',   # Yellow  
        'error': '\033[31m',     # Red
        'debug': '\033[90m',     # Gray
        'success': '\033[32m',   # Green
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
    }
    
    # Icons for different log levels
    ICONS = {
        'info': 'ℹ',
        'warning': '⚠',
        'error': '✗',
        'debug': '○',
        'success': '✓',
    }
    
    def __call__(self, logger: WrappedLogger, name: str, event_dict: EventDict) -> str:
        """Format log event for pretty console output."""
        level = event_dict.get('level', 'info').lower()
        timestamp = event_dict.get('timestamp', '')
        logger_name = event_dict.get('logger', '')
        event = event_dict.get('event', '')
        
        # Extract timestamp time only (not full ISO)
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = timestamp[:8] if len(timestamp) > 8 else timestamp
        else:
            time_str = ''
        
        # Choose color based on level
        color = self.COLORS.get(level, self.COLORS['info'])
        icon = self.ICONS.get(level, self.ICONS['info'])
        
        # Build formatted message
        parts = []
        
        # Time in gray
        if time_str:
            parts.append(f"{self.COLORS['dim']}{time_str}{self.COLORS['reset']}")
        
        # Icon and level
        parts.append(f"{color}{icon}{self.COLORS['reset']}")
        
        # Logger name in dim
        if logger_name and not logger_name.startswith('src.'):
            # Only show non-src loggers (like LiteLLM)
            parts.append(f"{self.COLORS['dim']}[{logger_name}]{self.COLORS['reset']}")
        
        # Main event message
        parts.append(event)
        
        # Add any extra fields (excluding standard ones)
        extras = []
        exclude_keys = {'timestamp', 'level', 'logger', 'event', 'logger_name'}
        for key, value in event_dict.items():
            if key not in exclude_keys:
                # Format the extra field nicely
                if isinstance(value, (list, tuple)) and len(value) > 3:
                    value_str = f"[{len(value)} items]"
                elif isinstance(value, dict):
                    value_str = f"[{len(value)} fields]"
                else:
                    value_str = str(value)
                extras.append(f"{self.COLORS['dim']}{key}={value_str}{self.COLORS['reset']}")
        
        if extras:
            parts.append(f"{self.COLORS['dim']}({', '.join(extras)}){self.COLORS['reset']}")
        
        return ' '.join(parts)


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
    elif settings.log_format == "pretty":
        renderer = PrettyConsoleRenderer()
    else:
        # Default to pretty renderer for better terminal experience
        renderer = PrettyConsoleRenderer()

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