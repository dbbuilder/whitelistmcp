"""Unit tests for configuration module."""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from awswhitelist.config import (
    Config, 
    CredentialProfile,
    DefaultParameters,
    SecuritySettings,
    PortMapping,
    load_config,
    get_port_number
)


class TestCredentialProfile:
    """Test credential profile functionality."""
    
    def test_credential_profile_creation(self):
        """Test creating a credential profile."""
        profile = CredentialProfile(
            name="test-profile",
            region="us-east-1",
            role_arn="arn:aws:iam::123456789012:role/TestRole"
        )
        assert profile.name == "test-profile"
        assert profile.region == "us-east-1"
        assert profile.role_arn == "arn:aws:iam::123456789012:role/TestRole"
    
    def test_credential_profile_validation(self):
        """Test credential profile validation."""
        # Valid profile
        profile = CredentialProfile(
            name="valid-profile",
            region="us-west-2"
        )
        assert profile.region == "us-west-2"
        
        # Invalid region format should raise error
        with pytest.raises(ValueError):
            CredentialProfile(
                name="invalid-profile",
                region="invalid-region-123"
            )


class TestDefaultParameters:
    """Test default parameters functionality."""
    
    def test_default_parameters_creation(self):
        """Test creating default parameters."""
        params = DefaultParameters(
            region="us-east-1",
            port=443,
            protocol="tcp",
            description_template="Added by {user} on {date}"
        )
        assert params.region == "us-east-1"
        assert params.port == 443
        assert params.protocol == "tcp"
        assert params.description_template == "Added by {user} on {date}"
    
    def test_default_parameters_defaults(self):
        """Test default parameter values."""
        params = DefaultParameters()
        assert params.region == "us-east-1"
        assert params.port == 22
        assert params.protocol == "tcp"
        assert "MCP" in params.description_template


class TestSecuritySettings:
    """Test security settings functionality."""
    
    def test_security_settings_creation(self):
        """Test creating security settings."""
        settings = SecuritySettings(
            require_mfa=True,
            allowed_ip_ranges=["10.0.0.0/8", "192.168.0.0/16"],
            max_rule_duration_hours=24,
            rate_limit_per_minute=10,
            enable_audit_logging=True
        )
        assert settings.require_mfa is True
        assert len(settings.allowed_ip_ranges) == 2
        assert settings.max_rule_duration_hours == 24
        assert settings.rate_limit_per_minute == 10
        assert settings.enable_audit_logging is True
    
    def test_security_settings_defaults(self):
        """Test default security settings."""
        settings = SecuritySettings()
        assert settings.require_mfa is False
        assert settings.allowed_ip_ranges == []
        assert settings.max_rule_duration_hours == 0  # No limit
        assert settings.rate_limit_per_minute == 60
        assert settings.enable_audit_logging is True


class TestPortMapping:
    """Test port mapping functionality."""
    
    def test_port_mapping_creation(self):
        """Test creating port mappings."""
        mapping = PortMapping(
            name="https",
            port=443,
            description="HTTPS traffic"
        )
        assert mapping.name == "https"
        assert mapping.port == 443
        assert mapping.description == "HTTPS traffic"


class TestConfig:
    """Test main configuration class."""
    
    def test_config_creation(self):
        """Test creating a configuration."""
        config = Config(
            credential_profiles=[
                CredentialProfile(name="default", region="us-east-1")
            ],
            default_parameters=DefaultParameters(),
            security_settings=SecuritySettings(),
            port_mappings=[
                PortMapping(name="ssh", port=22, description="SSH access")
            ]
        )
        assert len(config.credential_profiles) == 1
        assert config.default_parameters.region == "us-east-1"
        assert config.security_settings.rate_limit_per_minute == 60
        assert len(config.port_mappings) == 1
    
    def test_config_get_profile(self):
        """Test getting a profile by name."""
        config = Config(
            credential_profiles=[
                CredentialProfile(name="default", region="us-east-1"),
                CredentialProfile(name="production", region="us-west-2")
            ]
        )
        
        # Test existing profile
        profile = config.get_profile("production")
        assert profile is not None
        assert profile.region == "us-west-2"
        
        # Test non-existing profile
        profile = config.get_profile("non-existent")
        assert profile is None
    
    def test_config_get_port_mapping(self):
        """Test getting port mapping by name."""
        config = Config(
            port_mappings=[
                PortMapping(name="https", port=443),
                PortMapping(name="ssh", port=22)
            ]
        )
        
        # Test existing mapping
        mapping = config.get_port_mapping("https")
        assert mapping is not None
        assert mapping.port == 443
        
        # Test non-existing mapping
        mapping = config.get_port_mapping("telnet")
        assert mapping is None


class TestLoadConfig:
    """Test configuration loading functionality."""
    
    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        config_data = {
            "credential_profiles": [
                {"name": "default", "region": "us-east-1"}
            ],
            "default_parameters": {
                "region": "us-east-1",
                "port": 443
            },
            "security_settings": {
                "require_mfa": True,
                "rate_limit_per_minute": 30
            },
            "port_mappings": [
                {"name": "https", "port": 443, "description": "HTTPS"}
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
            with patch("pathlib.Path.exists", return_value=True):
                config = load_config("test_config.json")
            
            assert len(config.credential_profiles) == 1
            assert config.default_parameters.port == 443
            assert config.security_settings.require_mfa is True
            assert len(config.port_mappings) == 1
    
    def test_load_config_file_not_found(self):
        """Test loading configuration when file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            config = load_config("non_existent.json")
            
            # Should return default config
            assert len(config.credential_profiles) == 0
            assert config.default_parameters.region == "us-east-1"
    
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "AWS_WHITELIST_REGION": "eu-west-1",
            "AWS_WHITELIST_PORT": "8080",
            "AWS_WHITELIST_PROTOCOL": "udp",
            "AWS_WHITELIST_RATE_LIMIT": "120"
        }
        
        with patch.dict(os.environ, env_vars):
            config = load_config()
            
            assert config.default_parameters.region == "eu-west-1"
            assert config.default_parameters.port == 8080
            assert config.default_parameters.protocol == "udp"
            assert config.security_settings.rate_limit_per_minute == 120


class TestGetPortNumber:
    """Test port number resolution functionality."""
    
    def test_get_port_number_numeric(self):
        """Test getting port number from numeric string."""
        config = Config()
        assert get_port_number("443", config) == 443
        assert get_port_number("8080", config) == 8080
    
    def test_get_port_number_from_mapping(self):
        """Test getting port number from named mapping."""
        config = Config(
            port_mappings=[
                PortMapping(name="https", port=443),
                PortMapping(name="ssh", port=22)
            ]
        )
        
        assert get_port_number("https", config) == 443
        assert get_port_number("ssh", config) == 22
    
    def test_get_port_number_invalid(self):
        """Test getting port number with invalid input."""
        config = Config()
        
        with pytest.raises(ValueError):
            get_port_number("invalid-port", config)
        
        with pytest.raises(ValueError):
            get_port_number("99999", config)  # Port out of range