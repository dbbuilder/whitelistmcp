"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock, patch
import boto3
from moto import mock_aws


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    return {
        "access_key_id": "test-access-key",
        "secret_access_key": "test-secret-key",
        "session_token": "test-session-token",
        "region": "us-east-1"
    }


@pytest.fixture
def mock_ec2_client():
    """Create a mocked EC2 client."""
    with mock_aws():
        client = boto3.client("ec2", region_name="us-east-1")
        yield client


@pytest.fixture
def sample_security_group(mock_ec2_client):
    """Create a sample security group for testing."""
    response = mock_ec2_client.create_security_group(
        GroupName="test-sg",
        Description="Test security group"
    )
    sg_id = response["GroupId"]
    
    # Add some initial rules
    mock_ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [{"CidrIp": "10.0.0.0/24"}]
            }
        ]
    )
    
    return sg_id


@pytest.fixture
def mcp_request_base():
    """Base MCP request structure."""
    return {
        "jsonrpc": "2.0",
        "id": "test-request-id",
        "method": "",
        "params": {}
    }