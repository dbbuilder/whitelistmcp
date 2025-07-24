"""Configuration management for Multi-Cloud Whitelisting MCP Server."""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class CloudProvider(str, Enum):
    """Supported cloud providers."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ALL = "all"


class CredentialProfile(BaseModel):
    """Multi-cloud credential profile configuration."""
    
    name: str
    cloud: CloudProvider = CloudProvider.AWS
    
    # AWS-specific credentials and settings
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_role_arn: Optional[str] = None
    
    # Azure-specific credentials and settings
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_subscription_id: Optional[str] = None
    azure_region: str = "eastus"
    
    # GCP-specific credentials and settings
    gcp_project_id: Optional[str] = None
    gcp_credentials_path: Optional[str] = None
    gcp_credentials_json: Optional[Dict[str, Any]] = None
    gcp_region: str = "us-central1"
    
    @field_validator("aws_region")
    def validate_aws_region(cls, v):
        """Validate AWS region format."""
        if v:
            # AWS region pattern: xx-xxxx-n
            pattern = r"^[a-z]{2}-[a-z]+-\d{1,2}$"
            if not re.match(pattern, v):
                raise ValueError(f"Invalid AWS region format: {v}")
        return v
    
    @field_validator("azure_region")
    def validate_azure_region(cls, v):
        """Validate Azure region format."""
        if v:
            # Azure regions are typically lowercase with no spaces
            pattern = r"^[a-z]+[a-z0-9]*$"
            if not re.match(pattern, v):
                raise ValueError(f"Invalid Azure region format: {v}")
        return v


class DefaultParameters(BaseModel):
    """Default parameters for whitelisting operations."""
    
    # MCP runtime properties (shared across clouds)
    cloud_provider: CloudProvider = CloudProvider.AWS
    port: int = 22
    protocol: str = "tcp"
    description_template: str = "Added by MCP on {date} for {user}"
    
    # AWS-specific defaults
    aws_region: str = "us-east-1"
    aws_security_group_id: Optional[str] = None
    aws_vpc_id: Optional[str] = None
    
    # Azure-specific defaults
    azure_region: str = "eastus"
    azure_resource_group: Optional[str] = None
    azure_nsg_name: Optional[str] = None
    azure_location: Optional[str] = None
    
    # GCP-specific defaults
    gcp_region: str = "us-central1"
    gcp_zone: str = "us-central1-a"
    gcp_project_id: Optional[str] = None
    gcp_network: str = "default"
    gcp_additive_only: bool = True
    
    @field_validator("port")
    def validate_port(cls, v):
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v
    
    @field_validator("protocol")
    def validate_protocol(cls, v):
        """Validate protocol."""
        valid_protocols = ["tcp", "udp", "icmp", "-1"]  # -1 means all protocols
        if v not in valid_protocols:
            raise ValueError(f"Invalid protocol: {v}. Must be one of {valid_protocols}")
        return v
    
    @field_validator("aws_region")
    def validate_aws_region(cls, v):
        """Validate AWS region format."""
        if v:
            pattern = r"^[a-z]{2}-[a-z]+-\d{1,2}$"
            if not re.match(pattern, v):
                raise ValueError(f"Invalid AWS region format: {v}")
        return v
    
    @field_validator("azure_region", "azure_location")
    def validate_azure_region(cls, v):
        """Validate Azure region format."""
        if v:
            pattern = r"^[a-z]+[a-z0-9]*$"
            if not re.match(pattern, v):
                raise ValueError(f"Invalid Azure region format: {v}")
        return v


class SecuritySettings(BaseModel):
    """Security settings for the MCP server."""
    
    require_mfa: bool = False
    allowed_ip_ranges: List[str] = Field(default_factory=list)
    max_rule_duration_hours: int = 0  # 0 means no limit
    rate_limit_per_minute: int = 60
    enable_audit_logging: bool = True
    
    @field_validator("allowed_ip_ranges")
    def validate_ip_ranges(cls, v):
        """Validate IP range format."""
        cidr_pattern = r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"
        for ip_range in v:
            if not re.match(cidr_pattern, ip_range):
                raise ValueError(f"Invalid CIDR format: {ip_range}")
        return v
    
    @field_validator("rate_limit_per_minute")
    def validate_rate_limit(cls, v):
        """Validate rate limit."""
        if v < 1:
            raise ValueError(f"Rate limit must be at least 1, got {v}")
        return v


class PortMapping(BaseModel):
    """Named port mapping."""
    
    name: str
    port: int
    description: Optional[str] = None
    
    @field_validator("port")
    def validate_port(cls, v):
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v


class Config(BaseModel):
    """Main configuration for Multi-Cloud Whitelisting MCP Server."""
    
    credential_profiles: List[CredentialProfile] = Field(default_factory=list)
    default_parameters: DefaultParameters = Field(default_factory=DefaultParameters)
    security_settings: SecuritySettings = Field(default_factory=SecuritySettings)
    port_mappings: List[PortMapping] = Field(default_factory=list)
    
    def get_profile(self, name: str) -> Optional[CredentialProfile]:
        """Get credential profile by name."""
        for profile in self.credential_profiles:
            if profile.name == name:
                return profile
        return None
    
    def get_port_mapping(self, name: str) -> Optional[PortMapping]:
        """Get port mapping by name."""
        for mapping in self.port_mappings:
            if mapping.name == name:
                return mapping
        return None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        # Convert nested dictionaries to their respective models
        if "credential_profiles" in data:
            data["credential_profiles"] = [
                CredentialProfile(**profile) if isinstance(profile, dict) else profile
                for profile in data["credential_profiles"]
            ]
        
        if "default_parameters" in data:
            data["default_parameters"] = (
                DefaultParameters(**data["default_parameters"])
                if isinstance(data["default_parameters"], dict)
                else data["default_parameters"]
            )
        
        if "security_settings" in data:
            data["security_settings"] = (
                SecuritySettings(**data["security_settings"])
                if isinstance(data["security_settings"], dict)
                else data["security_settings"]
            )
        
        if "port_mappings" in data:
            data["port_mappings"] = [
                PortMapping(**mapping) if isinstance(mapping, dict) else mapping
                for mapping in data["port_mappings"]
            ]
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump()


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file and environment variables.
    
    Args:
        config_path: Path to configuration file. If not provided,
                    looks for mcp_config.json in current directory.
    
    Returns:
        Config object with loaded configuration.
    
    Environment variables (override file config):
        MCP Runtime (shared across clouds):
        - CLOUD_PROVIDER: Cloud provider selection (aws, azure, gcp, all)
        - WHITELIST_MCP_PORT: Default port
        - WHITELIST_MCP_PROTOCOL: Default protocol
        - WHITELIST_MCP_RATE_LIMIT: Rate limit per minute
        
        AWS-specific:
        - AWS_DEFAULT_REGION: Default AWS region
        - AWS_DEFAULT_SECURITY_GROUP_ID: Default security group
        - AWS_DEFAULT_VPC_ID: Default VPC
        
        Azure-specific:
        - AZURE_DEFAULT_REGION: Default Azure region
        - AZURE_DEFAULT_LOCATION: Default Azure location
        - AZURE_DEFAULT_RESOURCE_GROUP: Default resource group
        - AZURE_DEFAULT_NSG_NAME: Default NSG name
        
        GCP-specific:
        - GCP_DEFAULT_REGION: Default GCP region
        - GCP_DEFAULT_ZONE: Default GCP zone
        - GCP_PROJECT_ID: Default GCP project
        - GCP_DEFAULT_NETWORK: Default VPC network
        - GCP_ADDITIVE_ONLY: Enable additive-only mode
    """
    # Start with default config
    config_dict: Dict[str, Any] = {}
    
    # Load from file if it exists
    if config_path is None:
        config_path = "mcp_config.json"
    
    config_file = Path(config_path)
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)
                config_dict = file_config  # Replace entire dict, not update
        except Exception as e:
            # Log error but continue with defaults
            print(f"Warning: Failed to load config file {config_path}: {e}", file=sys.stderr)
    
    # Create config object
    config = Config.from_dict(config_dict)
    
    # Override with environment variables
    # Cloud provider selection
    cloud_provider = os.environ.get("CLOUD_PROVIDER", "aws").lower()
    if cloud_provider in ["aws", "azure", "gcp", "all"]:
        config.default_parameters.cloud_provider = CloudProvider(cloud_provider)
    
    # AWS-specific overrides
    if "AWS_DEFAULT_REGION" in os.environ:
        config.default_parameters.aws_region = os.environ["AWS_DEFAULT_REGION"]
    if "AWS_DEFAULT_SECURITY_GROUP_ID" in os.environ:
        config.default_parameters.aws_security_group_id = os.environ["AWS_DEFAULT_SECURITY_GROUP_ID"]
    if "AWS_DEFAULT_VPC_ID" in os.environ:
        config.default_parameters.aws_vpc_id = os.environ["AWS_DEFAULT_VPC_ID"]
    
    # Azure-specific overrides
    if "AZURE_DEFAULT_REGION" in os.environ:
        config.default_parameters.azure_region = os.environ["AZURE_DEFAULT_REGION"]
    if "AZURE_DEFAULT_LOCATION" in os.environ:
        config.default_parameters.azure_location = os.environ["AZURE_DEFAULT_LOCATION"]
    if "AZURE_DEFAULT_RESOURCE_GROUP" in os.environ:
        config.default_parameters.azure_resource_group = os.environ["AZURE_DEFAULT_RESOURCE_GROUP"]
    if "AZURE_DEFAULT_NSG_NAME" in os.environ:
        config.default_parameters.azure_nsg_name = os.environ["AZURE_DEFAULT_NSG_NAME"]
    
    # GCP-specific overrides
    if "GCP_DEFAULT_REGION" in os.environ:
        config.default_parameters.gcp_region = os.environ["GCP_DEFAULT_REGION"]
    if "GCP_DEFAULT_ZONE" in os.environ:
        config.default_parameters.gcp_zone = os.environ["GCP_DEFAULT_ZONE"]
    if "GCP_PROJECT_ID" in os.environ:
        config.default_parameters.gcp_project_id = os.environ["GCP_PROJECT_ID"]
    if "GCP_DEFAULT_NETWORK" in os.environ:
        config.default_parameters.gcp_network = os.environ["GCP_DEFAULT_NETWORK"]
    gcp_additive = os.environ.get("GCP_ADDITIVE_ONLY", "true").lower()
    config.default_parameters.gcp_additive_only = gcp_additive != "false"
    
    # Common MCP runtime overrides
    if "WHITELIST_MCP_PORT" in os.environ:
        try:
            config.default_parameters.port = int(os.environ["WHITELIST_MCP_PORT"])
        except ValueError:
            print(f"Warning: Invalid port in WHITELIST_MCP_PORT: {os.environ['WHITELIST_MCP_PORT']}", file=sys.stderr)
    
    if "WHITELIST_MCP_PROTOCOL" in os.environ:
        config.default_parameters.protocol = os.environ["WHITELIST_MCP_PROTOCOL"]
    
    if "WHITELIST_MCP_RATE_LIMIT" in os.environ:
        try:
            config.security_settings.rate_limit_per_minute = int(os.environ["WHITELIST_MCP_RATE_LIMIT"])
        except ValueError:
            print(f"Warning: Invalid rate limit in WHITELIST_MCP_RATE_LIMIT: {os.environ['WHITELIST_MCP_RATE_LIMIT']}", file=sys.stderr)
    
    return config


def get_port_number(port_input: str, config: Config) -> int:
    """Get port number from input string or mapping.
    
    Args:
        port_input: Port number or port name
        config: Configuration object
    
    Returns:
        Port number
    
    Raises:
        ValueError: If port is invalid
    """
    # Try to parse as integer
    try:
        port = int(port_input)
        if 1 <= port <= 65535:
            return port
        else:
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
    except ValueError:
        pass
    
    # Try to find in port mappings
    mapping = config.get_port_mapping(port_input)
    if mapping:
        return mapping.port
    
    # Common port names
    common_ports = {
        "ssh": 22,
        "telnet": 23,
        "smtp": 25,
        "http": 80,
        "https": 443,
        "rdp": 3389,
        "mysql": 3306,
        "postgresql": 5432,
        "mongodb": 27017,
    }
    
    if port_input.lower() in common_ports:
        return common_ports[port_input.lower()]
    
    raise ValueError(f"Invalid port: {port_input}")