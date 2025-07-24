"""Unit tests for MCP handler module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from whitelistmcp.mcp.handler import (
    MCPHandler,
    MCPRequest,
    MCPResponse,
    MCPError,
    validate_mcp_request,
    create_mcp_response,
    create_mcp_error,
    ERROR_PARSE,
    ERROR_INVALID_REQUEST,
    ERROR_METHOD_NOT_FOUND,
    ERROR_INVALID_PARAMS,
    ERROR_INTERNAL
)
from whitelistmcp.config import Config, CloudProvider
from whitelistmcp.cloud_service import CloudCredentials, UnifiedWhitelistResult


class TestMCPError:
    """Test MCPError model."""
    
    def test_error_creation(self):
        """Test creating MCP error."""
        error = MCPError(
            code=-32600,
            message="Invalid request",
            data={"details": "Missing required field"}
        )
        assert error.code == -32600
        assert error.message == "Invalid request"
        assert error.data["details"] == "Missing required field"


class TestMCPRequest:
    """Test MCPRequest model."""
    
    def test_valid_request(self):
        """Test creating valid MCP request."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="tools/call",
            params={"name": "whitelist_add"}
        )
        assert request.jsonrpc == "2.0"
        assert request.id == "123"
        assert request.method == "tools/call"
        assert request.params["name"] == "whitelist_add"
    
    def test_notification_request(self):
        """Test notification request without id."""
        request = MCPRequest(
            jsonrpc="2.0",
            method="notifications/initialized",
            params={}
        )
        assert request.id is None
    
    def test_invalid_jsonrpc_version(self):
        """Test invalid JSON-RPC version."""
        with pytest.raises(ValueError, match="JSON-RPC version must be 2.0"):
            MCPRequest(
                jsonrpc="1.0",
                id="123",
                method="test"
            )


class TestMCPResponse:
    """Test MCPResponse model."""
    
    def test_success_response(self):
        """Test successful response."""
        response = MCPResponse(
            jsonrpc="2.0",
            id="123",
            result={"success": True}
        )
        assert response.jsonrpc == "2.0"
        assert response.id == "123"
        assert response.result["success"] is True
        assert response.error is None
    
    def test_error_response(self):
        """Test error response."""
        error = MCPError(code=-32600, message="Invalid request")
        response = MCPResponse(
            jsonrpc="2.0",
            id="123",
            error=error
        )
        assert response.result is None
        assert response.error.code == -32600


class TestValidateMCPRequest:
    """Test validate_mcp_request function."""
    
    def test_valid_request_dict(self):
        """Test validating valid request dictionary."""
        request_data = {
            "jsonrpc": "2.0",
            "id": "123",
            "method": "test",
            "params": {}
        }
        request = validate_mcp_request(request_data)
        assert isinstance(request, MCPRequest)
        assert request.id == "123"
    
    def test_invalid_request_type(self):
        """Test invalid request type."""
        with pytest.raises(ValueError, match="Request must be a JSON object"):
            validate_mcp_request("not a dict")
    
    def test_missing_required_fields(self):
        """Test missing required fields."""
        with pytest.raises(ValueError):
            validate_mcp_request({})


class TestCreateMCPResponse:
    """Test create_mcp_response function."""
    
    def test_create_success_response(self):
        """Test creating successful response."""
        response = create_mcp_response("123", {"success": True})
        assert isinstance(response, MCPResponse)
        assert response.id == "123"
        assert response.result["success"] is True


class TestCreateMCPError:
    """Test create_mcp_error function."""
    
    def test_create_error_response(self):
        """Test creating error response."""
        response = create_mcp_error(
            "123",
            ERROR_INVALID_REQUEST,
            "Invalid request",
            {"field": "method"}
        )
        assert isinstance(response, MCPResponse)
        assert response.id == "123"
        assert response.error.code == ERROR_INVALID_REQUEST
        assert response.error.message == "Invalid request"
        assert response.error.data["field"] == "method"


class TestMCPHandler:
    """Test MCPHandler class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.default_parameters = Mock()
        config.default_parameters.cloud_provider = CloudProvider.AWS
        config.default_parameters.aws_region = "us-east-1"
        config.default_parameters.azure_region = "eastus"
        config.default_parameters.gcp_region = "us-central1"
        config.default_parameters.gcp_zone = "us-central1-a"
        config.default_parameters.port = 22
        config.default_parameters.protocol = "tcp"
        return config
    
    @pytest.fixture
    def handler(self, mock_config):
        """Create MCPHandler instance."""
        with patch('whitelistmcp.mcp.handler.CloudServiceManager'):
            return MCPHandler(mock_config)
    
    def test_initialization(self, handler, mock_config):
        """Test handler initialization."""
        assert handler.config == mock_config
        assert handler.cloud_manager is not None
        assert "initialize" in handler.methods
        assert "tools/list" in handler.methods
        assert "tools/call" in handler.methods
    
    def test_handle_initialize(self, handler):
        """Test initialize method."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="initialize",
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.result is not None
        assert response.result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in response.result
        assert response.result["serverInfo"]["name"] == "whitelistmcp"
    
    def test_handle_tools_list(self, handler):
        """Test tools/list method."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="tools/list",
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.result is not None
        assert "tools" in response.result
        tools = response.result["tools"]
        assert len(tools) == 4
        
        tool_names = [t["name"] for t in tools]
        assert "whitelist_add" in tool_names
        assert "whitelist_remove" in tool_names
        assert "whitelist_list" in tool_names
        assert "whitelist_check" in tool_names
    
    def test_handle_method_not_found(self, handler):
        """Test handling unknown method."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="unknown/method",
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.error is not None
        assert response.error.code == ERROR_METHOD_NOT_FOUND
        assert "Method not found" in response.error.message
    
    def test_handle_tools_call(self, handler):
        """Test tools/call method."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="tools/call",
            params={
                "name": "whitelist_add",
                "arguments": {
                    "credentials": {
                        "cloud": "aws",
                        "aws_credentials": {
                            "access_key_id": "AKIA...",
                            "secret_access_key": "secret",
                            "region": "us-east-1"
                        }
                    },
                    "security_group_id": "sg-12345",
                    "ip_address": "192.168.1.1"
                }
            }
        )
        
        # Mock cloud manager response
        mock_result = UnifiedWhitelistResult(
            cloud=CloudProvider.AWS,
            success=True,
            message="Rule added"
        )
        handler.cloud_manager.add_whitelist_rule.return_value = [mock_result]
        
        # Mock credential validation
        with patch('whitelistmcp.mcp.handler.validate_credentials') as mock_validate:
            mock_validate.return_value = {"valid": True}
            response = handler.handle_request(request)
        
        assert response.result is not None
        assert response.result["success"] is True
    
    def test_handle_tools_call_missing_name(self, handler):
        """Test tools/call without tool name."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="tools/call",
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.error is not None
        assert response.error.code == ERROR_INVALID_PARAMS
        assert "Missing required parameter: name" in response.error.message
    
    def test_validate_credentials_param_aws(self, handler):
        """Test validating AWS credentials parameter."""
        params = {
            "credentials": {
                "cloud": "aws",
                "aws_credentials": {
                    "access_key_id": "AKIA...",
                    "secret_access_key": "secret",
                    "region": "us-east-1"
                }
            }
        }
        
        with patch('whitelistmcp.mcp.handler.validate_credentials') as mock_validate:
            mock_validate.return_value = {"valid": True}
            creds = handler._validate_credentials_param(params)
        
        assert isinstance(creds, CloudCredentials)
        assert creds.cloud == CloudProvider.AWS
        assert creds.aws_credentials is not None
    
    def test_validate_credentials_param_all_clouds(self, handler):
        """Test validating credentials for all clouds."""
        params = {
            "credentials": {
                "cloud": "all",
                "aws_credentials": {
                    "access_key_id": "AKIA...",
                    "secret_access_key": "secret",
                    "region": "us-east-1"
                },
                "azure_credentials": {
                    "client_id": "client",
                    "client_secret": "secret",
                    "tenant_id": "tenant",
                    "subscription_id": "sub"
                },
                "gcp_credentials": {
                    "project_id": "project"
                }
            }
        }
        
        with patch('whitelistmcp.mcp.handler.validate_credentials') as mock_validate:
            mock_validate.return_value = {"valid": True}
            creds = handler._validate_credentials_param(params)
        
        assert creds.cloud == CloudProvider.ALL
        assert creds.aws_credentials is not None
        assert creds.azure_credentials is not None
        assert creds.gcp_credentials is not None
    
    def test_validate_credentials_param_missing(self, handler):
        """Test missing credentials parameter."""
        params = {}
        
        with pytest.raises(ValueError, match="Missing required parameter: credentials"):
            handler._validate_credentials_param(params)
    
    def test_handle_whitelist_add_success(self, handler):
        """Test successful whitelist_add."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="whitelist_add",
            params={
                "credentials": {
                    "cloud": "aws",
                    "aws_credentials": {
                        "access_key_id": "AKIA...",
                        "secret_access_key": "secret",
                        "region": "us-east-1"
                    }
                },
                "security_group_id": "sg-12345",
                "ip_address": "192.168.1.1",
                "port": 443,
                "description": "Test rule"
            }
        )
        
        # Mock responses
        mock_result = UnifiedWhitelistResult(
            cloud=CloudProvider.AWS,
            success=True,
            message="Rule added successfully",
            details={"rule_id": "sgr-12345"}
        )
        handler.cloud_manager.add_whitelist_rule.return_value = [mock_result]
        
        with patch('whitelistmcp.mcp.handler.validate_credentials') as mock_validate:
            mock_validate.return_value = {"valid": True}
            response = handler._handle_whitelist_add(request)
        
        assert response.result is not None
        assert response.result["success"] is True
        assert response.result["cloud"] == "aws"
        assert response.result["details"]["rule_id"] == "sgr-12345"
    
    def test_handle_whitelist_remove_by_ip(self, handler):
        """Test removing rule by IP."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="whitelist_remove",
            params={
                "credentials": {
                    "cloud": "aws",
                    "aws_credentials": {
                        "access_key_id": "AKIA...",
                        "secret_access_key": "secret",
                        "region": "us-east-1"
                    }
                },
                "security_group_id": "sg-12345",
                "ip_address": "192.168.1.1"
            }
        )
        
        # Mock response
        mock_result = UnifiedWhitelistResult(
            cloud=CloudProvider.AWS,
            success=True,
            message="Rule removed"
        )
        handler.cloud_manager.remove_whitelist_rule.return_value = [mock_result]
        
        with patch('whitelistmcp.mcp.handler.validate_credentials') as mock_validate:
            mock_validate.return_value = {"valid": True}
            response = handler._handle_whitelist_remove(request)
        
        assert response.result is not None
        assert response.result["success"] is True
    
    def test_handle_exception_in_method(self, handler):
        """Test exception handling in method."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="initialize",
            params={}
        )
        
        # Mock method to raise exception
        with patch.object(handler, '_handle_initialize', side_effect=Exception("Test error")):
            response = handler.handle_request(request)
        
        assert response.error is not None
        assert response.error.code == ERROR_INTERNAL
        assert "Internal error" in response.error.message
        assert response.error.data["error"] == "Test error"