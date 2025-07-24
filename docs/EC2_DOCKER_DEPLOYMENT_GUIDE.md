# EC2 Docker Container Deployment Guide

This guide provides detailed instructions for deploying the MCP Server as a Docker container on EC2 instances.

## Table of Contents
- [Overview](#overview)
- [Option 1: Standalone EC2 with Docker](#option-1-standalone-ec2-with-docker)
- [Option 2: ECS with EC2 Launch Type](#option-2-ecs-with-ec2-launch-type)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Container Management](#container-management)
- [Monitoring and Maintenance](#monitoring-and-maintenance)

## Overview

### Architecture Comparison

| Feature | Standalone EC2 | ECS EC2 |
|---------|---------------|---------|
| Management Overhead | High | Low |
| Auto-scaling | Manual | Automatic |
| Container Orchestration | Docker/Docker Compose | ECS |
| Cost | Lower | Higher (ECS overhead) |
| Complexity | Simple | More Complex |

## Option 1: Standalone EC2 with Docker

### Step 1: Launch EC2 Instance

Create a launch script `launch-ec2-docker.sh`:

```bash
#!/bin/bash

# Configuration
INSTANCE_TYPE="t3.medium"
KEY_NAME="mcp-server-key"
SECURITY_GROUP_NAME="mcp-docker-sg"
INSTANCE_NAME="mcp-docker-server"

# Get latest Amazon Linux 2 AMI optimized for ECS
AMI_ID=$(aws ssm get-parameters \
    --names /aws/service/ecs/optimized-ami/amazon-linux-2/recommended \
    --query 'Parameters[0].Value' | jq -r '.image_id')

# Create key pair
aws ec2 create-key-pair \
    --key-name $KEY_NAME \
    --query 'KeyMaterial' \
    --output text > $KEY_NAME.pem
chmod 400 $KEY_NAME.pem

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=is-default,Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text)

# Create security group
SG_ID=$(aws ec2 create-security-group \
    --group-name $SECURITY_GROUP_NAME \
    --description "Security group for MCP Docker server" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text)

# Configure security group rules
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

# Create IAM role for EC2
aws iam create-role \
    --role-name MCPDockerEC2Role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach policies
aws iam attach-role-policy \
    --role-name MCPDockerEC2Role \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

aws iam attach-role-policy \
    --role-name MCPDockerEC2Role \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy

# Create instance profile
aws iam create-instance-profile \
    --instance-profile-name MCPDockerEC2Profile

aws iam add-role-to-instance-profile \
    --instance-profile-name MCPDockerEC2Profile \
    --role-name MCPDockerEC2Role

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --iam-instance-profile Name=MCPDockerEC2Profile \
    --block-device-mappings '[{
        "DeviceName": "/dev/xvda",
        "Ebs": {
            "VolumeSize": 30,
            "VolumeType": "gp3",
            "DeleteOnTermination": true
        }
    }]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --user-data file://ec2-docker-userdata.sh \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "Instance launched: $INSTANCE_ID"
```

### Step 2: EC2 User Data Script

Create `ec2-docker-userdata.sh`:

```bash
#!/bin/bash
set -e

# Update system
yum update -y

# Install dependencies
yum install -y \
    docker \
    git \
    htop \
    amazon-cloudwatch-agent

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
DOCKER_COMPOSE_VERSION="2.23.0"
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Configure Docker daemon
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "metrics-addr": "127.0.0.1:9323",
  "experimental": true
}
EOF

systemctl restart docker

# Create application directory
mkdir -p /opt/mcp-server
cd /opt/mcp-server

# Clone repository
git clone https://github.com/InspirationAI/mcp-servers.git .

# Create environment configuration
cat > .env << 'EOF'
# MCP Server Configuration
MCP_AUTH_TOKEN=${MCP_AUTH_TOKEN}
LOG_LEVEL=INFO
NODE_ENV=production

# AWS Configuration (uses IAM role)
AWS_DEFAULT_REGION=us-east-1

# Container Configuration
CONTAINER_NAME=mcp-server
CONTAINER_PORT=8080
HOST_PORT=8080
EOF

# Create docker-compose override for production
cat > docker-compose.override.yml << 'EOF'
version: '3.8'

services:
  whitelistmcp-remote:
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1024M
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

# Create systemd service
cat > /etc/systemd/system/mcp-server.service << 'EOF'
[Unit]
Description=MCP Server Docker Container
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10
WorkingDirectory=/opt/mcp-server
ExecStartPre=/usr/local/bin/docker-compose down
ExecStart=/usr/local/bin/docker-compose -f docker-compose.remote.yml up
ExecStop=/usr/local/bin/docker-compose down
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable mcp-server
systemctl start mcp-server

# Install and configure Nginx for SSL termination
amazon-linux-extras install nginx1 -y

# Configure Nginx
cat > /etc/nginx/conf.d/mcp-server.conf << 'EOF'
upstream mcp_backend {
    server localhost:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name _;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name _;
    
    # SSL configuration (update with your certificates)
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location /health {
        proxy_pass http://mcp_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        access_log off;
    }
    
    location /mcp {
        proxy_pass http://mcp_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Create self-signed certificate (replace with Let's Encrypt in production)
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Start Nginx
systemctl enable nginx
systemctl start nginx

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
  "metrics": {
    "namespace": "MCP/Server",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          "cpu_usage_idle",
          "cpu_usage_iowait",
          "cpu_usage_user",
          "cpu_usage_system"
        ],
        "metrics_collection_interval": 60,
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          "used_percent",
          "inodes_free"
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "*"
        ]
      },
      "mem": {
        "measurement": [
          "mem_used_percent"
        ],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "/aws/ec2/mcp-server",
            "log_stream_name": "{instance_id}/system"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Setup automatic updates
cat > /etc/cron.daily/docker-updates << 'EOF'
#!/bin/bash
cd /opt/mcp-server
git pull
docker-compose pull
systemctl restart mcp-server
EOF
chmod +x /etc/cron.daily/docker-updates

echo "EC2 Docker setup complete!"
```

### Step 3: Container Management Script

Create `manage-mcp-container.sh`:

```bash
#!/bin/bash
# MCP Container Management Script

set -e

ACTION=$1
MCP_DIR="/opt/mcp-server"

case $ACTION in
    start)
        echo "Starting MCP container..."
        cd $MCP_DIR
        docker-compose -f docker-compose.remote.yml up -d
        ;;
    
    stop)
        echo "Stopping MCP container..."
        cd $MCP_DIR
        docker-compose down
        ;;
    
    restart)
        echo "Restarting MCP container..."
        cd $MCP_DIR
        docker-compose down
        docker-compose -f docker-compose.remote.yml up -d
        ;;
    
    logs)
        echo "Showing container logs..."
        cd $MCP_DIR
        docker-compose logs -f --tail=100
        ;;
    
    status)
        echo "Container status:"
        docker ps -a | grep mcp || echo "No MCP containers found"
        echo ""
        echo "Container health:"
        docker inspect whitelistmcp-remote | jq '.[0].State.Health'
        ;;
    
    update)
        echo "Updating MCP server..."
        cd $MCP_DIR
        git pull
        docker-compose pull
        docker-compose down
        docker-compose -f docker-compose.remote.yml up -d
        ;;
    
    shell)
        echo "Entering container shell..."
        docker exec -it whitelistmcp-remote /bin/sh
        ;;
    
    stats)
        echo "Container resource usage:"
        docker stats --no-stream whitelistmcp-remote
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|update|shell|stats}"
        exit 1
        ;;
esac
```

## Option 2: ECS with EC2 Launch Type

### Step 1: Create ECS Cluster with EC2

Create `ecs-ec2-cluster.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ECS Cluster with EC2 Container Instances'

Parameters:
  InstanceType:
    Type: String
    Default: t3.medium
    Description: EC2 instance type for container instances
  
  DesiredCapacity:
    Type: Number
    Default: 2
    Description: Number of EC2 instances
  
  MaxSize:
    Type: Number
    Default: 6
    Description: Maximum number of EC2 instances
  
  KeyName:
    Type: AWS::EC2::KeyPair::KeyName
    Description: EC2 Key Pair for SSH access

Resources:
  # ECS Cluster
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Sub '${AWS::StackName}-cluster'
      Configuration:
        ExecuteCommandConfiguration:
          Logging: DEFAULT

  # Launch Template
  LaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: !Sub '${AWS::StackName}-lt'
      LaunchTemplateData:
        ImageId: !Ref LatestECSOptimizedAMI
        InstanceType: !Ref InstanceType
        KeyName: !Ref KeyName
        IamInstanceProfile:
          Arn: !GetAtt InstanceProfile.Arn
        SecurityGroupIds:
          - !Ref ContainerInstanceSecurityGroup
        BlockDeviceMappings:
          - DeviceName: /dev/xvda
            Ebs:
              VolumeSize: 50
              VolumeType: gp3
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            echo ECS_CLUSTER=${ECSCluster} >> /etc/ecs/ecs.config
            echo ECS_ENABLE_TASK_IAM_ROLE=true >> /etc/ecs/ecs.config
            echo ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST=true >> /etc/ecs/ecs.config
            
            # Install CloudWatch agent
            wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
            rpm -U ./amazon-cloudwatch-agent.rpm
            
            # Configure Docker
            cat > /etc/docker/daemon.json << EOF
            {
              "log-driver": "awslogs",
              "log-opts": {
                "awslogs-group": "/ecs/container-instance",
                "awslogs-region": "${AWS::Region}",
                "awslogs-stream-prefix": "ecs"
              }
            }
            EOF
            
            systemctl restart docker
            
            # Install SSM agent
            yum install -y amazon-ssm-agent
            systemctl enable amazon-ssm-agent
            systemctl start amazon-ssm-agent

  # Auto Scaling Group
  AutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      AutoScalingGroupName: !Sub '${AWS::StackName}-asg'
      VPCZoneIdentifier: !Ref SubnetIds
      LaunchTemplate:
        LaunchTemplateId: !Ref LaunchTemplate
        Version: !GetAtt LaunchTemplate.LatestVersionNumber
      MinSize: 1
      MaxSize: !Ref MaxSize
      DesiredCapacity: !Ref DesiredCapacity
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-container-instance'
          PropagateAtLaunch: true

  # Capacity Provider
  CapacityProvider:
    Type: AWS::ECS::CapacityProvider
    Properties:
      Name: !Sub '${AWS::StackName}-cp'
      AutoScalingGroupProvider:
        AutoScalingGroupArn: !Ref AutoScalingGroup
        ManagedScaling:
          Status: ENABLED
          TargetCapacity: 100
          MinimumScalingStepSize: 1
          MaximumScalingStepSize: 10
        ManagedTerminationProtection: ENABLED

  # Cluster Capacity Provider Association
  ClusterCapacityProviderAssociation:
    Type: AWS::ECS::ClusterCapacityProviderAssociations
    Properties:
      Cluster: !Ref ECSCluster
      CapacityProviders:
        - !Ref CapacityProvider
      DefaultCapacityProviderStrategy:
        - CapacityProvider: !Ref CapacityProvider
          Weight: 1
          Base: 0

  # IAM Role for Container Instances
  ContainerInstanceRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
        - arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
      Policies:
        - PolicyName: ECSInstancePolicy
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action:
                  - ecs:CreateCluster
                  - ecs:DeregisterContainerInstance
                  - ecs:DiscoverPollEndpoint
                  - ecs:Poll
                  - ecs:RegisterContainerInstance
                  - ecs:StartTelemetrySession
                  - ecs:Submit*
                  - ecr:GetAuthorizationToken
                  - ecr:BatchCheckLayerAvailability
                  - ecr:GetDownloadUrlForLayer
                  - ecr:BatchGetImage
                Resource: '*'

  InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref ContainerInstanceRole

  # Security Group
  ContainerInstanceSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for ECS container instances
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          CidrIp: 0.0.0.0/0  # Restrict this!
        - IpProtocol: tcp
          FromPort: 32768
          ToPort: 65535
          SourceSecurityGroupId: !Ref ALBSecurityGroup

  # Parameter for latest ECS AMI
  LatestECSOptimizedAMI:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ecs/optimized-ami/amazon-linux-2/recommended/image_id

Outputs:
  ClusterName:
    Value: !Ref ECSCluster
  CapacityProvider:
    Value: !Ref CapacityProvider
  AutoScalingGroup:
    Value: !Ref AutoScalingGroup
```

### Step 2: Deploy MCP Task on EC2 Instances

Create `ecs-mcp-task-ec2.json`:

```json
{
  "family": "mcp-server-ec2",
  "networkMode": "bridge",
  "requiresCompatibilities": ["EC2"],
  "cpu": "1024",
  "memory": "2048",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/mcp-task-role",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "mcp-server",
      "image": "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/mcp-server:latest",
      "memoryReservation": 1024,
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 0,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        },
        {
          "name": "PORT",
          "value": "8080"
        }
      ],
      "secrets": [
        {
          "name": "MCP_AUTH_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:mcp/auth-token"
        }
      ],
      "mountPoints": [
        {
          "sourceVolume": "docker-socket",
          "containerPath": "/var/run/docker.sock",
          "readOnly": true
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mcp-server",
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
      },
      "ulimits": [
        {
          "name": "nofile",
          "softLimit": 65536,
          "hardLimit": 65536
        }
      ]
    }
  ],
  "volumes": [
    {
      "name": "docker-socket",
      "host": {
        "sourcePath": "/var/run/docker.sock"
      }
    }
  ],
  "placementConstraints": [
    {
      "type": "memberOf",
      "expression": "attribute:ecs.instance-type =~ t3.*"
    }
  ]
}
```

## Docker Compose Deployment

### Enhanced Docker Compose for Production

Create `docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  mcp-server:
    image: ${ECR_URI}/mcp-server:${VERSION:-latest}
    container_name: mcp-server
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=${LOG_LEVEL:-info}
      - MCP_AUTH_TOKEN=${MCP_AUTH_TOKEN}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
    volumes:
      - ./config:/app/config:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - mcp-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
        labels: "service=mcp-server"
    labels:
      - "com.mcp.service=server"
      - "com.mcp.version=${VERSION:-latest}"

  nginx:
    image: nginx:alpine
    container_name: mcp-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx-cache:/var/cache/nginx
    depends_on:
      - mcp-server
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: mcp-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    container_name: mcp-prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    ports:
      - "9090:9090"
    networks:
      - mcp-network

  node-exporter:
    image: prom/node-exporter:latest
    container_name: mcp-node-exporter
    restart: unless-stopped
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  redis-data:
  prometheus-data:
  nginx-cache:
```

## Container Management

### Health Monitoring Script

Create `monitor-containers.sh`:

```bash
#!/bin/bash
# Container Health Monitoring

# Check container health
check_health() {
    local container=$1
    local health=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null)
    
    if [ -z "$health" ]; then
        echo "Container $container not found"
        return 1
    fi
    
    case $health in
        healthy)
            echo "✓ $container is healthy"
            return 0
            ;;
        unhealthy)
            echo "✗ $container is unhealthy"
            docker logs --tail 50 $container
            return 1
            ;;
        starting)
            echo "⟳ $container is starting"
            return 0
            ;;
        *)
            echo "? $container status unknown: $health"
            return 1
            ;;
    esac
}

# Check all containers
echo "=== Container Health Check ==="
check_health mcp-server
check_health mcp-nginx
check_health mcp-redis

# Check resource usage
echo -e "\n=== Resource Usage ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Check disk usage
echo -e "\n=== Disk Usage ==="
df -h | grep -E "^/dev|Filesystem"
docker system df

# Check recent logs for errors
echo -e "\n=== Recent Errors ==="
docker logs mcp-server 2>&1 | grep -i error | tail -5

# Send metrics to CloudWatch
aws cloudwatch put-metric-data \
    --namespace "MCP/Docker" \
    --metric-name "ContainerHealth" \
    --value $(docker ps --filter "health=healthy" | wc -l) \
    --dimensions Instance=$(ec2-metadata --instance-id | cut -d' ' -f2)
```

### Backup and Recovery

Create `backup-docker-data.sh`:

```bash
#!/bin/bash
# Docker Data Backup Script

BACKUP_DIR="/backup/docker"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="s3://your-backup-bucket/docker-backups"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup Docker volumes
echo "Backing up Docker volumes..."
docker run --rm \
    -v redis-data:/source:ro \
    -v $BACKUP_DIR:/backup \
    alpine tar czf /backup/redis-data-$TIMESTAMP.tar.gz -C /source .

# Backup configurations
echo "Backing up configurations..."
tar czf $BACKUP_DIR/config-$TIMESTAMP.tar.gz \
    /opt/mcp-server/docker-compose*.yml \
    /opt/mcp-server/.env \
    /etc/nginx/conf.d/

# Upload to S3
echo "Uploading to S3..."
aws s3 cp $BACKUP_DIR/ $S3_BUCKET/ --recursive --exclude "*" --include "*-$TIMESTAMP.tar.gz"

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup complete!"
```

## Monitoring and Maintenance

### CloudWatch Dashboard

Create `cloudwatch-dashboard.json`:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["CWAgent", "mem_used_percent", {"stat": "Average"}],
          [".", "cpu_usage_active", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "EC2 Instance Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["ECS/ContainerInsights", "CpuUtilized", "ServiceName", "mcp-server"],
          [".", "MemoryUtilized", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Container Metrics"
      }
    }
  ]
}
```

### Automated Updates

Create `/etc/cron.d/mcp-updates`:

```cron
# Update MCP server weekly
0 2 * * 0 root /opt/mcp-server/scripts/update-containers.sh > /var/log/mcp-update.log 2>&1

# Backup daily
0 3 * * * root /opt/mcp-server/scripts/backup-docker-data.sh > /var/log/mcp-backup.log 2>&1

# Clean up old containers and images
0 4 * * * root docker system prune -af --filter "until=168h" > /var/log/docker-cleanup.log 2>&1
```

## Security Best Practices

1. **Container Security**
   - Run containers with non-root users
   - Use read-only root filesystems
   - Implement resource limits
   - Scan images for vulnerabilities

2. **Network Security**
   - Use custom bridge networks
   - Implement network policies
   - Enable TLS for all communications
   - Use secrets management

3. **Host Security**
   - Regular OS updates
   - Implement SELinux/AppArmor
   - Monitor for intrusions
   - Audit Docker daemon access

## Troubleshooting

### Common Issues

1. **Container Won't Start**
```bash
docker logs mcp-server
docker inspect mcp-server
journalctl -u mcp-server
```

2. **High Memory Usage**
```bash
docker stats
docker system prune -a
echo 3 > /proc/sys/vm/drop_caches
```

3. **Network Issues**
```bash
docker network ls
docker network inspect mcp-network
iptables -L -n
```

## Conclusion

This guide provides comprehensive instructions for deploying MCP Server as Docker containers on EC2 instances. Choose between standalone EC2 or ECS with EC2 based on your scaling and management requirements.