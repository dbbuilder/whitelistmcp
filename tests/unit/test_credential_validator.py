"""Unit tests for credential validation utilities."""

import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError

from whitelistmcp.utils.credential_validator import (
    AWSCredentials,
    validate_credentials,
    CredentialValidationError
)


class TestAWSCredentials:
    """Test AWSCredentials model."""
    
    def test_valid_credentials(self):
        """Test creating valid credentials."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1"
        )
        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert creds.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert creds.region == "us-east-1"
        assert creds.session_token is None
    
    def test_credentials_with_session_token(self):
        """Test credentials with session token."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            session_token="AQoDYXdzEJr...<rest of token>"
        )
        assert creds.session_token == "AQoDYXdzEJr...<rest of token>"
    
    def test_invalid_access_key_format(self):
        """Test invalid access key format."""
        with pytest.raises(ValueError, match="Invalid AWS access key format"):
            AWSCredentials(
                access_key_id="invalid-key",
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1"
            )
    
    def test_empty_credentials(self):
        """Test empty credential fields."""
        with pytest.raises(ValueError, match="Invalid AWS access key format"):
            AWSCredentials(
                access_key_id="",
                secret_access_key="secret",
                region="us-east-1"
            )
        
        with pytest.raises(ValueError, match="Secret access key cannot be empty"):
            AWSCredentials(
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key="",
                region="us-east-1"
            )
    
    def test_invalid_region(self):
        """Test invalid region format."""
        with pytest.raises(ValueError, match="Invalid AWS region format"):
            AWSCredentials(
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key="secret",
                region="invalid region"
            )
    
    def test_model_dump(self):
        """Test model dump excludes sensitive data."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="us-east-1"
        )
        dump = creds.model_dump(exclude_none=True)
        assert "access_key_id" in dump
        assert "secret_access_key" in dump
        assert "region" in dump
        assert "session_token" not in dump  # None values excluded


class TestValidateCredentials:
    """Test validate_credentials function."""
    
    @patch('boto3.client')
    def test_valid_credentials_without_session(self, mock_boto_client):
        """Test validating credentials without session token."""
        # Setup mock
        mock_sts = MagicMock()
        mock_boto_client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/testuser'
        }
        
        # Test
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="us-east-1"
        )
        result = validate_credentials(creds)
        
        # Verify
        assert result["valid"] is True
        assert result["account_id"] == "123456789012"
        assert result["user_arn"] == "arn:aws:iam::123456789012:user/testuser"
        assert "error" not in result
        
        # Check boto3 was called correctly
        mock_boto_client.assert_called_once_with(
            'sts',
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="secret",
            aws_session_token=None,
            region_name="us-east-1"
        )
    
    @patch('boto3.client')
    def test_valid_credentials_with_session(self, mock_boto_client):
        """Test validating credentials with session token."""
        # Setup mock
        mock_sts = MagicMock()
        mock_boto_client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            'UserId': 'AROACKCEVSQ6C2EXAMPLE:session-name',
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/role-name/session-name'
        }
        
        # Test
        creds = AWSCredentials(
            access_key_id="ASIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="us-west-2",
            session_token="session-token"
        )
        result = validate_credentials(creds)
        
        # Verify
        assert result["valid"] is True
        assert result["account_id"] == "123456789012"
        assert "assumed-role" in result["user_arn"]
        
        # Check boto3 was called with session token
        mock_boto_client.assert_called_once_with(
            'sts',
            aws_access_key_id="ASIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="secret",
            aws_session_token="session-token",
            region_name="us-west-2"
        )
    
    @patch('boto3.client')
    def test_invalid_credentials(self, mock_boto_client):
        """Test invalid credentials."""
        # Setup mock
        mock_sts = MagicMock()
        mock_boto_client.return_value = mock_sts
        mock_sts.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'InvalidClientTokenId', 'Message': 'The security token included in the request is invalid.'}},
            'GetCallerIdentity'
        )
        
        # Test
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="invalid",
            region="us-east-1"
        )
        result = validate_credentials(creds)
        
        # Verify
        assert result["valid"] is False
        assert "error" in result
        assert "InvalidClientTokenId" in result["error"]
    
    @patch('boto3.client')
    def test_no_credentials_error(self, mock_boto_client):
        """Test handling NoCredentialsError."""
        # Setup mock
        mock_sts = MagicMock()
        mock_boto_client.return_value = mock_sts
        mock_sts.get_caller_identity.side_effect = NoCredentialsError()
        
        # Test
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="us-east-1"
        )
        result = validate_credentials(creds)
        
        # Verify
        assert result["valid"] is False
        assert "error" in result
        assert "Unable to locate credentials" in result["error"]
    
    @patch('boto3.client')
    def test_network_error(self, mock_boto_client):
        """Test handling network errors."""
        # Setup mock
        mock_sts = MagicMock()
        mock_boto_client.return_value = mock_sts
        mock_sts.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'RequestTimeout', 'Message': 'Request has timed out'}},
            'GetCallerIdentity'
        )
        
        # Test
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="us-east-1"
        )
        result = validate_credentials(creds)
        
        # Verify
        assert result["valid"] is False
        assert "error" in result
        assert "RequestTimeout" in result["error"]
    
    @patch('boto3.client')
    def test_unexpected_error(self, mock_boto_client):
        """Test handling unexpected errors."""
        # Setup mock
        mock_boto_client.side_effect = Exception("Unexpected error")
        
        # Test
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="us-east-1"
        )
        result = validate_credentials(creds)
        
        # Verify
        assert result["valid"] is False
        assert "error" in result
        assert "Unexpected error" in result["error"]


class TestCredentialValidationError:
    """Test CredentialValidationError exception."""
    
    def test_error_creation(self):
        """Test error creation and message."""
        error = CredentialValidationError("Invalid credentials")
        assert str(error) == "Invalid credentials"
        assert isinstance(error, Exception)
    
    def test_error_with_details(self):
        """Test error with additional details."""
        error = CredentialValidationError("Invalid credentials: InvalidToken")
        assert "Invalid credentials" in str(error)
        assert "InvalidToken" in str(error)