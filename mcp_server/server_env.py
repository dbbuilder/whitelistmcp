#!/usr/bin/env python3
"""
AWS Security Group MCP Server - Environment Variable Version
Model Context Protocol server for managing AWS security group rules
"""

import asyncio
import json
import logging
import sys
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import configuration manager
try:
    from config_manager import get_config, reload_config
    USE_CONFIG_MANAGER = True
except ImportError:
    print("Warning: config_manager not found. Using direct environment variables.")
    USE_CONFIG_MANAGER = False

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Import boto3 for AWS operations
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv('MCP_LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ActionType(str, Enum):
    """Supported action types"""
    ADD_RULE = "add_rule"
    REMOVE_RULE = "remove_rule"
    LIST_RULES = "list_rules"
    UPDATE_DESCRIPTION = "update_description"
    TEST_CONNECTION = "test_connection"

@dataclass
class SecurityGroupRule:
    """Security Group Rule data structure"""
    user_name: str
    user_ip: str
    port: str
    security_group_id: str
    resource_name: str
    description: Optional[str] = None
    
    def generate_description(self) -> str:
        """Generate standard description format using environment config"""
        if USE_CONFIG_MANAGER:
            from config_manager import format_description
            return format_description(self.resource_name, self.port, self.user_name)
        else:
            # Fallback to manual formatting
            timestamp = datetime.now().strftime(
                os.getenv('DESCRIPTION_TIMESTAMP_FORMAT', '%Y%m%d-%H%M')
            )
            prefix = os.getenv('DESCRIPTION_PREFIX', 'auto')
            separator = os.getenv('DESCRIPTION_SEPARATOR', '-')
            
            return separator.join([
                f"{self.resource_name} {separator} {self.port}",
                prefix,
                self.user_name,
                timestamp
            ])

class AWSSecurityGroupManager:
    """AWS Security Group management class"""
    
    def __init__(self):
        self.ec2_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize EC2 client with credentials from environment"""
        try:
            if USE_CONFIG_MANAGER:
                config = get_config()
                aws_config = config.get_aws_client_config()
            else:
                # Fallback to direct environment variables
                aws_config = {
                    'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
                    'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
                    'region_name': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
                }
            
            if not aws_config.get('aws_access_key_id') or not aws_config.get('aws_secret_access_key'):
                raise ValueError("AWS credentials not found in environment")
            
            self.ec2_client = boto3.client('ec2', **aws_config)
            logger.info("AWS EC2 client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize EC2 client: {e}")
            raise
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test AWS connection by listing security groups"""
        try:
            response = self.ec2_client.describe_security_groups()
            security_groups = response.get('SecurityGroups', [])
            
            # Get default security group from environment
            default_sg_id = os.getenv('DEFAULT_SECURITY_GROUP_ID', '')
            default_sg_info = None
            
            for sg in security_groups:
                if sg['GroupId'] == default_sg_id:
                    default_sg_info = {
                        "id": sg['GroupId'],
                        "name": sg.get('GroupName', 'N/A'),
                        "vpc_id": sg.get('VpcId', 'N/A')
                    }
                    break
            
            return {
                "success": True,
                "message": f"Successfully connected to AWS. Found {len(security_groups)} security groups.",
                "default_security_group": default_sg_info,
                "security_groups": [
                    {
                        "id": sg['GroupId'],
                        "name": sg.get('GroupName', 'N/A'),
                        "vpc_id": sg.get('VpcId', 'N/A')
                    }
                    for sg in security_groups[:5]  # Return first 5 for brevity
                ],
                "environment": {
                    "region": os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                    "has_config_manager": USE_CONFIG_MANAGER
                }
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_rule(self, rule: SecurityGroupRule) -> Dict[str, Any]:
        """Add a new security group rule"""
        try:
            # Validate based on environment settings
            if USE_CONFIG_MANAGER:
                config = get_config()
                validation = config.validation_settings
                
                # Validate port range
                if validation.get('validate_port', True):
                    port_num = int(rule.port)
                    if port_num < validation.get('min_port', 1) or port_num > validation.get('max_port', 65535):
                        return {
                            "success": False,
                            "error": f"Port {port_num} is outside allowed range"
                        }
            
            # Add /32 to IP if not present
            ip_address = rule.user_ip
            if '/' not in ip_address:
                ip_address = f"{ip_address}/32"
            
            # Generate description
            description = rule.description or rule.generate_description()
            
            # Check if rule already exists
            existing_rules = await self._get_rules_for_port(
                rule.security_group_id,
                int(rule.port)
            )
            
            for existing_rule in existing_rules:
                if existing_rule['ip'] == ip_address:
                    return {
                        "success": False,
                        "message": f"Rule already exists for {ip_address} on port {rule.port}",
                        "existing_rule": existing_rule
                    }
            
            # Create the new rule
            new_rule = {
                'IpProtocol': 'tcp',
                'FromPort': int(rule.port),
                'ToPort': int(rule.port),
                'IpRanges': [{'CidrIp': ip_address, 'Description': description}]
            }
            
            # Add the rule
            response = self.ec2_client.authorize_security_group_ingress(
                GroupId=rule.security_group_id,
                IpPermissions=[new_rule]
            )
            
            if response['Return']:
                logger.info(f"Successfully added rule for {ip_address} on port {rule.port}")
                
                # Log to audit file if enabled
                if os.getenv('ENABLE_AUDIT_LOG', 'true').lower() == 'true':
                    await self._log_audit_entry('add_rule', rule, ip_address, description)
                
                return {
                    "success": True,
                    "message": f"Successfully added rule for {ip_address} on port {rule.port}",
                    "rule": {
                        "ip": ip_address,
                        "port": rule.port,
                        "description": description
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to add rule"
                }
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS Client Error: {error_code} - {error_message}")
            return {
                "success": False,
                "error": f"{error_code}: {error_message}"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _log_audit_entry(self, action: str, rule: SecurityGroupRule, ip_address: str, description: str):
        """Log audit entry if enabled"""
        try:
            audit_log_path = os.getenv('AUDIT_LOG_PATH', './logs/audit.log')
            os.makedirs(os.path.dirname(audit_log_path), exist_ok=True)
            
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'security_group_id': rule.security_group_id,
                'ip_address': ip_address,
                'port': rule.port,
                'username': rule.user_name,
                'resource_name': rule.resource_name,
                'description': description
            }
            
            with open(audit_log_path, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    async def _get_rules_for_port(self, security_group_id: str, port: int) -> List[Dict[str, Any]]:
        """Get existing rules for a specific port"""
        try:
            response = self.ec2_client.describe_security_groups(
                GroupIds=[security_group_id]
            )
            
            if not response['SecurityGroups']:
                return []
            
            sg = response['SecurityGroups'][0]
            rules = []
            
            for rule in sg.get('IpPermissions', []):
                if rule.get('FromPort') == port and rule.get('ToPort') == port:
                    for ip_range in rule.get('IpRanges', []):
                        rules.append({
                            'ip': ip_range.get('CidrIp'),
                            'description': ip_range.get('Description', 'No description'),
                            'protocol': rule.get('IpProtocol')
                        })
            
            return rules
        except Exception as e:
            logger.error(f"Error getting rules: {e}")
            return []
    
    async def list_rules(self, security_group_id: str, port: Optional[str] = None) -> Dict[str, Any]:
        """List rules for a security group"""
        try:
            # Use default security group if not specified
            if not security_group_id and os.getenv('DEFAULT_SECURITY_GROUP_ID'):
                security_group_id = os.getenv('DEFAULT_SECURITY_GROUP_ID')
            
            response = self.ec2_client.describe_security_groups(
                GroupIds=[security_group_id]
            )
            
            if not response['SecurityGroups']:
                return {
                    "success": False,
                    "error": f"Security group {security_group_id} not found"
                }
            
            sg = response['SecurityGroups'][0]
            all_rules = []
            
            for rule in sg.get('IpPermissions', []):
                from_port = rule.get('FromPort')
                to_port = rule.get('ToPort')
                
                # Filter by port if specified
                if port and str(from_port) != port:
                    continue
                
                for ip_range in rule.get('IpRanges', []):
                    all_rules.append({
                        'port': from_port,
                        'ip': ip_range.get('CidrIp'),
                        'description': ip_range.get('Description', 'No description'),
                        'protocol': rule.get('IpProtocol')
                    })
            
            return {
                "success": True,
                "security_group": {
                    "id": sg['GroupId'],
                    "name": sg.get('GroupName', 'N/A'),
                    "vpc_id": sg.get('VpcId', 'N/A')
                },
                "rules": all_rules,
                "total": len(all_rules)
            }
            
        except Exception as e:
            logger.error(f"Error listing rules: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Create server instance
server_name = os.getenv('MCP_SERVER_NAME', 'aws-security-group-server')
server_version = os.getenv('MCP_SERVER_VERSION', '1.0.0')

server = Server(server_name)
aws_manager = AWSSecurityGroupManager()

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available resources"""
    return [
        types.Resource(
            uri="aws://security-group/manager",
            name="AWS Security Group Manager",
            description="Manage AWS EC2 Security Group rules with environment configuration",
            mimeType="application/json"
        ),
        types.Resource(
            uri="aws://security-group/config",
            name="Environment Configuration",
            description="Current environment configuration for AWS Security Group management",
            mimeType="application/json"
        )
    ]

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    # Get JSON template from environment
    json_template = os.getenv('JSON_TEMPLATE', '{}')
    try:
        template = json.loads(json_template)
    except:
        template = {
            "UserName": "string",
            "UserIP": "string",
            "Port": "string",
            "SecurityGroupID": "string",
            "ResourceName": "string"
        }
    
    return [
        types.Tool(
            name="add_security_group_rule",
            description="Add an IP address to a security group",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "Username for the rule description",
                        "default": os.getenv('DEFAULT_USERNAME', 'user')
                    },
                    "user_ip": {
                        "type": "string",
                        "description": "IP address to whitelist"
                    },
                    "port": {
                        "type": "string",
                        "description": "Port number to allow access"
                    },
                    "security_group_id": {
                        "type": "string",
                        "description": "AWS Security Group ID",
                        "default": os.getenv('DEFAULT_SECURITY_GROUP_ID', '')
                    },
                    "resource_name": {
                        "type": "string",
                        "description": "Resource name for the description",
                        "default": os.getenv('DEFAULT_RESOURCE_NAME', 'Resource')
                    }
                },
                "required": ["user_name", "user_ip", "port", "security_group_id", "resource_name"]
            }
        ),
        types.Tool(
            name="list_security_group_rules",
            description="List rules for a security group",
            inputSchema={
                "type": "object",
                "properties": {
                    "security_group_id": {
                        "type": "string",
                        "description": "AWS Security Group ID",
                        "default": os.getenv('DEFAULT_SECURITY_GROUP_ID', '')
                    },
                    "port": {
                        "type": "string",
                        "description": "Optional: filter by specific port"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="test_aws_connection",
            description="Test AWS connectivity and list available security groups",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="show_configuration",
            description="Show current environment configuration",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any]
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""
    
    try:
        if name == "test_aws_connection":
            result = await aws_manager.test_connection()
            
        elif name == "add_security_group_rule":
            # Apply defaults from environment
            if not arguments.get("security_group_id") and os.getenv('DEFAULT_SECURITY_GROUP_ID'):
                arguments["security_group_id"] = os.getenv('DEFAULT_SECURITY_GROUP_ID')
            
            rule = SecurityGroupRule(
                user_name=arguments["user_name"],
                user_ip=arguments["user_ip"],
                port=arguments["port"],
                security_group_id=arguments["security_group_id"],
                resource_name=arguments["resource_name"]
            )
            result = await aws_manager.add_rule(rule)
            
        elif name == "list_security_group_rules":
            result = await aws_manager.list_rules(
                security_group_id=arguments.get("security_group_id", ""),
                port=arguments.get("port")
            )
            
        elif name == "show_configuration":
            if USE_CONFIG_MANAGER:
                config = get_config()
                result = {
                    "success": True,
                    "configuration": config.export_config()
                }
            else:
                result = {
                    "success": True,
                    "configuration": {
                        "aws_region": os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                        "default_security_group": os.getenv('DEFAULT_SECURITY_GROUP_ID', ''),
                        "description_format": {
                            "prefix": os.getenv('DESCRIPTION_PREFIX', 'auto'),
                            "separator": os.getenv('DESCRIPTION_SEPARATOR', '-'),
                            "timestamp_format": os.getenv('DESCRIPTION_TIMESTAMP_FORMAT', '%Y%m%d-%H%M')
                        },
                        "audit_enabled": os.getenv('ENABLE_AUDIT_LOG', 'true').lower() == 'true'
                    }
                }
            
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )
        ]
        
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )
        ]

async def main():
    """Main entry point"""
    logger.info(f"Starting {server_name} v{server_version}")
    
    # Load environment file if specified
    env_file = os.getenv('ENV_FILE', '.env')
    if USE_CONFIG_MANAGER and os.path.exists(env_file):
        reload_config(env_file)
        logger.info(f"Loaded environment from {env_file}")
    
    # Validate configuration
    if USE_CONFIG_MANAGER:
        config = get_config()
        if config.validate_configuration():
            logger.info("Configuration validated successfully")
        else:
            logger.error("Configuration validation failed")
    
    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=server_name,
                server_version=server_version,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
