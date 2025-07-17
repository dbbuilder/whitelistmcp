#!/usr/bin/env python3
"""
MCP Remote Proxy - Connects Claude Desktop to remote MCP servers
"""
import sys
import json
import os
import requests
from typing import Optional

class MCPRemoteProxy:
    def __init__(self):
        self.remote_url = os.getenv('MCP_REMOTE_URL', 'http://localhost:8080/mcp')
        self.auth_token = os.getenv('MCP_AUTH_TOKEN', '')
        self.session = requests.Session()
        
        if self.auth_token:
            self.session.headers['Authorization'] = f'Bearer {self.auth_token}'
        
        self.session.headers['Content-Type'] = 'application/json'
    
    def send_request(self, data: str) -> Optional[str]:
        """Send request to remote MCP server"""
        try:
            response = self.session.post(
                self.remote_url,
                data=data,
                timeout=30
            )
            
            if response.status_code == 204:
                # No content (notification)
                return None
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": f"Remote server error: {str(e)}"
                }
            }
            return json.dumps(error_response)
    
    def run(self):
        """Main loop - forward stdin to remote server"""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            response = self.send_request(line)
            if response:
                print(response, flush=True)

def main():
    proxy = MCPRemoteProxy()
    proxy.run()

if __name__ == "__main__":
    main()