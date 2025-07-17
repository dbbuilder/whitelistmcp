"""Unit tests for MCP protocol handlers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from awswhitelist.mcp.handler import (
    MCPHandler,
    MCPRequest,
    MCPResponse,
    MCPError,
    validate_mcp_request,
    create_mcp_response,
    create_mcp_error
)
from awswhitelist.aws.service import SecurityGroupRule, WhitelistResult
from awswhitelist.config import Config


class TestMCPRequest:
    """Test MCP request model."""
    
    def test_mcp_request_creation(self):
        """Test creating an MCP request."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="test-123",
            method="whitelist_add",
            params={
                "credentials": {
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "secret"
                },
                "security_group_id": "sg-123456",
                "ip_address": "192.168.1.1"
            }
        )
        assert request.jsonrpc == "2.0"
        assert request.id == "test-123"
        assert request.method == "whitelist_add"
        assert request.params["security_group_id"] == "sg-123456"
    
    def test_mcp_request_validation(self):
        """Test MCP request validation."""
        # Valid request
        request = MCPRequest(
            jsonrpc="2.0",
            id="123",
            method="whitelist_add",
            params={}
        )
        assert request.jsonrpc == "2.0"
        
        # Invalid JSON-RPC version
        with pytest.raises(ValueError):
            MCPRequest(
                jsonrpc="1.0",
                id="123",
                method="test",
                params={}
            )


class TestMCPResponse:
    """Test MCP response model."""
    
    def test_mcp_response_success(self):
        """Test creating a successful MCP response."""
        response = MCPResponse(
            jsonrpc="2.0",
            id="test-123",
            result={"success": True, "message": "Rule added"}
        )
        assert response.jsonrpc == "2.0"
        assert response.id == "test-123"
        assert response.result["success"] is True
        assert response.error is None
    
    def test_mcp_response_error(self):
        """Test creating an error MCP response."""
        response = MCPResponse(
            jsonrpc="2.0",
            id="test-123",
            error=MCPError(
                code=-32600,
                message="Invalid Request",
                data={"details": "Missing required parameter"}
            )
        )
        assert response.jsonrpc == "2.0"
        assert response.result is None
        assert response.error.code == -32600
        assert response.error.message == "Invalid Request"


class TestMCPError:
    """Test MCP error model."""
    
    def test_mcp_error_creation(self):
        """Test creating an MCP error."""
        error = MCPError(
            code=-32700,
            message="Parse error",
            data={"position": 42}
        )
        assert error.code == -32700
        assert error.message == "Parse error"
        assert error.data["position"] == 42
    
    def test_mcp_error_without_data(self):
        """Test creating an MCP error without data."""
        error = MCPError(
            code=-32601,
            message="Method not found"
        )
        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data is None


class TestValidateMCPRequest:
    """Test MCP request validation function."""
    
    def test_validate_valid_request(self):
        """Test validating a valid MCP request."""
        request_dict = {
            "jsonrpc": "2.0",
            "id": "123",
            "method": "whitelist_add",
            "params": {"test": "value"}
        }
        
        request = validate_mcp_request(request_dict)
        assert isinstance(request, MCPRequest)
        assert request.method == "whitelist_add"
    
    def test_validate_invalid_request(self):
        """Test validating invalid MCP requests."""
        # Missing required fields
        with pytest.raises(ValueError):
            validate_mcp_request({
                "jsonrpc": "2.0",
                "method": "test"
                # Missing id
            })
        
        # Invalid type
        with pytest.raises(ValueError):
            validate_mcp_request("not a dict")
        
        # Invalid JSON-RPC version
        with pytest.raises(ValueError):
            validate_mcp_request({
                "jsonrpc": "1.0",
                "id": "123",
                "method": "test",
                "params": {}
            })


class TestCreateMCPResponse:
    """Test MCP response creation functions."""
    
    def test_create_success_response(self):
        """Test creating a success response."""
        response = create_mcp_response(
            request_id="test-123",
            result={"success": True, "data": "test"}
        )
        
        assert response.jsonrpc == "2.0"
        assert response.id == "test-123"
        assert response.result["success"] is True
        assert response.error is None
    
    def test_create_error_response(self):
        """Test creating an error response."""
        response = create_mcp_error(
            request_id="test-123",
            code=-32602,
            message="Invalid params",
            data={"param": "missing"}
        )
        
        assert response.jsonrpc == "2.0"
        assert response.id == "test-123"
        assert response.result is None
        assert response.error.code == -32602
        assert response.error.message == "Invalid params"


class TestMCPHandler:
    """Test MCP handler functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config()
    
    @pytest.fixture
    def handler(self, config):
        """Create MCP handler instance."""
        return MCPHandler(config)
    
    def test_handler_initialization(self, handler, config):
        """Test handler initialization."""
        assert handler.config == config
        assert handler.methods is not None
        assert "whitelist_add" in handler.methods
        assert "whitelist_remove" in handler.methods
        assert "whitelist_list" in handler.methods
    
    @patch('awswhitelist.mcp.handler.AWSService')
    @patch('awswhitelist.mcp.handler.validate_credentials')
    def test_handle_whitelist_add(self, mock_validate, mock_aws_service, handler):
        """Test handling whitelist_add method."""
        # Mock credential validation
        mock_validate.return_value = {
            'valid': True,
            'account_id': '123456789012',
            'user_arn': 'arn:aws:iam::123456789012:user/test'
        }
        
        # Mock AWS service
        mock_service_instance = Mock()
        mock_aws_service.return_value = mock_service_instance
        mock_service_instance.add_whitelist_rule.return_value = WhitelistResult(
            success=True,
            message="Rule added successfully"
        )
        
        # Create request
        request = MCPRequest(
            jsonrpc="2.0",
            id="test-123",
            method="whitelist_add",
            params={
                "credentials": {
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "secret",
                    "region": "us-east-1"
                },
                "security_group_id": "sg-123456",
                "ip_address": "192.168.1.1",
                "port": 443,
                "protocol": "tcp",
                "description": "Test rule"
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-123"
        assert response.error is None
        assert response.result["success"] is True
        assert "added" in response.result["message"]
    
    @patch('awswhitelist.mcp.handler.validate_credentials')
    def test_handle_invalid_credentials(self, mock_validate, handler):
        """Test handling request with invalid credentials."""
        # Mock invalid credentials
        mock_validate.return_value = {
            'valid': False,
            'error': 'Invalid credentials'
        }
        
        request = MCPRequest(
            jsonrpc="2.0",
            id="test-123",
            method="whitelist_add",
            params={
                "credentials": {
                    "access_key_id": "invalid",
                    "secret_access_key": "invalid"
                },
                "security_group_id": "sg-123456",
                "ip_address": "192.168.1.1"
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-123"
        assert response.result is None
        assert response.error is not None
        assert response.error.code == -32602
        assert "Invalid credentials" in response.error.message
    
    def test_handle_missing_params(self, handler):
        """Test handling request with missing parameters."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="test-123",
            method="whitelist_add",
            params={
                # Missing required parameters
                "security_group_id": "sg-123456"
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.error is not None
        assert response.error.code == -32602
        assert "Missing required" in response.error.message
    
    def test_handle_invalid_method(self, handler):
        """Test handling request with invalid method."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="test-123",
            method="invalid/method",
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.error is not None
        assert response.error.code == -32601
        assert "Method not found" in response.error.message
    
    @patch('awswhitelist.mcp.handler.AWSService')
    @patch('awswhitelist.mcp.handler.validate_credentials')
    def test_handle_whitelist_list(self, mock_validate, mock_aws_service, handler):
        """Test handling whitelist_list method."""
        # Mock credential validation
        mock_validate.return_value = {
            'valid': True,
            'account_id': '123456789012'
        }
        
        # Mock AWS service
        mock_service_instance = Mock()
        mock_aws_service.return_value = mock_service_instance
        
        # Mock rules
        mock_rules = [
            SecurityGroupRule(
                group_id="sg-123456",
                ip_protocol="tcp",
                from_port=80,
                to_port=80,
                cidr_ip="10.0.0.0/24",
                description="HTTP access"
            ),
            SecurityGroupRule(
                group_id="sg-123456",
                ip_protocol="tcp",
                from_port=443,
                to_port=443,
                cidr_ip="192.168.1.0/24",
                description="HTTPS access"
            )
        ]
        mock_service_instance.list_whitelist_rules.return_value = mock_rules
        
        request = MCPRequest(
            jsonrpc="2.0",
            id="test-123",
            method="whitelist_list",
            params={
                "credentials": {
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "secret"
                },
                "security_group_id": "sg-123456"
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.error is None
        assert response.result["success"] is True
        assert len(response.result["rules"]) == 2
        assert response.result["rules"][0]["cidr_ip"] == "10.0.0.0/24"