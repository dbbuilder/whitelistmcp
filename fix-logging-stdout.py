#!/usr/bin/env python3
"""Fix to ensure all logging goes to stderr."""

import sys
import logging

# Redirect ALL stdout to stderr for logging
class StderrHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__(sys.stderr)
        # Force stream to always be stderr
        self.stream = sys.stderr
    
    def emit(self, record):
        # Always use stderr
        self.stream = sys.stderr
        super().emit(record)

# Test the current setup
print("Testing current logging setup...")
sys.path.insert(0, r'D:\dev2\awswhitelist2')

from awswhitelist.utils.logging import setup_logging

# Setup logger
logger = setup_logging()

# Test output
print("=== STDOUT TEST ===")
print("=== STDERR TEST ===", file=sys.stderr)
logger.info("=== LOGGER TEST ===")

# Check where it went
print("\nIf LOGGER TEST appeared above with STDOUT TEST, that's the problem!", file=sys.stderr)