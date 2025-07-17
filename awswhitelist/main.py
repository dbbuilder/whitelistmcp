"""Main entry point for AWS Whitelisting MCP Server."""

import sys
import json
import argparse
from typing import Dict, Any, Optional
from pathlib import Path

from awswhitelist.config import load_config
from awswhitelist.utils.logging import setup_logging, get_logger
from awswhitelist.mcp.handler import (
    MCPHandler,
    validate_mcp_request,
    create_mcp_error,
    ERROR_PARSE,
    ERROR_INVALID_REQUEST,
    ERROR_INTERNAL
)


class MCPServer:
    """MCP server for handling AWS whitelisting requests."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize MCP server.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Load configuration
        self.config = load_config(config_path)
        
        # Set up logging
        self.logger = setup_logging(
            log_level=getattr(self.config, "log_level", "INFO"),
            log_file=getattr(self.config, "log_file", None),
            json_format=True
        )
        
        # Create MCP handler
        self.handler = MCPHandler(self.config)
        
        self.logger.info("MCP server initialized", extra={
            "config_path": config_path,
            "region": self.config.default_parameters.region
        })
    
    def process_request(self, request_data: str) -> str:
        """Process a single MCP request.
        
        Args:
            request_data: JSON-formatted request string
        
        Returns:
            JSON-formatted response string
        """
        request_id = "unknown"
        
        try:
            # Parse JSON
            try:
                request_dict = json.loads(request_data)
                request_id = request_dict.get("id", "unknown")
            except json.JSONDecodeError as e:
                self.logger.error("JSON parse error", extra={
                    "error": str(e),
                    "request": request_data[:200]  # Log first 200 chars
                })
                response = create_mcp_error(
                    request_id,
                    ERROR_PARSE,
                    "Parse error",
                    {"error": str(e)}
                )
                return json.dumps(response.model_dump(exclude_none=True))
            
            # Validate request
            try:
                request = validate_mcp_request(request_dict)
                request_id = request.id
            except ValueError as e:
                self.logger.error("Invalid request", extra={
                    "error": str(e),
                    "request_id": request_id
                })
                response = create_mcp_error(
                    request_id,
                    ERROR_INVALID_REQUEST,
                    "Invalid Request",
                    {"error": str(e)}
                )
                return json.dumps(response.model_dump(exclude_none=True))
            
            # Check if this is a notification (no id field)
            if request.id is None:
                # Notifications don't require a response
                self.logger.info("Processing notification", extra={
                    "method": request.method
                })
                # Handle specific notifications if needed
                if request.method == "notifications/initialized":
                    self.logger.info("Client initialized")
                return None  # No response for notifications
            
            # Log request
            self.logger.info("Processing request", extra={
                "request_id": request.id,
                "method": request.method
            })
            
            # Handle request
            response = self.handler.handle_request(request)
            
            # Log response
            if response.error:
                self.logger.warning("Request failed", extra={
                    "request_id": request.id,
                    "method": request.method,
                    "error_code": response.error.code,
                    "error_message": response.error.message
                })
            else:
                self.logger.info("Request completed", extra={
                    "request_id": request.id,
                    "method": request.method,
                    "success": response.result.get("success", False) if response.result else False
                })
            
            return json.dumps(response.model_dump(exclude_none=True))
            
        except Exception as e:
            self.logger.exception("Unexpected error", extra={
                "request_id": request_id,
                "error": str(e)
            })
            response = create_mcp_error(
                request_id,
                ERROR_INTERNAL,
                "Internal error",
                {"error": str(e)}
            )
            return json.dumps(response.model_dump(exclude_none=True))
    
    def run(self):
        """Run the MCP server, reading from stdin and writing to stdout."""
        self.logger.info("MCP server started")
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                # Process request
                response = self.process_request(line)
                
                # Write response only if not None (notifications return None)
                if response is not None:
                    print(response)
                    sys.stdout.flush()
                
        except KeyboardInterrupt:
            self.logger.info("Server interrupted by user")
        except Exception as e:
            self.logger.exception("Server error", extra={"error": str(e)})
            sys.exit(1)
        
        self.logger.info("MCP server stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AWS Whitelisting MCP Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
        default=None
    )
    
    parser.add_argument(
        "-v", "--verbose",
        help="Enable verbose logging",
        action="store_true"
    )
    
    parser.add_argument(
        "--version",
        help="Show version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Create and run server
    server = MCPServer(config_path=args.config)
    
    if args.verbose:
        server.logger.setLevel("DEBUG")
    
    server.run()


if __name__ == "__main__":
    main()