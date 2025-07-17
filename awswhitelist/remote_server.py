"""
Remote MCP Server implementation with HTTP/WebSocket support
"""
import asyncio
import json
import os
import logging
from typing import Optional, Dict, Any
from aiohttp import web
import aiohttp_cors

from .main import MCPServer
from .mcp.handler import MCPHandler

logger = logging.getLogger(__name__)

class RemoteMCPServer:
    """Remote MCP Server with HTTP API"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.mcp_handler = MCPHandler()
        self.app = web.Application()
        self.auth_token = os.getenv("MCP_AUTH_TOKEN", "")
        self.setup_routes()
        self.setup_cors()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/', self.index)
    
    def setup_cors(self):
        """Setup CORS for browser-based clients"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods=["POST", "GET", "OPTIONS"]
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def verify_auth(self, request) -> bool:
        """Verify authentication token"""
        if not self.auth_token:
            return True  # No auth required if token not set
        
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        return token == self.auth_token
    
    async def index(self, request):
        """Index page with server info"""
        return web.json_response({
            "service": "AWS Whitelisting MCP Server",
            "version": "1.1.10",
            "protocol": "MCP",
            "endpoints": {
                "health": "/health",
                "mcp": "/mcp"
            }
        })
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "service": "awswhitelist-mcp",
            "version": "1.1.10",
            "mode": "remote"
        })
    
    async def handle_mcp_request(self, request):
        """Handle HTTP MCP requests"""
        # Verify authentication
        if not self.verify_auth(request):
            return web.json_response(
                {"error": "Unauthorized"}, 
                status=401
            )
        
        # Process MCP request
        try:
            data = await request.json()
            
            # Handle as JSON-RPC request
            if isinstance(data, dict):
                response = self.mcp_handler.handle_request(data)
            elif isinstance(data, list):
                # Batch request
                responses = []
                for req in data:
                    resp = self.mcp_handler.handle_request(req)
                    if resp is not None:
                        responses.append(resp)
                response = responses if responses else None
            else:
                return web.json_response(
                    {"error": "Invalid request format"}, 
                    status=400
                )
            
            if response is None:
                return web.Response(status=204)  # No content for notifications
            
            return web.json_response(response)
            
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON"}, 
                status=400
            )
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500
            )
    
    def run(self):
        """Start the remote server"""
        logger.info(f"Starting Remote MCP Server on {self.host}:{self.port}")
        web.run_app(
            self.app, 
            host=self.host, 
            port=self.port,
            print=lambda x: None  # Suppress aiohttp startup messages
        )

def main():
    """Main entry point for remote server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AWS Whitelisting Remote MCP Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--auth-token', help='Authentication token')
    
    args = parser.parse_args()
    
    if args.auth_token:
        os.environ['MCP_AUTH_TOKEN'] = args.auth_token
    
    server = RemoteMCPServer(host=args.host, port=args.port)
    server.run()

if __name__ == "__main__":
    main()