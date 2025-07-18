#!/bin/bash
# Deploy MCP Server to AWS
# Usage: ./deploy-to-aws.sh [ecs|ec2|lambda] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DEPLOYMENT_TYPE=${1:-ecs}
REGION=${AWS_REGION:-us-east-1}
STACK_NAME=${STACK_NAME:-mcp-server}
AUTH_TOKEN=${MCP_AUTH_TOKEN:-$(openssl rand -base64 32)}

echo -e "${GREEN}AWS MCP Server Deployment Script${NC}"
echo "=================================="
echo "Deployment Type: $DEPLOYMENT_TYPE"
echo "Region: $REGION"
echo "Stack Name: $STACK_NAME"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI not found. Please install it first.${NC}"
        exit 1
    fi
    
    # Check Docker (for ECS deployment)
    if [[ "$DEPLOYMENT_TYPE" == "ecs" ]] && ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker not found. Please install it for ECS deployment.${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}AWS credentials not configured. Please run 'aws configure'.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Prerequisites check passed!${NC}"
}

# Function to build and push Docker image
build_and_push_image() {
    echo -e "${YELLOW}Building and pushing Docker image...${NC}"
    
    # Get account ID and ECR URI
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
    ECR_REPO="$STACK_NAME"
    
    # Create ECR repository if it doesn't exist
    aws ecr describe-repositories --repository-names $ECR_REPO --region $REGION 2>/dev/null || \
        aws ecr create-repository --repository-name $ECR_REPO --region $REGION
    
    # Login to ECR
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI
    
    # Build image
    docker build -f Dockerfile.remote -t $ECR_REPO:latest .
    
    # Tag and push
    docker tag $ECR_REPO:latest $ECR_URI/$ECR_REPO:latest
    docker push $ECR_URI/$ECR_REPO:latest
    
    echo -e "${GREEN}Docker image pushed successfully!${NC}"
    echo "Image URI: $ECR_URI/$ECR_REPO:latest"
}

# Function to deploy ECS stack
deploy_ecs() {
    echo -e "${YELLOW}Deploying ECS Fargate stack...${NC}"
    
    # Build and push image first
    build_and_push_image
    
    # Get VPC and Subnets
    VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text)
    SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[?MapPublicIpOnLaunch==\`true\`].SubnetId" --output text | tr '\t' ',')
    
    # Deploy CloudFormation stack
    aws cloudformation deploy \
        --template-file aws/cloudformation/mcp-server-ecs.yaml \
        --stack-name $STACK_NAME \
        --parameter-overrides \
            VpcId=$VPC_ID \
            SubnetIds=$SUBNET_IDS \
            AuthToken=$AUTH_TOKEN \
            DockerImage=$ECR_URI/$ECR_REPO:latest \
        --capabilities CAPABILITY_IAM \
        --region $REGION
    
    # Get outputs
    echo -e "${GREEN}Deployment complete!${NC}"
    echo ""
    echo "Stack Outputs:"
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs' \
        --output table
}

# Function to deploy EC2 instance
deploy_ec2() {
    echo -e "${YELLOW}Deploying to EC2 instance...${NC}"
    
    # Get latest Amazon Linux 2 AMI
    AMI_ID=$(aws ec2 describe-images \
        --owners amazon \
        --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
        --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
        --output text)
    
    # Create key pair if it doesn't exist
    KEY_NAME="$STACK_NAME-key"
    if ! aws ec2 describe-key-pairs --key-names $KEY_NAME 2>/dev/null; then
        aws ec2 create-key-pair --key-name $KEY_NAME --query 'KeyMaterial' --output text > $KEY_NAME.pem
        chmod 400 $KEY_NAME.pem
        echo -e "${YELLOW}Created new key pair: $KEY_NAME.pem${NC}"
    fi
    
    # Create security group
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$STACK_NAME-sg" \
        --description "Security group for MCP server" \
        --query 'GroupId' \
        --output text)
    
    # Allow HTTPS
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0
    
    # Allow SSH (restrict this in production!)
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0
    
    # Create user data script
    cat > /tmp/user-data.sh << EOF
#!/bin/bash
yum update -y
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user

# Install docker-compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repository
cd /opt
git clone https://github.com/InspirationAI/mcp-servers.git
cd mcp-servers

# Create .env file
echo "MCP_AUTH_TOKEN=$AUTH_TOKEN" > .env

# Start services
docker-compose -f docker-compose.remote.yml up -d
EOF
    
    # Launch instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --instance-type t3.small \
        --key-name $KEY_NAME \
        --security-group-ids $SG_ID \
        --user-data file:///tmp/user-data.sh \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$STACK_NAME}]" \
        --query 'Instances[0].InstanceId' \
        --output text)
    
    echo -e "${GREEN}EC2 instance launched!${NC}"
    echo "Instance ID: $INSTANCE_ID"
    echo "Waiting for instance to be running..."
    
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID
    
    # Get public IP
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    echo -e "${GREEN}Instance is running!${NC}"
    echo "Public IP: $PUBLIC_IP"
    echo "SSH: ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP"
    echo "MCP Server will be available at: https://$PUBLIC_IP (after setup completes)"
}

# Function to deploy Lambda
deploy_lambda() {
    echo -e "${YELLOW}Deploying Lambda function...${NC}"
    
    # Create deployment package
    mkdir -p /tmp/lambda-package
    cd /tmp/lambda-package
    
    # Install dependencies
    pip install awswhitelist-mcp -t .
    
    # Create handler
    cat > lambda_handler.py << 'EOF'
import json
import os
from awswhitelist.mcp.handler import MCPHandler

mcp_handler = MCPHandler()

def lambda_handler(event, context):
    auth_token = os.environ.get('MCP_AUTH_TOKEN')
    if auth_token:
        provided_token = event.get('headers', {}).get('Authorization', '').replace('Bearer ', '')
        if provided_token != auth_token:
            return {'statusCode': 401, 'body': json.dumps({'error': 'Unauthorized'})}
    
    try:
        body = json.loads(event['body'])
        response = mcp_handler.handle_request(body)
        
        if response is None:
            return {'statusCode': 204}
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(response)
        }
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
EOF
    
    # Create ZIP
    zip -r /tmp/mcp-lambda.zip .
    cd -
    
    # Create IAM role for Lambda
    ROLE_NAME="$STACK_NAME-lambda-role"
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' 2>/dev/null || true
    
    # Attach policies
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    # Wait for role to be available
    sleep 10
    
    # Create Lambda function
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    aws lambda create-function \
        --function-name $STACK_NAME \
        --runtime python3.11 \
        --role arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME \
        --handler lambda_handler.lambda_handler \
        --zip-file fileb:///tmp/mcp-lambda.zip \
        --timeout 30 \
        --memory-size 512 \
        --environment Variables={MCP_AUTH_TOKEN=$AUTH_TOKEN} \
        2>/dev/null || \
    aws lambda update-function-code \
        --function-name $STACK_NAME \
        --zip-file fileb:///tmp/mcp-lambda.zip
    
    # Create API Gateway
    API_ID=$(aws apigatewayv2 create-api \
        --name "$STACK_NAME-api" \
        --protocol-type HTTP \
        --target arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$STACK_NAME \
        --query 'ApiId' \
        --output text)
    
    # Add Lambda permission
    aws lambda add-permission \
        --function-name $STACK_NAME \
        --statement-id api-gateway \
        --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        2>/dev/null || true
    
    # Get API endpoint
    API_ENDPOINT=$(aws apigatewayv2 get-api \
        --api-id $API_ID \
        --query 'ApiEndpoint' \
        --output text)
    
    echo -e "${GREEN}Lambda deployment complete!${NC}"
    echo "API Endpoint: $API_ENDPOINT"
}

# Function to display Claude Desktop config
show_config() {
    echo ""
    echo -e "${GREEN}Claude Desktop Configuration:${NC}"
    echo "Add this to your claude_desktop_config.json:"
    echo ""
    
    if [[ "$DEPLOYMENT_TYPE" == "ecs" ]]; then
        ALB_URL=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
            --output text)
        URL="$ALB_URL/mcp"
    elif [[ "$DEPLOYMENT_TYPE" == "ec2" ]]; then
        URL="https://$PUBLIC_IP/mcp"
    else
        URL="$API_ENDPOINT"
    fi
    
    cat << EOF
{
  "mcpServers": {
    "awswhitelist-remote": {
      "command": "python",
      "args": ["-m", "scripts.mcp-remote-proxy"],
      "env": {
        "MCP_REMOTE_URL": "$URL",
        "MCP_AUTH_TOKEN": "$AUTH_TOKEN"
      }
    }
  }
}
EOF
}

# Main execution
check_prerequisites

case $DEPLOYMENT_TYPE in
    ecs)
        deploy_ecs
        ;;
    ec2)
        deploy_ec2
        ;;
    lambda)
        deploy_lambda
        ;;
    *)
        echo -e "${RED}Unknown deployment type: $DEPLOYMENT_TYPE${NC}"
        echo "Usage: $0 [ecs|ec2|lambda]"
        exit 1
        ;;
esac

show_config

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo "Auth Token: $AUTH_TOKEN"
echo "(Save this token - you'll need it for Claude Desktop configuration)"