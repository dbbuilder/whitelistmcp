#!/usr/bin/env python3
"""Test logging configuration."""

import sys
import logging

# Check if root logger has handlers sending to stdout
print("=== Checking Root Logger ===", file=sys.stderr)
root_logger = logging.getLogger()
print(f"Root logger handlers: {root_logger.handlers}", file=sys.stderr)
for handler in root_logger.handlers:
    if hasattr(handler, 'stream'):
        print(f"  Handler stream: {handler.stream}", file=sys.stderr)
        print(f"  Is stdout: {handler.stream == sys.stdout}", file=sys.stderr)
        print(f"  Is stderr: {handler.stream == sys.stderr}", file=sys.stderr)

# Import and check awswhitelist logger
print("\n=== Importing awswhitelist ===", file=sys.stderr)
sys.path.insert(0, r'D:\dev2\awswhitelist2')

from awswhitelist.utils.logging import setup_logging

print("\n=== Setting up awswhitelist logger ===", file=sys.stderr)
logger = setup_logging()

print(f"Logger name: {logger.name}", file=sys.stderr)
print(f"Logger handlers: {logger.handlers}", file=sys.stderr)
for handler in logger.handlers:
    if hasattr(handler, 'stream'):
        print(f"  Handler: {handler}", file=sys.stderr)
        print(f"  Stream: {handler.stream}", file=sys.stderr)
        print(f"  Is stdout: {handler.stream == sys.stdout}", file=sys.stderr)
        print(f"  Is stderr: {handler.stream == sys.stderr}", file=sys.stderr)

# Test logging
print("\n=== Testing log output ===", file=sys.stderr)
print("This goes to stdout")
print("This goes to stderr", file=sys.stderr)
logger.info("This is a log message")

# Check all loggers
print("\n=== All loggers ===", file=sys.stderr)
for name in logging.Logger.manager.loggerDict:
    logger_obj = logging.getLogger(name)
    if logger_obj.handlers:
        print(f"{name}: {logger_obj.handlers}", file=sys.stderr)