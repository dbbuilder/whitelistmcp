#!/usr/bin/env python3
"""
AWS Security Group MCP Server
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

# Add parent directory to path to import the security group module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'simple_test'))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Import boto3 for AWS operations
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_CREDENTIALS = {
    'access_key': 'AKIAXEFUNA23JDGJOV67',
    'secret_key': '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',
    'region': 'us-east-1'
}

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
        """Generate standard description format"""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M')
        return f"{self.resource_name} - {self.port}-auto-{self.user_name}-{timestamp}"

class AWSSecurityGroupManager:
    """AWS Security Group management class"""
    
    def __init__(self):
        self.ec2_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize EC2 client with credentials"""
        try:
            self.ec2_client = boto3.client(
                'ec2',
                aws_access_key_id=AWS_CREDENTIALS['access_key'],
                aws_secret_access_key=AWS_CREDENTIALS['secret_key'],
                region_name=AWS_CREDENTIALS['region']
            )
            logger.info("AWS EC2 client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EC2 client: {e}")
            raise
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test AWS connection by listing security groups"""
        try:
            response = self.ec2_client.describe_security_groups()
            security_groups = response.get('SecurityGroups', [])
            
            return {
                "success": True,
                "message": f"Successfully connected to AWS. Found {len(security_groups)} security groups.",
                "security_groups": [
                    {
                        "id": sg['GroupId'],
                        "name": sg.get('GroupName', 'N/A'),
                        "vpc_id": sg.get('VpcId', 'N/A')
                    }
                    for sg in security_groups[:5]  # Return first 5 for brevity
                ]
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
server = Server("aws-security-group-server")
aws_manager = AWSSecurityGroupManager()

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available resources"""
    return [
        types.Resource(
            uri="aws://security-group/manager",
            name="AWS Security Group Manager",
            description="Manage AWS EC2 Security Group rules",
            mimeType="application/json"
        )
    ]

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="add_security_group_rule",
            description="Add an IP address to a security group",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "Username for the rule description"
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
                        "description": "AWS Security Group ID"
                    },
                    "resource_name": {
                        "type": "string",
                        "description": "Resource name for the description"
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
                        "description": "AWS Security Group ID"
                    },
                    "port": {
                        "type": "string",
                        "description": "Optional: filter by specific port"
                    }
                },
                "required": ["security_group_id"]
            }
        ),
        types.Tool(
            name="test_aws_connection",
            description="Test AWS connectivity and list available security groups",
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
                security_group_id=arguments["security_group_id"],
                port=arguments.get("port")
            )
            
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
    logger.info("Starting AWS Security Group MCP Server")
    
    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="aws-security-group-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
