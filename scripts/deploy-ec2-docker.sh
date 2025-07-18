#!/bin/bash
# One-click EC2 Docker Deployment for MCP Server
# Usage: ./deploy-ec2-docker.sh

set -e

# Configuration
STACK_NAME="${STACK_NAME:-mcp-docker-server}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.small}"
KEY_NAME="${KEY_NAME:-mcp-docker-key}"
AUTH_TOKEN="${MCP_AUTH_TOKEN:-$(openssl rand -base64 32)}"
REGION="${AWS_REGION:-us-east-1}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== MCP Server EC2 Docker Deployment ===${NC}"
echo "Instance Type: $INSTANCE_TYPE"
echo "Region: $REGION"
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI not installed${NC}"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}Error: AWS credentials not configured${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Prerequisites check passed${NC}"
}

# Create key pair
create_keypair() {
    echo -e "${YELLOW}Creating EC2 key pair...${NC}"
    
    if aws ec2 describe-key-pairs --key-names $KEY_NAME &> /dev/null; then
        echo "Key pair $KEY_NAME already exists"
    else
        aws ec2 create-key-pair \
            --key-name $KEY_NAME \
            --query 'KeyMaterial' \
            --output text > ${KEY_NAME}.pem
        chmod 400 ${KEY_NAME}.pem
        echo -e "${GREEN}✓ Created key pair: ${KEY_NAME}.pem${NC}"
    fi
}

# Create security group
create_security_group() {
    echo -e "${YELLOW}Creating security group...${NC}"
    
    VPC_ID=$(aws ec2 describe-vpcs \
        --filters "Name=is-default,Values=true" \
        --query "Vpcs[0].VpcId" \
        --output text)
    
    # Check if security group exists
    SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=${STACK_NAME}-sg" \
        --query "SecurityGroups[0].GroupId" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
        SG_ID=$(aws ec2 create-security-group \
            --group-name "${STACK_NAME}-sg" \
            --description "Security group for MCP Docker server" \
            --vpc-id $VPC_ID \
            --query 'GroupId' \
            --output text)
        
        # Add rules
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --protocol tcp --port 22 --cidr 0.0.0.0/0
        
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --protocol tcp --port 443 --cidr 0.0.0.0/0
        
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --protocol tcp --port 80 --cidr 0.0.0.0/0
        
        echo -e "${GREEN}✓ Created security group: $SG_ID${NC}"
    else
        echo "Security group already exists: $SG_ID"
    fi
}

# Create IAM role
create_iam_role() {
    echo -e "${YELLOW}Creating IAM role...${NC}"
    
    ROLE_NAME="${STACK_NAME}-role"
    
    # Check if role exists
    if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
        echo "IAM role $ROLE_NAME already exists"
    else
        # Create role
        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document '{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }' > /dev/null
        
        # Attach policies
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
        
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
        
        # Create custom policy for MCP operations
        aws iam put-role-policy \
            --role-name $ROLE_NAME \
            --policy-name MCPPolicy \
            --policy-document '{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": [
                        "ec2:DescribeSecurityGroups",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:RevokeSecurityGroupIngress",
                        "sts:GetCallerIdentity",
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage"
                    ],
                    "Resource": "*"
                }]
            }'
        
        echo -e "${GREEN}✓ Created IAM role: $ROLE_NAME${NC}"
    fi
    
    # Create instance profile
    PROFILE_NAME="${STACK_NAME}-profile"
    if ! aws iam get-instance-profile --instance-profile-name $PROFILE_NAME &> /dev/null; then
        aws iam create-instance-profile --instance-profile-name $PROFILE_NAME > /dev/null
        aws iam add-role-to-instance-profile \
            --instance-profile-name $PROFILE_NAME \
            --role-name $ROLE_NAME
        sleep 5  # Wait for propagation
    fi
}

# Create user data script
create_user_data() {
    cat > /tmp/user-data.sh << 'USERDATA'
#!/bin/bash
set -e

# Update system
yum update -y

# Install Docker
amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install additional tools
yum install -y git htop amazon-cloudwatch-agent

# Create application directory
mkdir -p /opt/mcp-server
cd /opt/mcp-server

# Clone repository
git clone https://github.com/InspirationAI/mcp-servers.git .

# Create environment file
cat > .env << EOF
MCP_AUTH_TOKEN=AUTH_TOKEN_PLACEHOLDER
LOG_LEVEL=INFO
AWS_DEFAULT_REGION=REGION_PLACEHOLDER
EOF

# Start services
docker-compose -f docker-compose.remote.yml up -d

# Install Nginx
amazon-linux-extras install nginx1 -y

# Configure Nginx
cat > /etc/nginx/conf.d/mcp.conf << 'NGINX'
server {
    listen 80;
    server_name _;
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name _;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location /health {
        proxy_pass http://localhost:8080;
        access_log off;
    }
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINX

# Create self-signed certificate
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=MCP/CN=mcp-server"

# Start Nginx
systemctl enable nginx
systemctl start nginx

# Setup auto-start
cat > /etc/systemd/system/mcp-docker.service << 'SYSTEMD'
[Unit]
Description=MCP Docker Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/mcp-server
ExecStart=/usr/local/bin/docker-compose -f docker-compose.remote.yml up
ExecStop=/usr/local/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable mcp-docker

echo "MCP Server Docker setup complete!"
USERDATA

    # Replace placeholders
    sed -i "s/AUTH_TOKEN_PLACEHOLDER/$AUTH_TOKEN/g" /tmp/user-data.sh
    sed -i "s/REGION_PLACEHOLDER/$REGION/g" /tmp/user-data.sh
}

# Launch EC2 instance
launch_instance() {
    echo -e "${YELLOW}Launching EC2 instance...${NC}"
    
    # Get latest Amazon Linux 2 AMI
    AMI_ID=$(aws ssm get-parameters \
        --names /aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2 \
        --query 'Parameters[0].Value' \
        --output text)
    
    # Launch instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --instance-type $INSTANCE_TYPE \
        --key-name $KEY_NAME \
        --security-group-ids $SG_ID \
        --iam-instance-profile Name=${STACK_NAME}-profile \
        --user-data file:///tmp/user-data.sh \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$STACK_NAME}]" \
        --block-device-mappings '[{
            "DeviceName": "/dev/xvda",
            "Ebs": {
                "VolumeSize": 20,
                "VolumeType": "gp3",
                "DeleteOnTermination": true
            }
        }]' \
        --query 'Instances[0].InstanceId' \
        --output text)
    
    echo -e "${GREEN}✓ Instance launched: $INSTANCE_ID${NC}"
    echo "Waiting for instance to be running..."
    
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID
    
    # Get instance details
    INSTANCE_INFO=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].[PublicIpAddress,PrivateIpAddress,PublicDnsName]' \
        --output text)
    
    PUBLIC_IP=$(echo $INSTANCE_INFO | cut -f1)
    PRIVATE_IP=$(echo $INSTANCE_INFO | cut -f2)
    PUBLIC_DNS=$(echo $INSTANCE_INFO | cut -f3)
    
    echo -e "${GREEN}✓ Instance is running!${NC}"
}

# Display results
display_results() {
    echo ""
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
    echo ""
    echo "Instance ID: $INSTANCE_ID"
    echo "Public IP: $PUBLIC_IP"
    echo "Public DNS: $PUBLIC_DNS"
    echo "Private IP: $PRIVATE_IP"
    echo ""
    echo "SSH Access:"
    echo "  ssh -i ${KEY_NAME}.pem ec2-user@$PUBLIC_IP"
    echo ""
    echo "MCP Server URL (wait 2-3 minutes for setup):"
    echo "  https://$PUBLIC_IP"
    echo ""
    echo "Auth Token: $AUTH_TOKEN"
    echo ""
    echo -e "${YELLOW}Claude Desktop Configuration:${NC}"
    cat << EOF
{
  "mcpServers": {
    "awswhitelist-ec2": {
      "command": "python",
      "args": ["-m", "scripts.mcp-remote-proxy"],
      "env": {
        "MCP_REMOTE_URL": "https://$PUBLIC_IP/mcp",
        "MCP_AUTH_TOKEN": "$AUTH_TOKEN"
      }
    }
  }
}
EOF
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Wait 2-3 minutes for Docker containers to start"
    echo "2. Test the health endpoint: curl -k https://$PUBLIC_IP/health"
    echo "3. Configure Claude Desktop with the above configuration"
    echo "4. (Optional) Set up a domain name and proper SSL certificate"
}

# Main execution
main() {
    check_prerequisites
    create_keypair
    create_security_group
    create_iam_role
    create_user_data
    launch_instance
    display_results
    
    # Clean up
    rm -f /tmp/user-data.sh
}

# Run main function
main