#!/usr/bin/env python3
"""
Test Environment Configuration
Verify that environment variables are properly configured
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Try to import config manager
try:
    from config_manager import get_config, reload_config
    HAS_CONFIG_MANAGER = True
except ImportError:
    print("⚠️  Warning: config_manager module not found")
    print("   Run: pip install python-dotenv")
    HAS_CONFIG_MANAGER = False

def test_environment():
    """Test environment configuration"""
    print("=" * 60)
    print("AWS Security Group Management - Environment Test")
    print("=" * 60)
    
    # Check for .env file
    env_files = ['.env', '.env.example']
    print("\n1. Checking for environment files:")
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"   ✓ {env_file} exists")
        else:
            print(f"   ✗ {env_file} not found")
    
    # Test config manager
    if HAS_CONFIG_MANAGER:
        print("\n2. Loading configuration with config_manager:")
        try:
            config = get_config()
            print("   ✓ Configuration loaded successfully")
            
            # Validate AWS credentials
            print("\n3. AWS Credentials:")
            if config.aws.access_key_id:
                print(f"   ✓ Access Key ID: {config.aws.access_key_id[:10]}...")
            else:
                print("   ✗ Access Key ID not set")
            
            if config.aws.secret_access_key:
                print("   ✓ Secret Key: ***hidden***")
            else:
                print("   ✗ Secret Access Key not set")
            
            print(f"   • Region: {config.aws.region}")
            
            # Security Group Configuration
            print("\n4. Security Group Configuration:")
            if config.security_group.default_sg_id:
                print(f"   ✓ Default SG ID: {config.security_group.default_sg_id}")
            else:
                print("   ⚠️  Default SG ID not set")
            
            if config.security_group.default_sg_name:
                print(f"   • SG Name: {config.security_group.default_sg_name}")
            
            if config.security_group.default_vpc_id:
                print(f"   • VPC ID: {config.security_group.default_vpc_id}")
            
            # Description Format
            print("\n5. Description Format:")
            print(f"   • Prefix: {config.description_format.prefix}")
            print(f"   • Separator: {config.description_format.separator}")
            print(f"   • Timestamp Format: {config.description_format.timestamp_format}")
            
            # Generate example description
            example_desc = config.format_description("TestApp", "8080", "test_user")
            print(f"   • Example: {example_desc}")
            
            # Validation Settings
            print("\n6. Validation Settings:")
            print(f"   • Validate IP: {config.validation_settings['validate_ip']}")
            print(f"   • Validate Port: {config.validation_settings['validate_port']}")
            print(f"   • Port Range: {config.validation_settings['min_port']}-{config.validation_settings['max_port']}")
            
            # Common Ports
            print("\n7. Common Ports:")
            for service, port in config.common_ports.items():
                print(f"   • {service.upper()}: {port}")
            
            # Audit Settings
            print("\n8. Audit Settings:")
            audit_enabled = os.getenv('ENABLE_AUDIT_LOG', 'true').lower() == 'true'
            print(f"   • Audit Logging: {'Enabled' if audit_enabled else 'Disabled'}")
            if audit_enabled:
                print(f"   • Log Path: {os.getenv('AUDIT_LOG_PATH', './logs/audit.log')}")
            
        except Exception as e:
            print(f"   ✗ Error loading configuration: {e}")
    
    else:
        # Fallback to direct environment variable checking
        print("\n2. Checking environment variables directly:")
        
        required_vars = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_DEFAULT_REGION'
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                if 'SECRET' in var:
                    print(f"   ✓ {var}: ***hidden***")
                else:
                    print(f"   ✓ {var}: {value[:20]}...")
            else:
                print(f"   ✗ {var}: Not set")
    
    # Test AWS connectivity
    print("\n9. Testing AWS Connectivity:")
    try:
        import boto3
        print("   ✓ boto3 installed")
        
        # Try to create client
        if HAS_CONFIG_MANAGER:
            aws_config = config.get_aws_client_config()
        else:
            aws_config = {
                'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
                'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
                'region_name': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            }
        
        if aws_config.get('aws_access_key_id') and aws_config.get('aws_secret_access_key'):
            try:
                ec2_client = boto3.client('ec2', **aws_config)
                # Try a simple operation
                response = ec2_client.describe_regions()
                print(f"   ✓ AWS connection successful - {len(response['Regions'])} regions available")
            except Exception as e:
                print(f"   ✗ AWS connection failed: {str(e)[:100]}...")
        else:
            print("   ✗ Cannot test - credentials not configured")
            
    except ImportError:
        print("   ✗ boto3 not installed - run: pip install boto3")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    
    issues = []
    if not os.path.exists('.env'):
        issues.append("Create .env file from .env.example")
    
    if not HAS_CONFIG_MANAGER:
        issues.append("Install python-dotenv: pip install python-dotenv")
    
    if HAS_CONFIG_MANAGER and config.aws.access_key_id == 'AKIAXEFUNA23JDGJOV67':
        issues.append("Update AWS credentials in .env file")
    
    if issues:
        print("⚠️  Issues to resolve:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ Environment is properly configured!")
    
    print("=" * 60)

def test_json_template():
    """Test JSON template parsing"""
    print("\n10. JSON Template Test:")
    template_str = os.getenv('JSON_TEMPLATE', '')
    if template_str:
        try:
            template = json.loads(template_str)
            print("   ✓ JSON template is valid")
            print("   Template structure:")
            for key, value in template.items():
                print(f"     • {key}: {value}")
        except json.JSONDecodeError as e:
            print(f"   ✗ Invalid JSON template: {e}")
    else:
        print("   ⚠️  JSON_TEMPLATE not set in environment")

def test_script_execution():
    """Test if scripts can be executed"""
    print("\n11. Script Execution Test:")
    
    scripts = [
        ('simple_test/test_aws_access.py', 'AWS Access Test'),
        ('config_manager.py', 'Config Manager'),
        ('mcp_server/server_env.py', 'MCP Server (Env)')
    ]
    
    for script_path, name in scripts:
        if os.path.exists(script_path):
            print(f"   ✓ {name}: {script_path} exists")
        else:
            print(f"   ✗ {name}: {script_path} not found")

if __name__ == "__main__":
    test_environment()
    test_json_template()
    test_script_execution()
    
    print("\nTo run a full test with actual AWS operations:")
    print("  python simple_test/test_aws_access.py")
    
    print("\nTo test the environment-aware script:")
    print('  python simple_test/add_sg_rule_env.py \'{"UserName":"test","UserIP":"1.1.1.1","Port":"8080","SecurityGroupID":"sg-123","ResourceName":"Test"}\'')
