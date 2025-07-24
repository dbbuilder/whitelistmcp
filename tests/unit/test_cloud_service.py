"""Unit tests for cloud service module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import Future

from whitelistmcp.cloud_service import (
    CloudServiceManager,
    CloudCredentials,
    UnifiedWhitelistResult
)
from whitelistmcp.config import CloudProvider, Config
from whitelistmcp.aws.service import WhitelistResult as AWSResult
from whitelistmcp.azure.service import WhitelistResult as AzureResult
from whitelistmcp.gcp.service import WhitelistResult as GCPResult


class TestCloudCredentials:
    """Test CloudCredentials model."""
    
    def test_single_cloud_credentials(self):
        """Test credentials for single cloud provider."""
        # AWS only
        creds = CloudCredentials(cloud=CloudProvider.AWS)
        assert creds.cloud == CloudProvider.AWS
        assert creds.aws_credentials is None
        assert creds.azure_credentials is None
        assert creds.gcp_credentials is None
    
    def test_multi_cloud_credentials(self):
        """Test credentials for all cloud providers."""
        creds = CloudCredentials(cloud=CloudProvider.ALL)
        assert creds.cloud == CloudProvider.ALL
    
    def test_with_aws_credentials(self):
        """Test with AWS credentials."""
        aws_creds = Mock()
        creds = CloudCredentials(
            cloud=CloudProvider.AWS,
            aws_credentials=aws_creds
        )
        assert creds.aws_credentials == aws_creds



class TestUnifiedWhitelistResult:
    """Test UnifiedWhitelistResult model."""
    
    def test_success_result(self):
        """Test successful result."""
        result = UnifiedWhitelistResult(
            cloud=CloudProvider.AWS,
            success=True,
            message="Rule added successfully"
        )
        assert result.cloud == CloudProvider.AWS
        assert result.success is True
        assert result.message == "Rule added successfully"
        assert result.error is None
    
    def test_error_result(self):
        """Test error result."""
        result = UnifiedWhitelistResult(
            cloud=CloudProvider.AZURE,
            success=False,
            message="Failed to add rule",
            error="Access denied"
        )
        assert result.cloud == CloudProvider.AZURE
        assert result.success is False
        assert result.error == "Access denied"


class TestCloudServiceManager:
    """Test CloudServiceManager class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.default_parameters = Mock()
        config.default_parameters.port = 22
        config.default_parameters.protocol = "tcp"
        config.default_parameters.gcp_additive_only = True
        return config
    
    @pytest.fixture
    def manager(self, mock_config):
        """Create CloudServiceManager instance."""
        return CloudServiceManager(mock_config)
    
    def test_initialization(self, manager, mock_config):
        """Test manager initialization."""
        assert manager.config == mock_config
        assert manager.logger is not None
    
    @patch('whitelistmcp.cloud_service.AWSService')
    def test_add_whitelist_rule_aws_only(self, mock_aws_service, manager):
        """Test adding rule to AWS only."""
        # Setup mock
        mock_service = Mock()
        mock_aws_service.return_value = mock_service
        mock_service.add_whitelist_rule.return_value = AWSResult(
            success=True,
            message="Rule added",
            rule=Mock(cidr_ip="192.168.1.1/32", from_port=22, to_port=22)
        )
        
        # Create credentials
        aws_creds = Mock()
        creds = CloudCredentials(
            cloud=CloudProvider.AWS,
            aws_credentials=aws_creds
        )
        
        # Execute
        results = manager.add_whitelist_rule(
            credentials=creds,
            target="sg-12345",
            ip_address="192.168.1.1",
            port=22
        )
        
        # Verify
        assert len(results) == 1
        assert results[0].cloud == CloudProvider.AWS
        assert results[0].success is True
        assert results[0].message == "Rule added"
    
    @patch('whitelistmcp.cloud_service.AWSService')
    @patch('whitelistmcp.cloud_service.AzureService')
    @patch('whitelistmcp.cloud_service.GCPService')
    def test_add_whitelist_rule_all_clouds(
        self, mock_gcp_service, mock_azure_service, mock_aws_service, manager
    ):
        """Test adding rule to all clouds in parallel."""
        # Setup mocks
        mock_aws = Mock()
        mock_azure = Mock()
        mock_gcp = Mock()
        
        mock_aws_service.return_value = mock_aws
        mock_azure_service.return_value = mock_azure
        mock_gcp_service.return_value = mock_gcp
        
        # Mock responses
        mock_aws.add_whitelist_rule.return_value = AWSResult(
            success=True, message="AWS rule added", rule=Mock()
        )
        mock_azure.add_whitelist_rule.return_value = AzureResult(
            success=True, message="Azure rule added", rule=Mock()
        )
        mock_gcp.add_whitelist_rule.return_value = GCPResult(
            success=True, message="GCP rule added", rule=Mock()
        )
        
        # Create credentials
        creds = CloudCredentials(
            cloud=CloudProvider.ALL,
            aws_credentials=Mock(),
            azure_credentials=Mock(),
            gcp_credentials=Mock()
        )
        
        # Execute
        results = manager.add_whitelist_rule(
            credentials=creds,
            target="test-target",
            ip_address="192.168.1.1"
        )
        
        # Verify
        assert len(results) == 3
        cloud_results = {r.cloud: r for r in results}
        
        assert CloudProvider.AWS in cloud_results
        assert cloud_results[CloudProvider.AWS].success is True
        assert "AWS" in cloud_results[CloudProvider.AWS].message
        
        assert CloudProvider.AZURE in cloud_results
        assert cloud_results[CloudProvider.AZURE].success is True
        assert "Azure" in cloud_results[CloudProvider.AZURE].message
        
        assert CloudProvider.GCP in cloud_results
        assert cloud_results[CloudProvider.GCP].success is True
        assert "GCP" in cloud_results[CloudProvider.GCP].message
    
    @patch('whitelistmcp.cloud_service.AWSService')
    def test_add_whitelist_rule_with_error(self, mock_aws_service, manager):
        """Test handling errors when adding rules."""
        # Setup mock to raise exception
        mock_service = Mock()
        mock_aws_service.return_value = mock_service
        mock_service.add_whitelist_rule.side_effect = Exception("AWS error")
        
        # Create credentials
        creds = CloudCredentials(
            cloud=CloudProvider.AWS,
            aws_credentials=Mock()
        )
        
        # Execute
        results = manager.add_whitelist_rule(
            credentials=creds,
            target="sg-12345",
            ip_address="192.168.1.1"
        )
        
        # Verify
        assert len(results) == 1
        assert results[0].cloud == CloudProvider.AWS
        assert results[0].success is False
        assert "AWS error" in results[0].error
    
    @patch('whitelistmcp.cloud_service.AWSService')
    def test_remove_whitelist_rule_by_ip(self, mock_aws_service, manager):
        """Test removing rule by IP address."""
        # Setup mock
        mock_service = Mock()
        mock_aws_service.return_value = mock_service
        mock_service.remove_whitelist_rule.return_value = AWSResult(
            success=True,
            message="Rule removed"
        )
        
        # Create credentials
        creds = CloudCredentials(
            cloud=CloudProvider.AWS,
            aws_credentials=Mock()
        )
        
        # Execute
        results = manager.remove_whitelist_rule(
            credentials=creds,
            target="sg-12345",
            ip_address="192.168.1.1"
        )
        
        # Verify
        assert len(results) == 1
        assert results[0].success is True
        mock_service.remove_whitelist_rule.assert_called_once()
    
    @patch('whitelistmcp.cloud_service.AWSService')
    def test_list_whitelist_rules(self, mock_aws_service, manager):
        """Test listing rules."""
        # Setup mock
        mock_service = Mock()
        mock_aws_service.return_value = mock_service
        mock_rule = Mock()
        mock_rule.cidr_ip = "192.168.1.0/24"
        mock_rule.from_port = 443
        mock_rule.to_port = 443
        mock_rule.ip_protocol = "tcp"
        mock_rule.description = "Test rule"
        mock_service.list_whitelist_rules.return_value = [mock_rule]
        
        # Create credentials
        creds = CloudCredentials(
            cloud=CloudProvider.AWS,
            aws_credentials=Mock()
        )
        
        # Execute
        results = manager.list_whitelist_rules(
            credentials=creds,
            target="sg-12345"
        )
        
        # Verify
        assert len(results) == 1
        assert results[0].cloud == CloudProvider.AWS
        assert results[0].cidr_ip == "192.168.1.0/24"
        assert results[0].port == 443
    
    def test_invalid_cloud_provider(self, manager):
        """Test handling invalid cloud provider."""
        creds = CloudCredentials(cloud=CloudProvider.AWS)
        
        # Should return empty results if no credentials provided
        results = manager.add_whitelist_rule(
            credentials=creds,
            target="sg-12345",
            ip_address="192.168.1.1"
        )
        
        assert len(results) == 1
        assert results[0].success is False
        assert "credentials required" in results[0].error