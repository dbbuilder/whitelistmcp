# AWS Deployment Guide for Remote MCP Server

This guide provides step-by-step instructions for deploying the AWS Whitelisting MCP Server on AWS infrastructure.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Option 1: ECS Fargate Deployment](#option-1-ecs-fargate-deployment)
- [Option 2: EC2 Instance Deployment](#option-2-ec2-instance-deployment)
- [Option 3: Lambda Function Deployment](#option-3-lambda-function-deployment)
- [Security Configuration](#security-configuration)
- [Monitoring and Logging](#monitoring-and-logging)
- [Cost Optimization](#cost-optimization)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│ Claude Desktop  │ ──SSL──▶│ ALB/API Gateway  │ ──────▶│ MCP Server  │
│   MCP Client    │         │  (Public)        │         │  (Private)  │
└─────────────────┘         └──────────────────┘         └─────────────┘
                                                                 │
                                                                 ▼
                                                         ┌─────────────┐
                                                         │   AWS APIs  │
                                                         │  EC2/STS    │
                                                         └─────────────┘
```

## Prerequisites

### AWS Account Setup
1. AWS Account with appropriate permissions
2. AWS CLI installed and configured
3. Docker installed locally (for container deployments)
4. Domain name (optional, for custom URLs)

### Required IAM Permissions
Create an IAM role with these permissions for the MCP server:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Option 1: ECS Fargate Deployment

### Step 1: Build and Push Docker Image

```bash
# Set variables
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO=awswhitelist-mcp

# Create ECR repository
aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION

# Get login token
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
docker build -f Dockerfile.remote -t $ECR_REPO:latest .

# Tag and push
docker tag $ECR_REPO:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
```

### Step 2: Create ECS Task Definition

Create `ecs-task-definition.json`:

```json
{
  "family": "awswhitelist-mcp",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/awswhitelist-mcp-task-role",
  "containerDefinitions": [
    {
      "name": "mcp-server",
      "image": "YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/awswhitelist-mcp:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MCP_AUTH_TOKEN",
          "value": "YOUR_AUTH_TOKEN"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:mcp/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/awswhitelist-mcp",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Step 3: Create ECS Service with ALB

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name mcp-server-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx \
  --scheme internet-facing \
  --type application

# Create target group
aws elbv2 create-target-group \
  --name mcp-server-targets \
  --protocol HTTP \
  --port 8080 \
  --vpc-id vpc-xxx \
  --target-type ip \
  --health-check-enabled \
  --health-check-path /health

# Create listener with SSL
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...

# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create ECS cluster
aws ecs create-cluster --cluster-name mcp-cluster

# Create service
aws ecs create-service \
  --cluster mcp-cluster \
  --service-name awswhitelist-mcp \
  --task-definition awswhitelist-mcp:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=mcp-server,containerPort=8080
```

### Step 4: Configure Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/mcp-cluster/awswhitelist-mcp \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/mcp-cluster/awswhitelist-mcp \
  --policy-name mcp-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

Create `scaling-policy.json`:

```json
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
  },
  "ScaleOutCooldown": 60,
  "ScaleInCooldown": 180
}
```

## Option 2: EC2 Instance Deployment

### Step 1: Launch EC2 Instance

```bash
# Create security group
aws ec2 create-security-group \
  --group-name mcp-server-sg \
  --description "Security group for MCP server" \
  --vpc-id vpc-xxx

# Allow HTTPS inbound
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Launch instance
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.small \
  --key-name your-key-pair \
  --security-group-ids sg-xxx \
  --subnet-id subnet-xxx \
  --iam-instance-profile Name=awswhitelist-mcp-instance-profile \
  --user-data file://user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=mcp-server}]'
```

### Step 2: User Data Script

Create `user-data.sh`:

```bash
#!/bin/bash
# Update system
yum update -y

# Install Docker
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Nginx for SSL termination
amazon-linux-extras install nginx1 -y

# Clone repository
cd /opt
git clone https://github.com/InspirationAI/mcp-servers.git
cd mcp-servers

# Create environment file
cat > .env << EOF
MCP_AUTH_TOKEN=$(aws secretsmanager get-secret-value --secret-id mcp/auth-token --query SecretString --output text)
AWS_DEFAULT_REGION=${AWS_REGION}
EOF

# Start services
docker-compose -f docker-compose.remote.yml up -d

# Configure Nginx
cat > /etc/nginx/conf.d/mcp.conf << 'NGINX'
server {
    listen 443 ssl http2;
    server_name mcp.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/mcp.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

# Install Certbot for SSL
amazon-linux-extras install epel -y
yum install certbot python3-certbot-nginx -y

# Get SSL certificate
certbot --nginx -d mcp.yourdomain.com --non-interactive --agree-tos --email admin@yourdomain.com

# Start Nginx
systemctl enable nginx
systemctl start nginx

# Setup CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm
```

### Step 3: Configure Auto-Recovery

```bash
# Create CloudWatch alarm for instance health
aws cloudwatch put-metric-alarm \
  --alarm-name mcp-server-health \
  --alarm-description "Auto recover MCP server" \
  --metric-name StatusCheckFailed_System \
  --namespace AWS/EC2 \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=InstanceId,Value=i-xxx \
  --alarm-actions arn:aws:automate:${AWS_REGION}:ec2:recover
```

## Option 3: Lambda Function Deployment

### Step 1: Create Lambda Package

Create `lambda_handler.py`:

```python
import json
import os
from awswhitelist.mcp.handler import MCPHandler

# Initialize handler
mcp_handler = MCPHandler()

def lambda_handler(event, context):
    """AWS Lambda handler for MCP requests"""
    
    # Verify authentication
    auth_token = os.environ.get('MCP_AUTH_TOKEN')
    if auth_token:
        provided_token = event.get('headers', {}).get('Authorization', '').replace('Bearer ', '')
        if provided_token != auth_token:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'})
            }
    
    # Parse request body
    try:
        if event.get('isBase64Encoded'):
            import base64
            body = base64.b64decode(event['body']).decode('utf-8')
        else:
            body = event['body']
        
        request_data = json.loads(body)
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid request body'})
        }
    
    # Process MCP request
    try:
        response = mcp_handler.handle_request(request_data)
        
        if response is None:
            return {'statusCode': 204}
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'jsonrpc': '2.0',
                'error': {
                    'code': -32000,
                    'message': str(e)
                }
            })
        }
```

### Step 2: Package and Deploy

```bash
# Create deployment package
mkdir lambda-package
cd lambda-package

# Install dependencies
pip install awswhitelist-mcp -t .

# Add handler
cp ../lambda_handler.py .

# Create ZIP
zip -r ../mcp-lambda.zip .

# Create Lambda function
aws lambda create-function \
  --function-name awswhitelist-mcp \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-mcp-role \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://../mcp-lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables={MCP_AUTH_TOKEN=your-token}

# Create API Gateway
aws apigatewayv2 create-api \
  --name mcp-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:awswhitelist-mcp

# Add Lambda permission
aws lambda add-permission \
  --function-name awswhitelist-mcp \
  --statement-id api-gateway \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com
```

## Security Configuration

### 1. Network Security

```bash
# Create VPC for MCP server
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# Create private subnets
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create security groups
aws ec2 create-security-group \
  --group-name mcp-alb-sg \
  --description "ALB security group" \
  --vpc-id vpc-xxx

aws ec2 create-security-group \
  --group-name mcp-app-sg \
  --description "Application security group" \
  --vpc-id vpc-xxx

# Configure security group rules
aws ec2 authorize-security-group-ingress \
  --group-id sg-alb \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-app \
  --protocol tcp \
  --port 8080 \
  --source-group sg-alb
```

### 2. Secrets Management

```bash
# Store sensitive data in AWS Secrets Manager
aws secretsmanager create-secret \
  --name mcp/auth-token \
  --secret-string "your-secure-token"

aws secretsmanager create-secret \
  --name mcp/jwt-secret \
  --secret-string "your-jwt-secret-key"

# Create KMS key for encryption
aws kms create-key \
  --description "MCP server encryption key" \
  --key-policy file://kms-policy.json
```

### 3. IAM Roles and Policies

```bash
# Create task execution role
aws iam create-role \
  --role-name awswhitelist-mcp-task-role \
  --assume-role-policy-document file://task-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name awswhitelist-mcp-task-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create custom policy for MCP operations
aws iam create-policy \
  --policy-name MCPServerPolicy \
  --policy-document file://mcp-policy.json

aws iam attach-role-policy \
  --role-name awswhitelist-mcp-task-role \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT:policy/MCPServerPolicy
```

## Monitoring and Logging

### 1. CloudWatch Configuration

```bash
# Create log group
aws logs create-log-group --log-group-name /aws/mcp/server

# Create metric filters
aws logs put-metric-filter \
  --log-group-name /aws/mcp/server \
  --filter-name ErrorCount \
  --filter-pattern '[timestamp, request_id, level="ERROR", ...]' \
  --metric-transformations \
    metricName=MCPErrors,metricNamespace=MCP,metricValue=1

# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name MCP-Server \
  --dashboard-body file://dashboard.json
```

### 2. X-Ray Tracing

```python
# Add to your application
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.aiohttp.middleware import middleware

xray_recorder.configure(service='mcp-server')
app.middlewares.append(middleware)

@xray_recorder.capture_async('mcp_request')
async def handle_request(self, request):
    # Your code here
    pass
```

### 3. CloudWatch Alarms

```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name mcp-high-error-rate \
  --alarm-description "High error rate on MCP server" \
  --metric-name MCPErrors \
  --namespace MCP \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:YOUR_ACCOUNT:mcp-alerts

# High latency alarm
aws cloudwatch put-metric-alarm \
  --alarm-name mcp-high-latency \
  --alarm-description "High latency on MCP server" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold
```

## Cost Optimization

### 1. Use Spot Instances for ECS

```json
{
  "capacityProviders": ["FARGATE_SPOT"],
  "defaultCapacityProviderStrategy": [
    {
      "capacityProvider": "FARGATE_SPOT",
      "weight": 4,
      "base": 0
    },
    {
      "capacityProvider": "FARGATE",
      "weight": 1,
      "base": 2
    }
  ]
}
```

### 2. Reserved Capacity

```bash
# Purchase Savings Plans for predictable workloads
aws savingsplans purchase \
  --commitment-amount 10 \
  --savings-plan-type Compute \
  --term-duration-in-seconds 31536000
```

### 3. Cost Monitoring

```bash
# Set up cost anomaly detection
aws ce create-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "MCP-Server-Monitor",
    "MonitorType": "CUSTOM",
    "MonitorSpecification": {
      "Tags": {
        "Key": "Service",
        "Values": ["mcp-server"]
      }
    }
  }'
```

## Claude Desktop Configuration

After deployment, configure Claude Desktop to use the remote server:

```json
{
  "mcpServers": {
    "awswhitelist-prod": {
      "command": "python",
      "args": ["-m", "scripts.mcp-remote-proxy"],
      "env": {
        "MCP_REMOTE_URL": "https://mcp.yourdomain.com/mcp",
        "MCP_AUTH_TOKEN": "your-auth-token"
      }
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   ```bash
   # Check security groups
   aws ec2 describe-security-groups --group-ids sg-xxx
   
   # Check ALB target health
   aws elbv2 describe-target-health --target-group-arn arn:aws:...
   ```

2. **Authentication Failures**
   ```bash
   # Verify secrets
   aws secretsmanager get-secret-value --secret-id mcp/auth-token
   
   # Check IAM permissions
   aws iam simulate-principal-policy \
     --policy-source-arn arn:aws:iam::... \
     --action-names ec2:DescribeSecurityGroups
   ```

3. **High Latency**
   ```bash
   # Check CloudWatch metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ECS \
     --metric-name CPUUtilization \
     --dimensions Name=ServiceName,Value=awswhitelist-mcp \
     --start-time 2024-01-01T00:00:00Z \
     --end-time 2024-01-01T01:00:00Z \
     --period 300 \
     --statistics Average
   ```

### Debug Mode

Enable debug logging:

```bash
# Update task definition
aws ecs update-service \
  --cluster mcp-cluster \
  --service awswhitelist-mcp \
  --task-definition awswhitelist-mcp:2 \
  --environment LOG_LEVEL=DEBUG
```

## Maintenance

### 1. Updates and Patches

```bash
# Update container image
docker build -f Dockerfile.remote -t mcp:new .
docker push $ECR_REPO:new

# Update service
aws ecs update-service \
  --cluster mcp-cluster \
  --service awswhitelist-mcp \
  --task-definition awswhitelist-mcp:new
```

### 2. Backup Configuration

```bash
# Backup task definitions
aws ecs describe-task-definition \
  --task-definition awswhitelist-mcp \
  > backup/task-definition-$(date +%Y%m%d).json

# Backup secrets
aws secretsmanager describe-secret \
  --secret-id mcp/auth-token \
  > backup/secrets-$(date +%Y%m%d).json
```

### 3. Disaster Recovery

Create multi-region setup:

```bash
# Replicate to another region
aws ecr create-replication-configuration \
  --replication-configuration file://replication-config.json

# Create Route53 health checks
aws route53 create-health-check \
  --health-check-config file://health-check.json
```

## Conclusion

This guide provides comprehensive instructions for deploying the MCP server on AWS. Choose the deployment option that best fits your requirements:

- **ECS Fargate**: Best for containerized, scalable deployments
- **EC2**: Best for full control and custom configurations
- **Lambda**: Best for serverless, pay-per-request model

Remember to:
1. Follow security best practices
2. Monitor costs and performance
3. Keep the deployment updated
4. Test disaster recovery procedures regularly