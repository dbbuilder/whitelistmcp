"""MCP protocol handler for AWS whitelisting operations."""

from typing import Dict, Any, Optional, Callable, List, Union
from pydantic import BaseModel, field_validator

from whitelistmcp import __version__
from whitelistmcp.config import Config, get_port_number
from whitelistmcp.utils.credential_validator import (
    AWSCredentials,
    validate_credentials,
    CredentialValidationError
)
from whitelistmcp.utils.ip_validator import (
    normalize_ip_input,
    IPValidationError
)
from whitelistmcp.aws.service import (
    AWSService,
    SecurityGroupRule,
    WhitelistResult,
    create_rule_description
)
from whitelistmcp.azure.service import AzureCredentials
from whitelistmcp.gcp.service import GCPCredentials
from whitelistmcp.cloud_service import (
    CloudServiceManager,
    CloudCredentials,
    UnifiedWhitelistResult
)
from whitelistmcp.config import CloudProvider


# MCP Error Codes
ERROR_PARSE = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32603


class MCPError(BaseModel):
    """MCP error object."""
    
    code: int
    message: str
    data: Optional[Any] = None


class MCPRequest(BaseModel):
    """MCP request object."""
    
    jsonrpc: str
    id: Optional[Union[str, int]] = None  # Notifications don't have id
    method: str
    params: Dict[str, Any] = {}
    
    @field_validator("jsonrpc")
    def validate_jsonrpc(cls, v: str) -> str:
        """Validate JSON-RPC version."""
        if v != "2.0":
            raise ValueError("JSON-RPC version must be 2.0")
        return v


class MCPResponse(BaseModel):
    """MCP response object."""
    
    jsonrpc: str = "2.0"
    id: Union[str, int]
    result: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None
    
    @field_validator("error")
    def validate_response(cls, v: Optional[MCPError], info: Any) -> Optional[MCPError]:
        """Validate that either result or error is set, not both."""
        if v is not None and info.data.get("result") is not None:
            raise ValueError("Response cannot have both result and error")
        return v


def validate_mcp_request(request_data: Any) -> MCPRequest:
    """Validate and parse MCP request data.
    
    Args:
        request_data: Raw request data
    
    Returns:
        Validated MCPRequest object
    
    Raises:
        ValueError: If request is invalid
    """
    if not isinstance(request_data, dict):
        raise ValueError("Request must be a JSON object")
    
    return MCPRequest(**request_data)


def create_mcp_response(request_id: str, result: Dict[str, Any]) -> MCPResponse:
    """Create a successful MCP response.
    
    Args:
        request_id: Request ID to echo back
        result: Result data
    
    Returns:
        MCPResponse object
    """
    return MCPResponse(
        id=request_id,
        result=result
    )


def create_mcp_error(
    request_id: Union[str, int],
    code: int,
    message: str,
    data: Optional[Any] = None
) -> MCPResponse:
    """Create an error MCP response.
    
    Args:
        request_id: Request ID to echo back
        code: Error code
        message: Error message
        data: Optional error data
    
    Returns:
        MCPResponse object with error
    """
    return MCPResponse(
        id=request_id,
        error=MCPError(
            code=code,
            message=message,
            data=data
        )
    )


class MCPHandler:
    """Handler for MCP protocol requests."""
    
    def __init__(self, config: Config):
        """Initialize MCP handler.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.cloud_manager = CloudServiceManager(config)
        self.methods: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "prompts/list": self._handle_prompts_list,
            "whitelist_add": self._handle_whitelist_add,
            "whitelist_remove": self._handle_whitelist_remove,
            "whitelist_list": self._handle_whitelist_list,
            "whitelist_check": self._handle_whitelist_check
        }
        
        # Map tool names to handlers for tools/call dispatch
        self.tool_handlers = {
            "whitelist_add": self._handle_whitelist_add,
            "whitelist_remove": self._handle_whitelist_remove,
            "whitelist_list": self._handle_whitelist_list,
            "whitelist_check": self._handle_whitelist_check
        }
    
    def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request.
        
        Args:
            request: Validated MCP request
        
        Returns:
            MCP response
        """
        # Check if method exists
        if request.method not in self.methods:
            return create_mcp_error(
                request.id,
                ERROR_METHOD_NOT_FOUND,
                f"Method not found: {request.method}"
            )
        
        # Call method handler
        try:
            handler = self.methods[request.method]
            return handler(request)
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INTERNAL,
                "Internal error",
                {"error": str(e)}
            )
    
    def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle initialize method.
        
        Args:
            request: MCP request
        
        Returns:
            MCP response with server capabilities
        """
        return create_mcp_response(
            request.id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "whitelistmcp",
                    "version": __version__
                }
            }
        )
    
    def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/list method.
        
        Args:
            request: MCP request
        
        Returns:
            MCP response with available tools
        """
        # Define credential schemas for each cloud
        aws_credential_schema = {
            "type": "object",
            "properties": {
                "access_key_id": {"type": "string"},
                "secret_access_key": {"type": "string"},
                "region": {"type": "string"},
                "session_token": {"type": "string"}
            },
            "required": ["access_key_id", "secret_access_key", "region"]
        }
        
        azure_credential_schema = {
            "type": "object",
            "properties": {
                "client_id": {"type": "string"},
                "client_secret": {"type": "string"},
                "tenant_id": {"type": "string"},
                "subscription_id": {"type": "string"},
                "region": {"type": "string"}
            },
            "required": ["client_id", "client_secret", "tenant_id", "subscription_id"]
        }
        
        gcp_credential_schema = {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "credentials_path": {"type": "string"},
                "region": {"type": "string"},
                "zone": {"type": "string"}
            },
            "required": ["project_id"]
        }
        
        # Combined credential schema for multi-cloud
        multi_cloud_credential_schema = {
            "type": "object",
            "properties": {
                "cloud": {"type": "string", "enum": ["aws", "azure", "gcp", "all"]},
                "aws_credentials": aws_credential_schema,
                "azure_credentials": azure_credential_schema,
                "gcp_credentials": gcp_credential_schema
            },
            "required": ["cloud"]
        }
        
        tools = [
            {
                "name": "whitelist_add",
                "description": "Add an IP address to security groups/firewalls across AWS, Azure, and/or GCP",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials": multi_cloud_credential_schema,
                        "security_group_id": {
                            "type": "string",
                            "description": "AWS Security Group ID (e.g., sg-12345678)"
                        },
                        "nsg_name": {"type": "string", "description": "Azure Network Security Group name"},
                        "resource_group": {"type": "string", "description": "Azure Resource Group name"},
                        "firewall_name": {
                            "type": "string",
                            "description": "GCP Firewall rule name (auto-generated if not provided)"
                        },
                        "ip_address": {"type": "string", "description": "IP address or CIDR block to whitelist"},
                        "port": {
                            "type": "integer",
                            "description": "Port number (default from config)",
                            "minimum": 1,
                            "maximum": 65535
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["tcp", "udp", "icmp"],
                            "description": "Protocol (default: tcp)"
                        },
                        "description": {"type": "string", "description": "Description for the rule"},
                        "service_name": {"type": "string", "description": "Service name (e.g., ssh, https)"}
                    },
                    "required": ["credentials", "ip_address"]
                }
            },
            {
                "name": "whitelist_remove",
                "description": "Remove rules from security groups/firewalls by IP, service, or combination",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials": multi_cloud_credential_schema,
                        "security_group_id": {
                            "type": "string",
                            "description": "AWS Security Group ID (e.g., sg-12345678)"
                        },
                        "nsg_name": {"type": "string", "description": "Azure Network Security Group name"},
                        "resource_group": {"type": "string", "description": "Azure Resource Group name"},
                        "ip_address": {"type": "string", "description": "IP address to remove (optional)"},
                        "port": {
                            "type": "integer",
                            "description": "Port number to remove (optional)",
                            "minimum": 1,
                            "maximum": 65535
                        },
                        "service_name": {"type": "string", "description": "Service name to remove (optional)"},
                        "protocol": {
                            "type": "string",
                            "enum": ["tcp", "udp", "icmp"],
                            "description": "Protocol (default: tcp)"
                        }
                    },
                    "required": ["credentials"]
                }
            },
            {
                "name": "whitelist_list",
                "description": "List all whitelisted rules in security groups/firewalls",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials": multi_cloud_credential_schema,
                        "security_group_id": {
                            "type": "string",
                            "description": "AWS Security Group ID (e.g., sg-12345678)"
                        },
                        "nsg_name": {"type": "string", "description": "Azure Network Security Group name"},
                        "resource_group": {"type": "string", "description": "Azure Resource Group name"}
                    },
                    "required": ["credentials"]
                }
            },
            {
                "name": "whitelist_check",
                "description": "Check if an IP/port combination is whitelisted",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials": multi_cloud_credential_schema,
                        "security_group_id": {
                            "type": "string",
                            "description": "AWS Security Group ID (e.g., sg-12345678)"
                        },
                        "nsg_name": {"type": "string", "description": "Azure Network Security Group name"},
                        "resource_group": {"type": "string", "description": "Azure Resource Group name"},
                        "ip_address": {"type": "string", "description": "IP address or CIDR block to check"},
                        "port": {
                            "type": "integer",
                            "description": "Port number to check (optional)",
                            "minimum": 1,
                            "maximum": 65535
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["tcp", "udp", "icmp"],
                            "description": "Protocol (default: tcp)"
                        }
                    },
                    "required": ["credentials", "ip_address"]
                }
            }
        ]
        
        return create_mcp_response(request.id, {"tools": tools})
    
    def _handle_resources_list(self, request: MCPRequest) -> MCPResponse:
        """Handle resources/list method.
        
        Args:
            request: MCP request
        
        Returns:
            MCP response with available resources (empty for this server)
        """
        # This server doesn't provide any resources
        return create_mcp_response(request.id, {"resources": []})
    
    def _handle_prompts_list(self, request: MCPRequest) -> MCPResponse:
        """Handle prompts/list method.
        
        Args:
            request: MCP request
        
        Returns:
            MCP response with available prompts (empty for this server)
        """
        # This server doesn't provide any prompts
        return create_mcp_response(request.id, {"prompts": []})
    
    def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/call method.
        
        Args:
            request: MCP request with tool name and arguments
        
        Returns:
            MCP response with tool execution result
        """
        params = request.params
        
        # Validate required parameters
        if "name" not in params:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                "Missing required parameter: name"
            )
        
        tool_name = params["name"]
        
        # Check if tool exists
        if tool_name not in self.tool_handlers:
            return create_mcp_error(
                request.id,
                ERROR_METHOD_NOT_FOUND,
                f"Tool not found: {tool_name}"
            )
        
        # Get tool arguments
        tool_args = params.get("arguments", {})
        
        # Create a new request with the tool's parameters
        tool_request = MCPRequest(
            jsonrpc="2.0",
            id=request.id,
            method=tool_name,
            params=tool_args
        )
        
        # Dispatch to the appropriate tool handler
        return self.tool_handlers[tool_name](tool_request)
    
    def _validate_credentials_param(self, params: Dict[str, Any]) -> CloudCredentials:
        """Validate and extract cloud credentials from parameters.
        
        Args:
            params: Request parameters
        
        Returns:
            CloudCredentials object
        
        Raises:
            ValueError: If credentials are invalid
        """
        if "credentials" not in params:
            raise ValueError("Missing required parameter: credentials")
        
        cred_data = params["credentials"]
        if not isinstance(cred_data, dict):
            raise ValueError("Credentials must be an object")
        
        # Extract cloud provider
        cloud = cred_data.get("cloud", self.config.default_parameters.cloud_provider.value)
        try:
            cloud_provider = CloudProvider(cloud)
        except ValueError:
            raise ValueError(f"Invalid cloud provider: {cloud}")
        
        # Create CloudCredentials object
        cloud_creds = CloudCredentials(cloud=cloud_provider)
        
        # Extract AWS credentials if needed
        if cloud_provider in [CloudProvider.AWS, CloudProvider.ALL]:
            aws_creds = cred_data.get("aws_credentials")
            if aws_creds:
                try:
                    cloud_creds.aws_credentials = AWSCredentials(
                        access_key_id=aws_creds.get("access_key_id", ""),
                        secret_access_key=aws_creds.get("secret_access_key", ""),
                        session_token=aws_creds.get("session_token"),
                        region=aws_creds.get("region", self.config.default_parameters.aws_region)
                    )
                    # Validate AWS credentials
                    validation_result = validate_credentials(cloud_creds.aws_credentials)
                    if not validation_result["valid"]:
                        raise ValueError(f"Invalid AWS credentials: {validation_result.get('error', 'Unknown error')}")
                except Exception as e:
                    raise ValueError(f"Invalid AWS credentials: {str(e)}")
            elif cloud_provider == CloudProvider.AWS:
                raise ValueError("AWS credentials required for AWS cloud provider")
        
        # Extract Azure credentials if needed
        if cloud_provider in [CloudProvider.AZURE, CloudProvider.ALL]:
            azure_creds = cred_data.get("azure_credentials")
            if azure_creds:
                try:
                    cloud_creds.azure_credentials = AzureCredentials(
                        client_id=azure_creds.get("client_id", ""),
                        client_secret=azure_creds.get("client_secret", ""),
                        tenant_id=azure_creds.get("tenant_id", ""),
                        subscription_id=azure_creds.get("subscription_id", "")
                    )
                except Exception as e:
                    raise ValueError(f"Invalid Azure credentials: {str(e)}")
            elif cloud_provider == CloudProvider.AZURE:
                raise ValueError("Azure credentials required for Azure cloud provider")
        
        # Extract GCP credentials if needed
        if cloud_provider in [CloudProvider.GCP, CloudProvider.ALL]:
            gcp_creds = cred_data.get("gcp_credentials")
            if gcp_creds:
                try:
                    cloud_creds.gcp_credentials = GCPCredentials(
                        project_id=gcp_creds.get("project_id", ""),
                        credentials_path=gcp_creds.get("credentials_path"),
                        credentials_json=gcp_creds.get("credentials_json"),
                        use_default_credential=gcp_creds.get("use_default_credential", False)
                    )
                except Exception as e:
                    raise ValueError(f"Invalid GCP credentials: {str(e)}")
            elif cloud_provider == CloudProvider.GCP:
                raise ValueError("GCP credentials required for GCP cloud provider")
        
        return cloud_creds
    
    def _handle_whitelist_add(self, request: MCPRequest) -> MCPResponse:
        """Handle whitelist_add method.
        
        Args:
            request: MCP request
        
        Returns:
            MCP response
        """
        params = request.params
        
        # Validate credentials
        try:
            credentials = self._validate_credentials_param(params)
        except ValueError as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                str(e)
            )
        
        # Validate required parameters
        if "ip_address" not in params:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                "Missing required parameter: ip_address"
            )
        
        # Determine target based on cloud provider
        target = None
        if credentials.cloud == CloudProvider.AWS:
            if "security_group_id" not in params:
                return create_mcp_error(
                    request.id,
                    ERROR_INVALID_PARAMS,
                    "Missing required parameter: security_group_id for AWS"
                )
            target = params["security_group_id"]
        elif credentials.cloud == CloudProvider.AZURE:
            if "nsg_name" not in params:
                return create_mcp_error(
                    request.id,
                    ERROR_INVALID_PARAMS,
                    "Missing required parameter: nsg_name for Azure"
                )
            target = params["nsg_name"]
        elif credentials.cloud == CloudProvider.GCP:
            # GCP generates target automatically
            target = "auto"
        elif credentials.cloud == CloudProvider.ALL:
            # For multi-cloud, we'll use the appropriate target for each cloud
            target = params.get("security_group_id", params.get("nsg_name", "auto"))
        
        # Get port number
        try:
            port_input = params.get("port", self.config.default_parameters.port)
            port = get_port_number(str(port_input), self.config) if port_input else self.config.default_parameters.port
        except ValueError as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                str(e)
            )
        
        # Use CloudServiceManager to add rule
        try:
            results = self.cloud_manager.add_whitelist_rule(
                credentials=credentials,
                target=target,
                ip_address=params["ip_address"],
                port=port,
                protocol=params.get("protocol", self.config.default_parameters.protocol),
                description=params.get("description"),
                service_name=params.get("service_name"),
                resource_group=params.get("resource_group")
            )
            
            # Process results
            if not results:
                return create_mcp_error(
                    request.id,
                    ERROR_INTERNAL,
                    "No results returned from cloud service"
                )
            
            # If single cloud, return simple result
            if len(results) == 1:
                result = results[0]
                if result.success:
                    return create_mcp_response(
                        request.id,
                        {
                            "success": True,
                            "message": result.message,
                            "cloud": result.cloud.value,
                            "details": result.details
                        }
                    )
                else:
                    return create_mcp_error(
                        request.id,
                        ERROR_INTERNAL,
                        result.error or "Failed to add rule"
                    )
            
            # Multi-cloud result
            cloud_results = []
            all_success = True
            for result in results:
                cloud_results.append({
                    "cloud": result.cloud.value,
                    "success": result.success,
                    "message": result.message,
                    "error": result.error,
                    "details": result.details
                })
                if not result.success:
                    all_success = False
            
            return create_mcp_response(
                request.id,
                {
                    "success": all_success,
                    "message": f"Processed {len(results)} cloud(s)",
                    "results": cloud_results
                }
            )
                
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INTERNAL,
                f"Cloud service error: {str(e)}"
            )
    
    def _handle_whitelist_remove(self, request: MCPRequest) -> MCPResponse:
        """Handle whitelist_remove method.
        
        Args:
            request: MCP request
        
        Returns:
            MCP response
        """
        params = request.params
        
        # Validate credentials
        try:
            credentials = self._validate_credentials_param(params)
        except ValueError as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                str(e)
            )
        
        # At least one filter parameter is required
        if not any(p in params for p in ["ip_address", "port", "service_name"]):
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                "At least one of ip_address, port, or service_name is required"
            )
        
        # Determine target based on cloud provider
        target = None
        if credentials.cloud == CloudProvider.AWS:
            if "security_group_id" not in params:
                return create_mcp_error(
                    request.id,
                    ERROR_INVALID_PARAMS,
                    "Missing required parameter: security_group_id for AWS"
                )
            target = params["security_group_id"]
        elif credentials.cloud == CloudProvider.AZURE:
            if "nsg_name" not in params:
                return create_mcp_error(
                    request.id,
                    ERROR_INVALID_PARAMS,
                    "Missing required parameter: nsg_name for Azure"
                )
            target = params["nsg_name"]
        elif credentials.cloud == CloudProvider.GCP:
            # GCP uses project_id as target
            if credentials.gcp_credentials:
                target = credentials.gcp_credentials.project_id
            else:
                return create_mcp_error(
                    request.id,
                    ERROR_INVALID_PARAMS,
                    "GCP credentials missing project_id"
                )
        elif credentials.cloud == CloudProvider.ALL:
            # For multi-cloud, we'll use the appropriate target for each cloud
            target = params.get("security_group_id", params.get("nsg_name", "auto"))
        
        # Use CloudServiceManager to remove rule
        try:
            results = self.cloud_manager.remove_whitelist_rule(
                credentials=credentials,
                target=target,
                ip_address=params.get("ip_address"),
                port=params.get("port"),
                service_name=params.get("service_name"),
                protocol=params.get("protocol", self.config.default_parameters.protocol),
                resource_group=params.get("resource_group")
            )
            
            # Process results
            if not results:
                return create_mcp_error(
                    request.id,
                    ERROR_INTERNAL,
                    "No results returned from cloud service"
                )
            
            # If single cloud, return simple result
            if len(results) == 1:
                result = results[0]
                if result.success:
                    return create_mcp_response(
                        request.id,
                        {
                            "success": True,
                            "message": result.message,
                            "cloud": result.cloud.value
                        }
                    )
                else:
                    return create_mcp_error(
                        request.id,
                        ERROR_INTERNAL,
                        result.error or "Failed to remove rule"
                    )
            
            # Multi-cloud result
            cloud_results = []
            all_success = True
            for result in results:
                cloud_results.append({
                    "cloud": result.cloud.value,
                    "success": result.success,
                    "message": result.message,
                    "error": result.error
                })
                if not result.success:
                    all_success = False
            
            return create_mcp_response(
                request.id,
                {
                    "success": all_success,
                    "message": f"Processed {len(results)} cloud(s)",
                    "results": cloud_results
                }
            )
                
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INTERNAL,
                f"Cloud service error: {str(e)}"
            )
    
    def _handle_whitelist_list(self, request: MCPRequest) -> MCPResponse:
        """Handle whitelist_list method.
        
        Args:
            request: MCP request
        
        Returns:
            MCP response
        """
        params = request.params
        
        # Validate credentials
        try:
            credentials = self._validate_credentials_param(params)
        except ValueError as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                str(e)
            )
        
        # Validate required parameters
        if "security_group_id" not in params:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                "Missing required parameter: security_group_id"
            )
        
        # List rules using AWS service
        try:
            aws_service = AWSService(credentials.aws_credentials)
            rules = aws_service.list_whitelist_rules(params["security_group_id"])
            
            # Convert rules to response format
            rule_list = []
            for rule in rules:
                rule_list.append({
                    "cidr_ip": rule.cidr_ip,
                    "port": rule.from_port,
                    "protocol": rule.ip_protocol,
                    "description": rule.description
                })
            
            return create_mcp_response(
                request.id,
                {
                    "success": True,
                    "security_group_id": params["security_group_id"],
                    "rules": rule_list,
                    "count": len(rule_list)
                }
            )
            
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INTERNAL,
                f"Failed to list rules: {str(e)}"
            )
    
    def _handle_whitelist_check(self, request: MCPRequest) -> MCPResponse:
        """Handle whitelist_check method.
        
        Args:
            request: MCP request
        
        Returns:
            MCP response
        """
        params = request.params
        
        # Validate credentials
        try:
            credentials = self._validate_credentials_param(params)
        except ValueError as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                str(e)
            )
        
        # Validate required parameters
        required = ["security_group_id", "ip_address"]
        missing = [p for p in required if p not in params]
        if missing:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                f"Missing required parameters: {', '.join(missing)}"
            )
        
        # Normalize IP address
        try:
            cidr_ip = normalize_ip_input(params["ip_address"])
        except IPValidationError as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                f"Invalid IP address: {str(e)}"
            )
        
        # Get port number
        try:
            port_input = str(params.get("port", self.config.default_parameters.port))
            port = get_port_number(port_input, self.config)
        except ValueError as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                str(e)
            )
        
        # Create rule to check
        try:
            rule = SecurityGroupRule(
                group_id=params["security_group_id"],
                ip_protocol=params.get("protocol", self.config.default_parameters.protocol),
                from_port=port,
                to_port=port,
                cidr_ip=cidr_ip
            )
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                f"Invalid rule parameters: {str(e)}"
            )
        
        # Check if rule exists
        try:
            aws_service = AWSService(credentials.aws_credentials)
            exists = aws_service.check_rule_exists(rule)
            
            return create_mcp_response(
                request.id,
                {
                    "success": True,
                    "exists": exists,
                    "message": f"Rule {'exists' if exists else 'does not exist'} in security group"
                }
            )
            
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INTERNAL,
                f"Failed to check rule: {str(e)}"
            )