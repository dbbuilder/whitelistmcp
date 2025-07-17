"""MCP protocol handler for AWS whitelisting operations."""

from typing import Dict, Any, Optional, Callable, List, Union
from pydantic import BaseModel, field_validator

from awswhitelist import __version__
from awswhitelist.config import Config, get_port_number
from awswhitelist.utils.credential_validator import (
    AWSCredentials,
    validate_credentials,
    CredentialValidationError
)
from awswhitelist.utils.ip_validator import (
    normalize_ip_input,
    IPValidationError
)
from awswhitelist.aws.service import (
    AWSService,
    SecurityGroupRule,
    WhitelistResult,
    create_rule_description
)


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
    def validate_jsonrpc(cls, v):
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
    def validate_response(cls, v, info):
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
        self.methods: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "resources/list": self._handle_resources_list,
            "prompts/list": self._handle_prompts_list,
            "whitelist/add": self._handle_whitelist_add,
            "whitelist/remove": self._handle_whitelist_remove,
            "whitelist/list": self._handle_whitelist_list,
            "whitelist/check": self._handle_whitelist_check
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
                    "name": "awswhitelist",
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
        # Define credential schema once for reuse
        credential_schema = {
            "type": "object",
            "properties": {
                "access_key_id": {"type": "string"},
                "secret_access_key": {"type": "string"},
                "region": {"type": "string"},
                "session_token": {"type": "string"}
            },
            "required": ["access_key_id", "secret_access_key", "region"]
        }
        
        tools = [
            {
                "name": "whitelist/add",
                "description": "Add an IP address to an AWS Security Group",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials": credential_schema,
                        "security_group_id": {"type": "string", "description": "AWS Security Group ID (e.g., sg-12345678)"},
                        "ip_address": {"type": "string", "description": "IP address or CIDR block to whitelist"},
                        "port": {"type": "integer", "description": "Port number (default: 443)", "minimum": 1, "maximum": 65535},
                        "protocol": {"type": "string", "enum": ["tcp", "udp", "icmp"], "description": "Protocol (default: tcp)"},
                        "description": {"type": "string", "description": "Description for the security group rule"}
                    },
                    "required": ["credentials", "security_group_id", "ip_address"]
                }
            },
            {
                "name": "whitelist/remove",
                "description": "Remove an IP address from an AWS Security Group",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials": credential_schema,
                        "security_group_id": {"type": "string", "description": "AWS Security Group ID (e.g., sg-12345678)"},
                        "ip_address": {"type": "string", "description": "IP address or CIDR block to remove"},
                        "port": {"type": "integer", "description": "Port number (optional, remove all ports if not specified)", "minimum": 1, "maximum": 65535},
                        "protocol": {"type": "string", "enum": ["tcp", "udp", "icmp"], "description": "Protocol (optional, default: tcp)"}
                    },
                    "required": ["credentials", "security_group_id", "ip_address"]
                }
            },
            {
                "name": "whitelist/list",
                "description": "List all IP addresses whitelisted in an AWS Security Group",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials": credential_schema,
                        "security_group_id": {"type": "string", "description": "AWS Security Group ID (e.g., sg-12345678)"}
                    },
                    "required": ["credentials", "security_group_id"]
                }
            },
            {
                "name": "whitelist/check",
                "description": "Check if an IP address is whitelisted in an AWS Security Group",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials": credential_schema,
                        "security_group_id": {"type": "string", "description": "AWS Security Group ID (e.g., sg-12345678)"},
                        "ip_address": {"type": "string", "description": "IP address or CIDR block to check"},
                        "port": {"type": "integer", "description": "Port number to check (optional, check all ports if not specified)", "minimum": 1, "maximum": 65535},
                        "protocol": {"type": "string", "enum": ["tcp", "udp", "icmp"], "description": "Protocol to check (optional, default: tcp)"}
                    },
                    "required": ["credentials", "security_group_id", "ip_address"]
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
    
    def _validate_credentials_param(self, params: Dict[str, Any]) -> AWSCredentials:
        """Validate and extract credentials from parameters.
        
        Args:
            params: Request parameters
        
        Returns:
            AWSCredentials object
        
        Raises:
            ValueError: If credentials are invalid
        """
        if "credentials" not in params:
            raise ValueError("Missing required parameter: credentials")
        
        cred_data = params["credentials"]
        if not isinstance(cred_data, dict):
            raise ValueError("Credentials must be an object")
        
        # Extract credentials
        try:
            credentials = AWSCredentials(
                access_key_id=cred_data.get("access_key_id", ""),
                secret_access_key=cred_data.get("secret_access_key", ""),
                session_token=cred_data.get("session_token"),
                region=cred_data.get("region", self.config.default_parameters.region)
            )
        except Exception as e:
            raise ValueError(f"Invalid credentials: {str(e)}")
        
        # Validate credentials
        validation_result = validate_credentials(credentials)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid credentials: {validation_result.get('error', 'Unknown error')}")
        
        return credentials
    
    def _handle_whitelist_add(self, request: MCPRequest) -> MCPResponse:
        """Handle whitelist/add method.
        
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
        
        # Create rule
        try:
            rule = SecurityGroupRule(
                group_id=params["security_group_id"],
                ip_protocol=params.get("protocol", self.config.default_parameters.protocol),
                from_port=port,
                to_port=port,
                cidr_ip=cidr_ip,
                description=create_rule_description(
                    params.get("description", self.config.default_parameters.description_template),
                    user=params.get("user", "MCP"),
                    reason=params.get("reason", "API access")
                )
            )
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INVALID_PARAMS,
                f"Invalid rule parameters: {str(e)}"
            )
        
        # Add rule using AWS service
        try:
            aws_service = AWSService(credentials)
            result = aws_service.add_whitelist_rule(rule)
            
            if result.success:
                return create_mcp_response(
                    request.id,
                    {
                        "success": True,
                        "message": result.message,
                        "rule": {
                            "group_id": rule.group_id,
                            "cidr_ip": rule.cidr_ip,
                            "port": rule.from_port,
                            "protocol": rule.ip_protocol,
                            "description": rule.description
                        }
                    }
                )
            else:
                return create_mcp_error(
                    request.id,
                    ERROR_INTERNAL,
                    result.error or "Failed to add rule"
                )
                
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INTERNAL,
                f"AWS service error: {str(e)}"
            )
    
    def _handle_whitelist_remove(self, request: MCPRequest) -> MCPResponse:
        """Handle whitelist/remove method.
        
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
        
        # Create rule to remove
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
        
        # Remove rule using AWS service
        try:
            aws_service = AWSService(credentials)
            result = aws_service.remove_whitelist_rule(rule)
            
            if result.success:
                return create_mcp_response(
                    request.id,
                    {
                        "success": True,
                        "message": result.message
                    }
                )
            else:
                return create_mcp_error(
                    request.id,
                    ERROR_INTERNAL,
                    result.error or "Failed to remove rule"
                )
                
        except Exception as e:
            return create_mcp_error(
                request.id,
                ERROR_INTERNAL,
                f"AWS service error: {str(e)}"
            )
    
    def _handle_whitelist_list(self, request: MCPRequest) -> MCPResponse:
        """Handle whitelist/list method.
        
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
            aws_service = AWSService(credentials)
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
        """Handle whitelist/check method.
        
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
            aws_service = AWSService(credentials)
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