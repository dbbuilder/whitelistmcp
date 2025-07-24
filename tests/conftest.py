"""Shared pytest fixtures and configuration."""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

from whitelistmcp.config import Config, CloudProvider, DefaultParameters
from whitelistmcp.utils.credential_validator import AWSCredentials
from whitelistmcp.azure.service import AzureCredentials
from whitelistmcp.gcp.service import GCPCredentials
from whitelistmcp.cloud_service import CloudCredentials


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Config()
    config.default_parameters = DefaultParameters(
        cloud_provider=CloudProvider.AWS,
        port=22,
        protocol="tcp",
        aws_region="us-east-1",
        azure_region="eastus",
        gcp_region="us-central1"
    )
    return config


@pytest.fixture
def aws_credentials():
    """Create mock AWS credentials."""
    return AWSCredentials(
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1"
    )


@pytest.fixture
def azure_credentials():
    """Create mock Azure credentials."""
    return AzureCredentials(
        client_id="00000000-0000-0000-0000-000000000000",
        client_secret="mock_secret",
        tenant_id="00000000-0000-0000-0000-000000000000",
        subscription_id="00000000-0000-0000-0000-000000000000",
        region="eastus"
    )


@pytest.fixture
def gcp_credentials():
    """Create mock GCP credentials."""
    return GCPCredentials(
        project_id="test-project-123",
        credentials_path="/path/to/creds.json",
        region="us-central1",
        zone="us-central1-a"
    )


@pytest.fixture
def multi_cloud_credentials():
    """Create mock multi-cloud credentials."""
    return CloudCredentials(
        cloud=CloudProvider.ALL,
        aws_credentials=AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1"
        ),
        azure_credentials=AzureCredentials(
            client_id="00000000-0000-0000-0000-000000000000",
            client_secret="mock_secret",
            tenant_id="00000000-0000-0000-0000-000000000000",
            subscription_id="00000000-0000-0000-0000-000000000000",
            region="eastus"
        ),
        gcp_credentials=GCPCredentials(
            project_id="test-project-123",
            credentials_path="/path/to/creds.json",
            region="us-central1",
            zone="us-central1-a"
        )
    )


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 EC2 client."""
    client = MagicMock()
    
    # Mock describe_security_groups
    client.describe_security_groups.return_value = {
        'SecurityGroups': [{
            'GroupId': 'sg-12345678',
            'GroupName': 'test-sg',
            'Description': 'Test security group',
            'IpPermissions': []
        }]
    }
    
    # Mock authorize_security_group_ingress
    client.authorize_security_group_ingress.return_value = {
        'Return': True,
        'SecurityGroupRules': []
    }
    
    # Mock revoke_security_group_ingress
    client.revoke_security_group_ingress.return_value = {
        'Return': True
    }
    
    return client


@pytest.fixture
def mock_azure_client():
    """Create a mock Azure NetworkManagementClient."""
    client = MagicMock()
    
    # Mock NSG operations
    nsg = MagicMock()
    nsg.name = "test-nsg"
    nsg.location = "eastus"
    nsg.security_rules = []
    
    client.network_security_groups.get.return_value = nsg
    client.security_rules.begin_create_or_update.return_value = MagicMock()
    client.security_rules.begin_delete.return_value = MagicMock()
    
    return client


@pytest.fixture
def mock_gcp_client():
    """Create a mock GCP Compute client."""
    client = MagicMock()
    
    # Mock firewall operations
    client.firewalls.return_value.list.return_value.execute.return_value = {
        'items': []
    }
    client.firewalls.return_value.insert.return_value.execute.return_value = {
        'name': 'operation-123'
    }
    client.firewalls.return_value.delete.return_value.execute.return_value = {
        'name': 'operation-456'
    }
    
    return client


@pytest.fixture
def sample_mcp_request():
    """Create a sample MCP request."""
    return {
        "jsonrpc": "2.0",
        "id": "test-123",
        "method": "whitelist_add",
        "params": {
            "credentials": {
                "cloud": "aws",
                "aws_credentials": {
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                    "region": "us-east-1"
                }
            },
            "security_group_id": "sg-12345678",
            "ip_address": "192.168.1.1",
            "port": 22,
            "protocol": "tcp",
            "description": "Test rule"
        }
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singletons between tests."""
    # Add any singleton resets here if needed
    yield
