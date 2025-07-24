# Remote MCP Server Hosting Guide

This guide explains how to host the AWS Whitelisting MCP server both remotely and locally.

## Overview

The MCP protocol supports both local and remote server configurations. You can:
1. Run locally for Claude Desktop (current setup)
2. Host remotely for shared access
3. Use both simultaneously

## Architecture Options

### Option 1: Direct Remote MCP Server

```
Claude Desktop → Internet → Remote MCP Server → AWS APIs
```

### Option 2: MCP Proxy/Gateway

```
Claude Desktop → MCP Proxy → Remote MCP Server → AWS APIs
```

### Option 3: WebSocket Bridge

```
Claude Desktop → WebSocket → Remote MCP Server → AWS APIs
```

## Remote Hosting Implementation

### 1. Docker Deployment (Recommended)

Create a `docker-compose.remote.yml`:

```yaml
version: '3.8'

services:
  whitelistmcp-remote:
    build: .
    image: whitelistmcp-mcp:latest
    ports:
      - "8080:8080"  # HTTP API endpoint
      - "8081:8081"  # WebSocket endpoint
    environment:
      - MCP_MODE=remote
      - MCP_AUTH_TOKEN=${MCP_AUTH_TOKEN}
      - CORS_ORIGINS=*
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 2. Remote Server Wrapper

Create `whitelistmcp/remote_server.py`:

```python
"""
Remote MCP Server implementation with HTTP/WebSocket support
"""
import asyncio
import json
import os
from aiohttp import web
import aiohttp_cors
from typing import Optional, Dict, Any
import websockets
import jwt
from datetime import datetime, timedelta

from .main import MCPServer
from .mcp.handler import MCPHandler

class RemoteMCPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.mcp_handler = MCPHandler()
        self.app = web.Application()
        self.auth_token = os.getenv("MCP_AUTH_TOKEN", "default-secret-token")
        self.setup_routes()
        self.setup_cors()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/ws', self.websocket_handler)
    
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
    
    def verify_token(self, token: str) -> bool:
        """Verify JWT token for authentication"""
        try:
            jwt.decode(token, self.auth_token, algorithms=["HS256"])
            return True
        except:
            return False
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "service": "whitelistmcp-mcp",
            "version": "1.1.10"
        })
    
    async def handle_mcp_request(self, request):
        """Handle HTTP MCP requests"""
        # Verify authentication
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return web.json_response(
                {"error": "Unauthorized"}, 
                status=401
            )
        
        token = auth_header.split(' ')[1]
        if not self.verify_token(token):
            return web.json_response(
                {"error": "Invalid token"}, 
                status=401
            )
        
        # Process MCP request
        try:
            data = await request.json()
            response = self.mcp_handler.handle_request(data)
            return web.json_response(response)
        except Exception as e:
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Authenticate WebSocket connection
        try:
            auth_msg = await ws.receive_json()
            if not self.verify_token(auth_msg.get('token', '')):
                await ws.close(code=4001, message=b'Unauthorized')
                return ws
        except:
            await ws.close(code=4002, message=b'Invalid auth')
            return ws
        
        # Handle MCP messages
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    response = self.mcp_handler.handle_request(data)
                    await ws.send_json(response)
                except Exception as e:
                    await ws.send_json({
                        "error": str(e),
                        "type": "error"
                    })
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
        
        return ws
    
    def run(self):
        """Start the remote server"""
        web.run_app(
            self.app, 
            host=self.host, 
            port=self.port
        )

if __name__ == "__main__":
    server = RemoteMCPServer()
    server.run()
```

### 3. Client Configuration for Remote Server

Create `claude_desktop_config_remote.json`:

```json
{
  "mcpServers": {
    "whitelistmcp-remote": {
      "command": "node",
      "args": ["mcp-client-proxy.js"],
      "env": {
        "MCP_REMOTE_URL": "https://your-server.com:8080/mcp",
        "MCP_AUTH_TOKEN": "your-auth-token",
        "MCP_MODE": "http"
      }
    }
  }
}
```

### 4. MCP Client Proxy (Node.js)

Create `mcp-client-proxy.js`:

```javascript
#!/usr/bin/env node
/**
 * MCP Client Proxy for connecting to remote MCP servers
 */

const readline = require('readline');
const https = require('https');
const WebSocket = require('ws');

class MCPClientProxy {
  constructor() {
    this.remoteUrl = process.env.MCP_REMOTE_URL;
    this.authToken = process.env.MCP_AUTH_TOKEN;
    this.mode = process.env.MCP_MODE || 'http'; // http or websocket
    
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false
    });
    
    if (this.mode === 'websocket') {
      this.connectWebSocket();
    } else {
      this.setupHttpMode();
    }
  }
  
  connectWebSocket() {
    this.ws = new WebSocket(this.remoteUrl.replace('https://', 'wss://').replace('http://', 'ws://'));
    
    this.ws.on('open', () => {
      // Authenticate
      this.ws.send(JSON.stringify({ token: this.authToken }));
      
      // Forward stdin to WebSocket
      this.rl.on('line', (line) => {
        this.ws.send(line);
      });
    });
    
    this.ws.on('message', (data) => {
      console.log(data.toString());
    });
    
    this.ws.on('error', (error) => {
      console.error(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: `WebSocket error: ${error.message}`
        }
      }));
      process.exit(1);
    });
  }
  
  setupHttpMode() {
    this.rl.on('line', async (line) => {
      try {
        const response = await this.sendHttpRequest(line);
        console.log(JSON.stringify(response));
      } catch (error) {
        console.error(JSON.stringify({
          jsonrpc: "2.0",
          error: {
            code: -32000,
            message: error.message
          }
        }));
      }
    });
  }
  
  async sendHttpRequest(data) {
    return new Promise((resolve, reject) => {
      const options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.authToken}`
        }
      };
      
      const req = https.request(this.remoteUrl, options, (res) => {
        let responseData = '';
        
        res.on('data', (chunk) => {
          responseData += chunk;
        });
        
        res.on('end', () => {
          try {
            resolve(JSON.parse(responseData));
          } catch (e) {
            reject(new Error('Invalid JSON response'));
          }
        });
      });
      
      req.on('error', reject);
      req.write(data);
      req.end();
    });
  }
}

// Start the proxy
new MCPClientProxy();
```

## Deployment Options

### 1. Cloud Providers

#### AWS ECS/Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO
docker build -t whitelistmcp-mcp .
docker tag whitelistmcp-mcp:latest $ECR_REPO/whitelistmcp-mcp:latest
docker push $ECR_REPO/whitelistmcp-mcp:latest

# Deploy with ECS
aws ecs create-service --cluster mcp-cluster --service-name whitelistmcp-mcp ...
```

#### Google Cloud Run
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/whitelistmcp-mcp
gcloud run deploy whitelistmcp-mcp --image gcr.io/$PROJECT_ID/whitelistmcp-mcp --platform managed
```

#### Azure Container Instances
```bash
# Deploy to ACI
az container create --resource-group mcp-rg --name whitelistmcp-mcp --image whitelistmcp-mcp:latest
```

### 2. Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whitelistmcp-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: whitelistmcp-mcp
  template:
    metadata:
      labels:
        app: whitelistmcp-mcp
    spec:
      containers:
      - name: whitelistmcp-mcp
        image: whitelistmcp-mcp:latest
        ports:
        - containerPort: 8080
        env:
        - name: MCP_MODE
          value: "remote"
        - name: MCP_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: auth-token
---
apiVersion: v1
kind: Service
metadata:
  name: whitelistmcp-mcp
spec:
  selector:
    app: whitelistmcp-mcp
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
```

### 3. Serverless Deployment (AWS Lambda)

Create `serverless.yml`:

```yaml
service: whitelistmcp-mcp

provider:
  name: aws
  runtime: python3.9
  timeout: 30
  environment:
    MCP_MODE: serverless

functions:
  mcp:
    handler: lambda_handler.handle
    events:
      - http:
          path: /mcp
          method: post
          cors: true
          authorizer:
            type: TOKEN
            authorizerId: !Ref MCPAuthorizer

resources:
  Resources:
    MCPAuthorizer:
      Type: AWS::ApiGateway::Authorizer
      Properties:
        Name: MCPAuthorizer
        Type: TOKEN
        IdentitySource: method.request.header.Authorization
```

## Security Considerations

### 1. Authentication Methods

- **JWT Tokens**: Time-limited tokens with claims
- **API Keys**: Simple but less secure
- **OAuth 2.0**: For enterprise deployments
- **mTLS**: Certificate-based authentication

### 2. Network Security

- Use HTTPS/WSS for all communications
- Implement rate limiting
- Use VPN or private networks where possible
- Whitelist client IPs if feasible

### 3. AWS Credential Management

For remote servers, consider:
- AWS IAM roles for the server
- Temporary credentials via STS
- Never expose credentials in responses
- Audit all AWS operations

## Hybrid Setup (Local + Remote)

You can run both configurations simultaneously:

```json
{
  "mcpServers": {
    "whitelistmcp-local": {
      "command": "whitelistmcp",
      "env": {
        "AWS_PROFILE": "development"
      }
    },
    "whitelistmcp-remote": {
      "command": "node",
      "args": ["mcp-client-proxy.js"],
      "env": {
        "MCP_REMOTE_URL": "https://mcp.company.com/aws",
        "MCP_AUTH_TOKEN": "production-token"
      }
    }
  }
}
```

## Monitoring and Logging

### 1. Health Checks
- `/health` endpoint for load balancers
- Periodic self-tests
- AWS API connectivity checks

### 2. Metrics
- Request count and latency
- Error rates
- AWS API usage
- Active connections (WebSocket)

### 3. Logging
- Structured JSON logs
- Request/response logging (sanitized)
- Error tracking
- Audit trails for AWS operations

## Cost Optimization

### 1. Caching
- Cache AWS describe operations
- Use Redis for distributed caching
- Implement TTL based on operation type

### 2. Connection Pooling
- Reuse AWS clients
- WebSocket connection management
- HTTP keep-alive

### 3. Auto-scaling
- Scale based on request volume
- Use spot instances where appropriate
- Implement request queuing

## Example Production Setup

### 1. Infrastructure as Code (Terraform)

```hcl
resource "aws_ecs_service" "mcp_server" {
  name            = "whitelistmcp-mcp"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.mcp.arn
  desired_count   = 3

  load_balancer {
    target_group_arn = aws_lb_target_group.mcp.arn
    container_name   = "mcp-server"
    container_port   = 8080
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }
}
```

### 2. CI/CD Pipeline

```yaml
# .github/workflows/deploy-remote.yml
name: Deploy Remote MCP Server

on:
  push:
    branches: [main]
    paths:
      - 'whitelistmcp/**'
      - 'Dockerfile'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Cloud Run
        run: |
          gcloud builds submit --tag gcr.io/$PROJECT_ID/whitelistmcp-mcp
          gcloud run deploy whitelistmcp-mcp \
            --image gcr.io/$PROJECT_ID/whitelistmcp-mcp \
            --platform managed \
            --region us-central1 \
            --allow-unauthenticated
```

## Testing Remote Deployment

### 1. Basic Connectivity Test
```bash
curl -X POST https://your-server.com/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{}}'
```

### 2. WebSocket Test
```javascript
const ws = new WebSocket('wss://your-server.com/ws');
ws.on('open', () => {
  ws.send(JSON.stringify({ token: 'your-token' }));
  ws.send(JSON.stringify({
    jsonrpc: "2.0",
    method: "tools/list",
    id: 1,
    params: {}
  }));
});
```

## Conclusion

This setup allows you to:
1. Keep the existing local MCP server for development
2. Deploy a remote version for production/shared use
3. Use both simultaneously through Claude Desktop
4. Scale the remote deployment as needed

The key is maintaining MCP protocol compliance while adding the necessary networking layer for remote access.