"""Unit tests for configuration module."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from whitelistmcp.config import (
    Config, CloudProvider, DefaultParameters, SecuritySettings,
    PortMapping, CredentialProfile, load_config, get_port_number
)


class TestCloudProvider:
    """Test CloudProvider enum."""
    
    def test_cloud_provider_values(self):
        """Test CloudProvider enum values."""
        assert CloudProvider.AWS.value == "aws"
        assert CloudProvider.AZURE.value == "azure"
        assert CloudProvider.GCP.value == "gcp"
        assert CloudProvider.ALL.value == "all"


class TestDefaultParameters:
    """Test DefaultParameters model."""
    
    def test_default_values(self):
        """Test default parameter values."""
        params = DefaultParameters()
        assert params.cloud_provider == CloudProvider.AWS
        assert params.port == 22
        assert params.protocol == "tcp"
        assert params.aws_region == "us-east-1"
        assert params.azure_region == "eastus"
        assert params.gcp_region == "us-central1"
        assert params.gcp_additive_only is True
    
    def test_port_validation(self):
        """Test port number validation."""
        # Valid port
        params = DefaultParameters(port=443)
        assert params.port == 443
        
        # Invalid ports
        with pytest.raises(ValueError, match="Port must be between"):
            DefaultParameters(port=0)
        
        with pytest.raises(ValueError, match="Port must be between"):
            DefaultParameters(port=65536)
    
    def test_protocol_validation(self):
        """Test protocol validation."""
        # Valid protocols
        for protocol in ["tcp", "udp", "icmp", "-1"]:
            params = DefaultParameters(protocol=protocol)
            assert params.protocol == protocol
        
        # Invalid protocol
        with pytest.raises(ValueError, match="Invalid protocol"):
            DefaultParameters(protocol="invalid")
    
    def test_aws_region_validation(self):
        """Test AWS region format validation."""
        # Valid regions
        valid_regions = ["us-east-1", "eu-west-2", "ap-southeast-1"]
        for region in valid_regions:
            params = DefaultParameters(aws_region=region)
            assert params.aws_region == region
        
        # Invalid regions
        with pytest.raises(ValueError, match="Invalid AWS region"):
            DefaultParameters(aws_region="invalid-region")
    
    def test_azure_region_validation(self):
        """Test Azure region format validation."""
        # Valid regions
        valid_regions = ["eastus", "westeurope", "australiaeast"]
        for region in valid_regions:
            params = DefaultParameters(azure_region=region)
            assert params.azure_region == region
        
        # Invalid regions
        with pytest.raises(ValueError, match="Invalid Azure region"):
            DefaultParameters(azure_region="invalid region")


class TestSecuritySettings:
    """Test SecuritySettings model."""
    
    def test_default_values(self):
        """Test default security settings."""
        settings = SecuritySettings()
        assert settings.require_mfa is False
        assert settings.allowed_ip_ranges == []
        assert settings.max_rule_duration_hours == 0
        assert settings.rate_limit_per_minute == 60
        assert settings.enable_audit_logging is True
    
    def test_ip_range_validation(self):
        """Test IP range validation."""
        # Valid CIDR ranges
        settings = SecuritySettings(
            allowed_ip_ranges=["192.168.1.0/24", "10.0.0.0/8"]
        )
        assert len(settings.allowed_ip_ranges) == 2
        
        # Invalid CIDR range
        with pytest.raises(ValueError, match="Invalid CIDR format"):
            SecuritySettings(allowed_ip_ranges=["192.168.1.1"])
    
    def test_rate_limit_validation(self):
        """Test rate limit validation."""
        # Valid rate limit
        settings = SecuritySettings(rate_limit_per_minute=100)
        assert settings.rate_limit_per_minute == 100
        
        # Invalid rate limit
        with pytest.raises(ValueError, match="Rate limit must be at least 1"):
            SecuritySettings(rate_limit_per_minute=0)


class TestPortMapping:
    """Test PortMapping model."""
    
    def test_port_mapping(self):
        """Test port mapping creation."""
        mapping = PortMapping(name="ssh", port=22, description="SSH access")
        assert mapping.name == "ssh"
        assert mapping.port == 22
        assert mapping.description == "SSH access"
    
    def test_port_validation(self):
        """Test port validation in mapping."""
        with pytest.raises(ValueError, match="Port must be between"):
            PortMapping(name="invalid", port=99999)


class TestCredentialProfile:
    """Test CredentialProfile model."""
    
    def test_aws_profile(self):
        """Test AWS credential profile."""
        profile = CredentialProfile(
            name="prod-aws",
            cloud=CloudProvider.AWS,
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="secret",
            aws_region="us-west-2"
        )
        assert profile.name == "prod-aws"
        assert profile.cloud == CloudProvider.AWS
        assert profile.aws_region == "us-west-2"
    
    def test_azure_profile(self):
        """Test Azure credential profile."""
        profile = CredentialProfile(
            name="prod-azure",
            cloud=CloudProvider.AZURE,
            azure_client_id="client-id",
            azure_tenant_id="tenant-id",
            azure_subscription_id="sub-id",
            azure_region="westus"
        )
        assert profile.name == "prod-azure"
        assert profile.cloud == CloudProvider.AZURE
        assert profile.azure_region == "westus"


class TestConfig:
    """Test Config model."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = Config()
        assert len(config.credential_profiles) == 0
        assert isinstance(config.default_parameters, DefaultParameters)
        assert isinstance(config.security_settings, SecuritySettings)
        assert len(config.port_mappings) == 0
    
    def test_get_profile(self):
        """Test getting credential profile by name."""
        profile = CredentialProfile(name="test", cloud=CloudProvider.AWS)
        config = Config(credential_profiles=[profile])
        
        assert config.get_profile("test") == profile
        assert config.get_profile("nonexistent") is None
    
    def test_get_port_mapping(self):
        """Test getting port mapping by name."""
        mapping = PortMapping(name="https", port=443)
        config = Config(port_mappings=[mapping])
        
        assert config.get_port_mapping("https") == mapping
        assert config.get_port_mapping("nonexistent") is None
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "credential_profiles": [
                {"name": "test", "cloud": "aws"}
            ],
            "default_parameters": {
                "port": 443,
                "protocol": "tcp"
            },
            "security_settings": {
                "rate_limit_per_minute": 120
            },
            "port_mappings": [
                {"name": "https", "port": 443}
            ]
        }
        
        config = Config.from_dict(data)
        assert len(config.credential_profiles) == 1
        assert config.default_parameters.port == 443
        assert config.security_settings.rate_limit_per_minute == 120
        assert len(config.port_mappings) == 1
    
    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = Config()
        data = config.to_dict()
        
        assert "credential_profiles" in data
        assert "default_parameters" in data
        assert "security_settings" in data
        assert "port_mappings" in data


class TestLoadConfig:
    """Test load_config function."""
    
    @patch("builtins.open", new_callable=mock_open, read_data='{}')
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_empty_config(self, mock_exists, mock_file):
        """Test loading empty config file."""
        config = load_config("test.json")
        assert isinstance(config, Config)
    
    @patch("builtins.open", new_callable=mock_open, read_data='{"default_parameters": {"port": 8080}}')
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_config_with_params(self, mock_exists, mock_file):
        """Test loading config with parameters."""
        config = load_config("test.json")
        assert config.default_parameters.port == 8080
    
    @patch("pathlib.Path.exists", return_value=False)
    def test_load_config_no_file(self, mock_exists):
        """Test loading config when file doesn't exist."""
        config = load_config("nonexistent.json")
        assert isinstance(config, Config)
    
    @patch.dict(os.environ, {
        "CLOUD_PROVIDER": "azure",
        "WHITELIST_MCP_PORT": "443",
        "WHITELIST_MCP_PROTOCOL": "tcp",
        "AWS_DEFAULT_REGION": "eu-west-1",
        "AZURE_DEFAULT_REGION": "westeurope",
        "GCP_DEFAULT_REGION": "europe-west1"
    })
    def test_load_config_env_override(self):
        """Test environment variable overrides."""
        config = load_config()
        assert config.default_parameters.cloud_provider == CloudProvider.AZURE
        assert config.default_parameters.port == 443
        assert config.default_parameters.aws_region == "eu-west-1"
        assert config.default_parameters.azure_region == "westeurope"
        assert config.default_parameters.gcp_region == "europe-west1"
    
    @patch.dict(os.environ, {
        "WHITELIST_MCP_PORT": "invalid",
        "WHITELIST_MCP_RATE_LIMIT": "invalid"
    })
    def test_load_config_invalid_env(self, capsys):
        """Test invalid environment variable values."""
        config = load_config()
        captured = capsys.readouterr()
        assert "Warning: Invalid port" in captured.err
        assert "Warning: Invalid rate limit" in captured.err


class TestGetPortNumber:
    """Test get_port_number function."""
    
    def test_numeric_port(self, mock_config):
        """Test numeric port input."""
        assert get_port_number("22", mock_config) == 22
        assert get_port_number("443", mock_config) == 443
    
    def test_invalid_numeric_port(self, mock_config):
        """Test invalid numeric port."""
        with pytest.raises(ValueError, match="Invalid port"):
            get_port_number("99999", mock_config)
    
    def test_common_port_names(self, mock_config):
        """Test common port name mappings."""
        assert get_port_number("ssh", mock_config) == 22
        assert get_port_number("http", mock_config) == 80
        assert get_port_number("https", mock_config) == 443
        assert get_port_number("mysql", mock_config) == 3306
    
    def test_port_mapping(self, mock_config):
        """Test custom port mapping."""
        mapping = PortMapping(name="custom", port=9999)
        mock_config.port_mappings = [mapping]
        assert get_port_number("custom", mock_config) == 9999
    
    def test_invalid_port_name(self, mock_config):
        """Test invalid port name."""
        with pytest.raises(ValueError, match="Invalid port"):
            get_port_number("nonexistent", mock_config)