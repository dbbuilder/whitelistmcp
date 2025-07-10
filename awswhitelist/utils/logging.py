"""Logging configuration for AWS whitelisting MCP server."""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from pythonjsonlogger.json import JsonFormatter


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = True
) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_format: Whether to use JSON format for logs
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("awswhitelist")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatter
    if json_format:
        formatter = JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            timestamp=lambda: datetime.now(timezone.utc).isoformat()
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (typically module name)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"awswhitelist.{name}")