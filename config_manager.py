#!/usr/bin/env python3
"""
Environment Configuration Manager
Handles loading and validation of environment variables
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    print("Warning: python-dotenv not installed. Using system environment variables only.")

logger = logging.getLogger(__name__)

@dataclass
class AWSConfig:
    """AWS configuration from environment"""
    access_key_id: str
    secret_access_key: str
    region: str
    
    @classmethod
    def from_env(cls) -> 'AWSConfig':
        """Load AWS configuration from environment variables"""
        return cls(
            access_key_id=os.getenv('AWS_ACCESS_KEY_ID', ''),
            secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', ''),
            region=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
    
    def validate(self) -> bool:
        """Validate AWS configuration"""
        if not self.access_key_id or not self.secret_access_key:
            logger.error("AWS credentials not found in environment")
            return False
        if not self.access_key_id.startswith('AKI'):
            logger.warning("AWS access key ID format may be invalid")
        return True

@dataclass
class SecurityGroupConfig:
    """Security group configuration from environment"""
    default_sg_id: str
    default_sg_name: str
    default_vpc_id: str
    
    @classmethod
    def from_env(cls) -> 'SecurityGroupConfig':
        """Load security group configuration from environment"""
        return cls(
            default_sg_id=os.getenv('DEFAULT_SECURITY_GROUP_ID', ''),
            default_sg_name=os.getenv('DEFAULT_SECURITY_GROUP_NAME', ''),
            default_vpc_id=os.getenv('DEFAULT_VPC_ID', '')
        )

@dataclass
class DescriptionFormat:
    """Description format configuration"""
    prefix: str
    separator: str
    timestamp_format: str
    
    @classmethod
    def from_env(cls) -> 'DescriptionFormat':
        """Load description format from environment"""
        return cls(
            prefix=os.getenv('DESCRIPTION_PREFIX', 'auto'),
            separator=os.getenv('DESCRIPTION_SEPARATOR', '-'),
            timestamp_format=os.getenv('DESCRIPTION_TIMESTAMP_FORMAT', '%Y%m%d-%H%M')
        )
    
    def generate(self, resource_name: str, port: str, username: str) -> str:
        """Generate a formatted description"""
        timestamp = datetime.now().strftime(self.timestamp_format)
        parts = [
            f"{resource_name} {self.separator} {port}",
            self.prefix,
            username,
            timestamp
        ]
        return self.separator.join(parts)

class ConfigManager:
    """Central configuration management"""
    
    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration manager"""
        self.env_file = env_file or '.env'
        self._load_environment()
        
        # Load configurations
        self.aws = AWSConfig.from_env()
        self.security_group = SecurityGroupConfig.from_env()
        self.description_format = DescriptionFormat.from_env()
        
        # Load additional settings
        self.validation_settings = self._load_validation_settings()
        self.common_ports = self._load_common_ports()
        self.json_template = self._load_json_template()
    
    def _load_environment(self):
        """Load environment variables from .env file"""
        if HAS_DOTENV:
            env_path = Path(self.env_file)
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded environment from {env_path}")
            else:
                logger.warning(f"Environment file {env_path} not found")
    
    def _load_validation_settings(self) -> Dict[str, Any]:
        """Load validation settings from environment"""
        return {
            'validate_ip': os.getenv('VALIDATE_IP_FORMAT', 'true').lower() == 'true',
            'validate_port': os.getenv('VALIDATE_PORT_RANGE', 'true').lower() == 'true',
            'min_port': int(os.getenv('MIN_PORT', '1')),
            'max_port': int(os.getenv('MAX_PORT', '65535')),
            'allow_private_ips': os.getenv('ALLOW_PRIVATE_IPS', 'true').lower() == 'true',
            'require_cidr': os.getenv('REQUIRE_CIDR_NOTATION', 'false').lower() == 'true'
        }
    
    def _load_common_ports(self) -> Dict[str, int]:
        """Load common port definitions from environment"""
        return {
            'ssh': int(os.getenv('COMMON_PORTS_SSH', '22')),
            'http': int(os.getenv('COMMON_PORTS_HTTP', '80')),
            'https': int(os.getenv('COMMON_PORTS_HTTPS', '443')),
            'rdp': int(os.getenv('COMMON_PORTS_RDP', '3389')),
            'custom_start': int(os.getenv('COMMON_PORTS_CUSTOM_START', '8080')),
            'custom_end': int(os.getenv('COMMON_PORTS_CUSTOM_END', '8090'))
        }
    
    def _load_json_template(self) -> Dict[str, str]:
        """Load JSON template from environment"""
        template_str = os.getenv('JSON_TEMPLATE', '{}')
        try:
            return json.loads(template_str)
        except json.JSONDecodeError:
            logger.error("Invalid JSON_TEMPLATE in environment")
            return {}
    
    def get_aws_client_config(self) -> Dict[str, str]:
        """Get AWS client configuration"""
        return {
            'aws_access_key_id': self.aws.access_key_id,
            'aws_secret_access_key': self.aws.secret_access_key,
            'region_name': self.aws.region
        }
    
    def validate_configuration(self) -> bool:
        """Validate all configuration"""
        valid = True
        
        # Validate AWS config
        if not self.aws.validate():
            logger.error("AWS configuration validation failed")
            valid = False
        
        # Validate security group config
        if not self.security_group.default_sg_id:
            logger.warning("No default security group ID configured")
        
        return valid
    
    def get_rule_config(self, override_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get rule configuration with optional overrides"""
        config = {
            'UserName': os.getenv('DEFAULT_USERNAME', 'user'),
            'UserIP': '',
            'Port': '',
            'SecurityGroupID': self.security_group.default_sg_id,
            'ResourceName': os.getenv('DEFAULT_RESOURCE_NAME', 'Resource')
        }
        
        if override_values:
            config.update(override_values)
        
        return config
    
    def format_description(self, resource_name: str, port: str, username: str) -> str:
        """Format a description using configured format"""
        return self.description_format.generate(resource_name, port, username)
    
    def is_common_port(self, port: int) -> Optional[str]:
        """Check if a port is a common service port"""
        for service, service_port in self.common_ports.items():
            if service_port == port:
                return service.upper()
        
        # Check custom range
        if self.common_ports['custom_start'] <= port <= self.common_ports['custom_end']:
            return 'CUSTOM'
        
        return None
    
    def export_config(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Export current configuration"""
        config = {
            'aws': {
                'region': self.aws.region,
                'has_credentials': bool(self.aws.access_key_id)
            },
            'security_group': {
                'default_id': self.security_group.default_sg_id,
                'default_name': self.security_group.default_sg_name,
                'default_vpc': self.security_group.default_vpc_id
            },
            'description_format': {
                'prefix': self.description_format.prefix,
                'separator': self.description_format.separator,
                'timestamp_format': self.description_format.timestamp_format,
                'example': self.format_description('ExampleApp', '8080', 'test_user')
            },
            'validation': self.validation_settings,
            'common_ports': self.common_ports,
            'json_template': self.json_template
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Configuration exported to {output_file}")
        
        return config

# Singleton instance
_config_manager: Optional[ConfigManager] = None

def get_config() -> ConfigManager:
    """Get or create configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def reload_config(env_file: Optional[str] = None) -> ConfigManager:
    """Reload configuration from environment"""
    global _config_manager
    _config_manager = ConfigManager(env_file)
    return _config_manager

# Convenience functions
def get_aws_config() -> AWSConfig:
    """Get AWS configuration"""
    return get_config().aws

def get_description_format() -> DescriptionFormat:
    """Get description format configuration"""
    return get_config().description_format

def format_description(resource_name: str, port: str, username: str) -> str:
    """Format a description using configured format"""
    return get_config().format_description(resource_name, port, username)

if __name__ == "__main__":
    # Test configuration loading
    config = get_config()
    
    print("Configuration Manager Test")
    print("=" * 50)
    
    # Validate configuration
    if config.validate_configuration():
        print("✓ Configuration valid")
    else:
        print("✗ Configuration invalid")
    
    # Show loaded configuration
    print("\nLoaded Configuration:")
    print(json.dumps(config.export_config(), indent=2))
    
    # Test description generation
    test_desc = config.format_description("TestApp", "8080", "john_doe")
    print(f"\nExample description: {test_desc}")
