"""Configuration management for AWS Whitelisting MCP Server."""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class CredentialProfile(BaseModel):
    """AWS credential profile configuration."""
    
    name: str
    region: str = "us-east-1"
    role_arn: Optional[str] = None
    
    @field_validator("region")
    def validate_region(cls, v):
        """Validate AWS region format."""
        # AWS region pattern: xx-xxxx-n
        pattern = r"^[a-z]{2}-[a-z]+-\d{1,2}$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v


class DefaultParameters(BaseModel):
    """Default parameters for whitelisting operations."""
    
    region: str = "us-east-1"
    port: int = 22
    protocol: str = "tcp"
    description_template: str = "Added by MCP on {date} for {user}"
    
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
    """Main configuration for AWS Whitelisting MCP Server."""
    
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
        if "default_parameters" in data and isinstance(data["default_parameters"], dict):
            data["default_parameters"] = DefaultParameters(**data["default_parameters"])
        if "security_settings" in data and isinstance(data["security_settings"], dict):
            data["security_settings"] = SecuritySettings(**data["security_settings"])
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
        - AWS_WHITELIST_REGION: Default AWS region
        - AWS_WHITELIST_PORT: Default port
        - AWS_WHITELIST_PROTOCOL: Default protocol
        - AWS_WHITELIST_RATE_LIMIT: Rate limit per minute
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
    if "AWS_WHITELIST_REGION" in os.environ:
        config.default_parameters.region = os.environ["AWS_WHITELIST_REGION"]
    
    if "AWS_WHITELIST_PORT" in os.environ:
        try:
            config.default_parameters.port = int(os.environ["AWS_WHITELIST_PORT"])
        except ValueError:
            print(f"Warning: Invalid port in AWS_WHITELIST_PORT: {os.environ['AWS_WHITELIST_PORT']}", file=sys.stderr)
    
    if "AWS_WHITELIST_PROTOCOL" in os.environ:
        config.default_parameters.protocol = os.environ["AWS_WHITELIST_PROTOCOL"]
    
    if "AWS_WHITELIST_RATE_LIMIT" in os.environ:
        try:
            config.security_settings.rate_limit_per_minute = int(os.environ["AWS_WHITELIST_RATE_LIMIT"])
        except ValueError:
            print(f"Warning: Invalid rate limit in AWS_WHITELIST_RATE_LIMIT: {os.environ['AWS_WHITELIST_RATE_LIMIT']}", file=sys.stderr)
    
    return config


def get_port_number(port_input: str, config: Config) -> int:
    """Resolve port number from numeric string or named mapping.
    
    Args:
        port_input: Port number as string or port name
        config: Configuration object with port mappings
    
    Returns:
        Port number as integer
    
    Raises:
        ValueError: If port input is invalid
    """
    # Try to parse as integer first
    try:
        port = int(port_input)
        if 1 <= port <= 65535:
            return port
        else:
            raise ValueError(f"Port number out of range: {port}")
    except ValueError:
        pass
    
    # Try to find in port mappings
    mapping = config.get_port_mapping(port_input)
    if mapping:
        return mapping.port
    
    # Invalid port input
    raise ValueError(f"Invalid port: {port_input}. Must be a number (1-65535) or a named mapping.")


# Default port mappings
DEFAULT_PORT_MAPPINGS = [
    PortMapping(name="ssh", port=22, description="SSH access"),
    PortMapping(name="http", port=80, description="HTTP traffic"),
    PortMapping(name="https", port=443, description="HTTPS traffic"),
    PortMapping(name="rdp", port=3389, description="Remote Desktop Protocol"),
    PortMapping(name="mysql", port=3306, description="MySQL database"),
    PortMapping(name="postgresql", port=5432, description="PostgreSQL database"),
    PortMapping(name="redis", port=6379, description="Redis cache"),
    PortMapping(name="mongodb", port=27017, description="MongoDB database"),
]