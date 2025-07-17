# AWS Whitelisting MCP Server - Remote Hosting Setup

This guide explains how to deploy the AWS Whitelisting MCP Server for remote access while maintaining local desktop functionality.

## Quick Start

### 1. Install with Remote Support

```bash
# Option 1: Install with remote extras
pip install awswhitelist-mcp[remote]

# Option 2: Install from requirements-remote.txt
pip install -r requirements-remote.txt
pip install -e .
```

### 2. Run as Remote Server

```bash
# Basic remote server
awswhitelist-remote --port 8080

# With authentication
awswhitelist-remote --port 8080 --auth-token "your-secret-token"
```

### 3. Configure Claude Desktop for Remote Access

Create a configuration that uses the remote proxy:

```json
{
  "mcpServers": {
    "awswhitelist-remote": {
      "command": "python",
      "args": ["-m", "scripts.mcp-remote-proxy"],
      "env": {
        "MCP_REMOTE_URL": "https://your-server.com:8080/mcp",
        "MCP_AUTH_TOKEN": "your-secret-token"
      }
    }
  }
}
```

## Deployment Options

### Docker Deployment

```bash
# Build the remote server image
docker build -f Dockerfile.remote -t awswhitelist-mcp-remote .

# Run with docker-compose
docker-compose -f docker-compose.remote.yml up -d
```

### Cloud Deployment

#### AWS Lambda
Deploy as a serverless function for cost-effective hosting.

#### Google Cloud Run
```bash
gcloud run deploy awswhitelist-mcp \
  --source . \
  --platform managed \
  --allow-unauthenticated
```

#### Kubernetes
Use the provided k8s manifests in the docs for production deployments.

## Security Considerations

1. **Always use HTTPS** in production
2. **Set strong authentication tokens**
3. **Use IAM roles** instead of hardcoded credentials
4. **Enable audit logging** for compliance

## Hybrid Setup

Run both local and remote servers simultaneously:

```json
{
  "mcpServers": {
    "aws-local": {
      "command": "awswhitelist"
    },
    "aws-prod": {
      "command": "python",
      "args": ["-m", "scripts.mcp-remote-proxy"],
      "env": {
        "MCP_REMOTE_URL": "https://prod.example.com/mcp"
      }
    }
  }
}
```

## Testing

Test your remote server:

```bash
# Health check
curl https://your-server.com:8080/health

# Test MCP request
curl -X POST https://your-server.com:8080/mcp \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

See [docs/REMOTE_HOSTING_GUIDE.md](docs/REMOTE_HOSTING_GUIDE.md) for complete documentation.