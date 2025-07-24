"""End-to-end integration tests for AWS Whitelisting MCP Server."""

import pytest
import json
from unittest.mock import patch, Mock
from whitelistmcp.main import MCPServer
from whitelistmcp.config import Config


class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def server(self):
        """Create server instance with test config."""
        config = Config()
        with patch('whitelistmcp.main.load_config', return_value=config):
            with patch('whitelistmcp.main.setup_logging') as mock_logging:
                mock_logging.return_value = Mock()
                server = MCPServer()
                return server
    
    @patch('boto3.client')
    def test_add_whitelist_rule_flow(self, mock_boto_client, server):
        """Test complete flow of adding a whitelist rule."""
        # Mock AWS clients
        mock_ec2 = Mock()
        mock_sts = Mock()
        
        def client_factory(service, **kwargs):
            if service == 'ec2':
                return mock_ec2
            elif service == 'sts':
                return mock_sts
            raise ValueError(f"Unknown service: {service}")
        
        mock_boto_client.side_effect = client_factory
        
        # Mock STS response for credential validation
        mock_sts.get_caller_identity.return_value = {
            'UserId': 'AIDAI23456789EXAMPLE',
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/TestUser'
        }
        
        # Mock EC2 responses
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-123456',
                'GroupName': 'test-sg',
                'Description': 'Test security group',
                'IpPermissions': []
            }]
        }
        
        mock_ec2.authorize_security_group_ingress.return_value = {
            'Return': True,
            'SecurityGroupRules': [{
                'SecurityGroupRuleId': 'sgr-123456'
            }]
        }
        
        # Create request
        request = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "method": "tools/call",
            "params": {
                "name": "whitelist_add",
                "arguments": {
                    "credentials": {
                        "cloud": "aws",
                        "aws_credentials": {
                            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                            "region": "us-east-1"
                        }
                    },
                    "security_group_id": "sg-123456",
                    "ip_address": "192.168.1.1",
                    "port": "https",  # Named port
                    "protocol": "tcp",
                    "description": "Test rule for integration test"
                }
            }
        }
        
        # Process request
        response_str = server.process_request(json.dumps(request))
        response = json.loads(response_str)
        
        # Verify response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-123"
        assert "error" not in response
        assert response["result"]["success"] is True
        assert response["result"]["message"]
        assert response["result"]["cloud"] == "aws"
        assert response["result"]["details"] is not None
        
        # Verify AWS calls
        mock_sts.get_caller_identity.assert_called_once()
        mock_ec2.describe_security_groups.assert_called_once_with(GroupIds=['sg-123456'])
        mock_ec2.authorize_security_group_ingress.assert_called_once()
    
    @patch('boto3.client')
    def test_list_whitelist_rules_flow(self, mock_boto_client, server):
        """Test complete flow of listing whitelist rules."""
        # Mock AWS clients
        mock_ec2 = Mock()
        mock_sts = Mock()
        
        def client_factory(service, **kwargs):
            if service == 'ec2':
                return mock_ec2
            elif service == 'sts':
                return mock_sts
            raise ValueError(f"Unknown service: {service}")
        
        mock_boto_client.side_effect = client_factory
        
        # Mock STS response
        mock_sts.get_caller_identity.return_value = {
            'UserId': 'AIDAI23456789EXAMPLE',
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/TestUser'
        }
        
        # Mock EC2 response with existing rules
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-123456',
                'GroupName': 'test-sg',
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [
                            {
                                'CidrIp': '10.0.0.0/8',
                                'Description': 'Internal SSH access'
                            },
                            {
                                'CidrIp': '192.168.1.100/32',
                                'Description': 'Admin SSH access'
                            }
                        ]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': 'Public HTTPS access'
                            }
                        ]
                    }
                ]
            }]
        }
        
        # Create request
        request = {
            "jsonrpc": "2.0",
            "id": "test-list-123",
            "method": "tools/call",
            "params": {
                "name": "whitelist_list",
                "arguments": {
                    "credentials": {
                        "cloud": "aws",
                        "aws_credentials": {
                            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                            "region": "us-east-1"
                        }
                    },
                    "security_group_id": "sg-123456"
                }
            }
        }
        
        # Process request
        response_str = server.process_request(json.dumps(request))
        response = json.loads(response_str)
        
        # Verify response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-list-123"
        assert "error" not in response
        assert response["result"]["success"] is True
        assert response["result"]["count"] == 3
        assert len(response["result"]["rules"]) == 3
        
        # Check specific rules
        rules = response["result"]["rules"]
        ssh_rules = [r for r in rules if r["port"] == 22]
        https_rules = [r for r in rules if r["port"] == 443]
        
        assert len(ssh_rules) == 2
        assert len(https_rules) == 1
        assert https_rules[0]["cidr_ip"] == "0.0.0.0/0"
    
    @patch('boto3.client')
    def test_error_handling_flow(self, mock_boto_client, server):
        """Test error handling in the complete flow."""
        # Mock AWS clients
        mock_ec2 = Mock()
        mock_sts = Mock()
        
        def client_factory(service, **kwargs):
            if service == 'ec2':
                return mock_ec2
            elif service == 'sts':
                return mock_sts
            raise ValueError(f"Unknown service: {service}")
        
        mock_boto_client.side_effect = client_factory
        
        # Mock STS to fail credential validation
        mock_sts.get_caller_identity.side_effect = Exception("Invalid credentials")
        
        # Create request with invalid credentials
        request = {
            "jsonrpc": "2.0",
            "id": "test-error-123",
            "method": "tools/call",
            "params": {
                "name": "whitelist_add",
                "arguments": {
                    "credentials": {
                        "cloud": "aws",
                        "aws_credentials": {
                            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                            "secret_access_key": "invalid-secret",
                            "region": "us-east-1"
                        }
                    },
                    "security_group_id": "sg-123456",
                    "ip_address": "192.168.1.1"
                }
            }
        }
        
        # Process request
        response_str = server.process_request(json.dumps(request))
        response = json.loads(response_str)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-error-123"
        assert "result" not in response
        assert response["error"]["code"] == -32602  # Invalid params
        assert "Invalid credentials" in response["error"]["message"]
    
    def test_invalid_method_flow(self, server):
        """Test handling of invalid method."""
        request = {
            "jsonrpc": "2.0",
            "id": "test-invalid-method",
            "method": "invalid/method",
            "params": {}
        }
        
        response_str = server.process_request(json.dumps(request))
        response = json.loads(response_str)
        
        assert response["error"]["code"] == -32601  # Method not found
        assert "Method not found" in response["error"]["message"]
    
    def test_malformed_json_flow(self, server):
        """Test handling of malformed JSON."""
        request_str = '{"jsonrpc": "2.0", "id": "test", invalid json}'
        
        response_str = server.process_request(request_str)
        response = json.loads(response_str)
        
        assert response["error"]["code"] == -32700  # Parse error
        assert "Parse error" in response["error"]["message"]