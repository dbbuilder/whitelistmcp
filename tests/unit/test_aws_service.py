"""Unit tests for AWS service wrapper."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from awswhitelist.aws.service import (
    AWSService,
    SecurityGroupRule,
    WhitelistResult,
    AWSServiceError,
    create_rule_description
)
from awswhitelist.utils.credential_validator import AWSCredentials


class TestSecurityGroupRule:
    """Test SecurityGroupRule model."""
    
    def test_security_group_rule_creation(self):
        """Test creating a security group rule."""
        rule = SecurityGroupRule(
            group_id="sg-123456",
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_ip="192.168.1.0/24",
            description="Test rule"
        )
        assert rule.group_id == "sg-123456"
        assert rule.ip_protocol == "tcp"
        assert rule.from_port == 443
        assert rule.to_port == 443
        assert rule.cidr_ip == "192.168.1.0/24"
        assert rule.description == "Test rule"
    
    def test_security_group_rule_defaults(self):
        """Test security group rule with defaults."""
        rule = SecurityGroupRule(
            group_id="sg-123456",
            cidr_ip="192.168.1.1/32"
        )
        assert rule.ip_protocol == "tcp"
        assert rule.from_port == 22
        assert rule.to_port == 22
        assert rule.description == ""
    
    def test_security_group_rule_to_dict(self):
        """Test converting rule to AWS API format."""
        rule = SecurityGroupRule(
            group_id="sg-123456",
            ip_protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_ip="10.0.0.0/24",
            description="HTTP access"
        )
        
        api_dict = rule.to_aws_dict()
        assert api_dict["IpProtocol"] == "tcp"
        assert api_dict["FromPort"] == 80
        assert api_dict["ToPort"] == 80
        assert len(api_dict["IpRanges"]) == 1
        assert api_dict["IpRanges"][0]["CidrIp"] == "10.0.0.0/24"
        assert api_dict["IpRanges"][0]["Description"] == "HTTP access"


class TestWhitelistResult:
    """Test WhitelistResult model."""
    
    def test_whitelist_result_success(self):
        """Test successful whitelist result."""
        result = WhitelistResult(
            success=True,
            rule=SecurityGroupRule(
                group_id="sg-123456",
                cidr_ip="192.168.1.1/32"
            ),
            message="Rule added successfully"
        )
        assert result.success is True
        assert result.rule.group_id == "sg-123456"
        assert result.message == "Rule added successfully"
        assert result.error is None
    
    def test_whitelist_result_failure(self):
        """Test failed whitelist result."""
        result = WhitelistResult(
            success=False,
            error="Invalid security group"
        )
        assert result.success is False
        assert result.rule is None
        assert result.message is None
        assert result.error == "Invalid security group"


class TestCreateRuleDescription:
    """Test rule description creation."""
    
    def test_create_rule_description(self):
        """Test creating rule description from template."""
        template = "Added by {user} on {date} for {reason}"
        description = create_rule_description(
            template,
            user="testuser",
            reason="API access"
        )
        
        assert "testuser" in description
        assert "API access" in description
        # Should contain date in ISO format
        assert description.count("-") >= 2  # YYYY-MM-DD format
    
    def test_create_rule_description_minimal(self):
        """Test creating rule description with minimal template."""
        template = "MCP Rule"
        description = create_rule_description(template)
        assert description == "MCP Rule"


class TestAWSService:
    """Test AWS service wrapper."""
    
    @pytest.fixture
    def credentials(self):
        """Create test credentials."""
        return AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1"
        )
    
    @pytest.fixture
    def aws_service(self, credentials):
        """Create AWS service instance."""
        return AWSService(credentials)
    
    @patch('boto3.client')
    def test_aws_service_initialization(self, mock_boto_client, credentials):
        """Test AWS service initialization."""
        mock_ec2 = Mock()
        mock_boto_client.return_value = mock_ec2
        
        service = AWSService(credentials)
        
        assert service.credentials == credentials
        assert service.ec2_client == mock_ec2
        
        mock_boto_client.assert_called_once_with(
            'ec2',
            aws_access_key_id=credentials.access_key_id,
            aws_secret_access_key=credentials.secret_access_key,
            aws_session_token=None,
            region_name=credentials.region
        )
    
    @patch('boto3.client')
    def test_get_security_group(self, mock_boto_client, credentials):
        """Test getting security group details."""
        mock_ec2 = Mock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock response
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-123456',
                'GroupName': 'test-sg',
                'Description': 'Test security group',
                'VpcId': 'vpc-123456',
                'IpPermissions': []
            }]
        }
        
        service = AWSService(credentials)
        sg = service.get_security_group('sg-123456')
        
        assert sg is not None
        assert sg['GroupId'] == 'sg-123456'
        assert sg['GroupName'] == 'test-sg'
        
        mock_ec2.describe_security_groups.assert_called_once_with(
            GroupIds=['sg-123456']
        )
    
    @patch('boto3.client')
    def test_get_security_group_not_found(self, mock_boto_client, credentials):
        """Test getting non-existent security group."""
        mock_ec2 = Mock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock not found error
        mock_ec2.describe_security_groups.side_effect = ClientError(
            {'Error': {'Code': 'InvalidGroup.NotFound'}},
            'DescribeSecurityGroups'
        )
        
        service = AWSService(credentials)
        sg = service.get_security_group('sg-invalid')
        
        assert sg is None
    
    @patch('boto3.client')
    def test_add_whitelist_rule_success(self, mock_boto_client, credentials):
        """Test successfully adding a whitelist rule."""
        mock_ec2 = Mock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock successful authorization
        mock_ec2.authorize_security_group_ingress.return_value = {
            'Return': True,
            'SecurityGroupRules': [{
                'SecurityGroupRuleId': 'sgr-123456'
            }]
        }
        
        # Mock security group exists
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-123456',
                'GroupName': 'test-sg'
            }]
        }
        
        service = AWSService(credentials)
        rule = SecurityGroupRule(
            group_id="sg-123456",
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_ip="192.168.1.0/24",
            description="Test rule"
        )
        
        result = service.add_whitelist_rule(rule)
        
        assert result.success is True
        assert result.rule == rule
        assert "successfully" in result.message
        
        # Verify API call
        mock_ec2.authorize_security_group_ingress.assert_called_once()
        call_args = mock_ec2.authorize_security_group_ingress.call_args[1]
        assert call_args['GroupId'] == 'sg-123456'
        assert len(call_args['IpPermissions']) == 1
    
    @patch('boto3.client')
    def test_add_whitelist_rule_already_exists(self, mock_boto_client, credentials):
        """Test adding a rule that already exists."""
        mock_ec2 = Mock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock duplicate rule error
        mock_ec2.authorize_security_group_ingress.side_effect = ClientError(
            {'Error': {'Code': 'InvalidPermission.Duplicate'}},
            'AuthorizeSecurityGroupIngress'
        )
        
        # Mock security group exists
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-123456',
                'GroupName': 'test-sg'
            }]
        }
        
        service = AWSService(credentials)
        rule = SecurityGroupRule(
            group_id="sg-123456",
            cidr_ip="192.168.1.1/32"
        )
        
        result = service.add_whitelist_rule(rule)
        
        assert result.success is False
        assert "already exists" in result.error
    
    @patch('boto3.client')
    def test_remove_whitelist_rule_success(self, mock_boto_client, credentials):
        """Test successfully removing a whitelist rule."""
        mock_ec2 = Mock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock successful revocation
        mock_ec2.revoke_security_group_ingress.return_value = {
            'Return': True
        }
        
        service = AWSService(credentials)
        rule = SecurityGroupRule(
            group_id="sg-123456",
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_ip="192.168.1.0/24"
        )
        
        result = service.remove_whitelist_rule(rule)
        
        assert result.success is True
        assert "removed" in result.message
        
        # Verify API call
        mock_ec2.revoke_security_group_ingress.assert_called_once()
        call_args = mock_ec2.revoke_security_group_ingress.call_args[1]
        assert call_args['GroupId'] == 'sg-123456'
    
    @patch('boto3.client')
    def test_list_whitelist_rules(self, mock_boto_client, credentials):
        """Test listing whitelist rules for a security group."""
        mock_ec2 = Mock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock security group with rules
        mock_ec2.describe_security_groups.return_value = {
            'SecurityGroups': [{
                'GroupId': 'sg-123456',
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [
                            {
                                'CidrIp': '10.0.0.0/24',
                                'Description': 'HTTP access'
                            }
                        ]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'IpRanges': [
                            {
                                'CidrIp': '192.168.1.0/24',
                                'Description': 'HTTPS access'
                            },
                            {
                                'CidrIp': '172.16.0.0/16',
                                'Description': 'Internal HTTPS'
                            }
                        ]
                    }
                ]
            }]
        }
        
        service = AWSService(credentials)
        rules = service.list_whitelist_rules('sg-123456')
        
        assert len(rules) == 3
        
        # Check first rule
        assert rules[0].ip_protocol == 'tcp'
        assert rules[0].from_port == 80
        assert rules[0].cidr_ip == '10.0.0.0/24'
        
        # Check second rule
        assert rules[1].from_port == 443
        assert rules[1].cidr_ip == '192.168.1.0/24'
        
        # Check third rule
        assert rules[2].from_port == 443
        assert rules[2].cidr_ip == '172.16.0.0/16'