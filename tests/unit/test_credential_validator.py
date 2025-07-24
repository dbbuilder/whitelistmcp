"""Unit tests for AWS credential validation."""

import pytest
from unittest.mock import Mock, patch
from whitelistmcp.utils.credential_validator import (
    validate_credentials,
    CredentialValidationError,
    AWSCredentials,
    validate_role_arn,
    validate_session_token
)


class TestAWSCredentials:
    """Test AWS credentials model."""
    
    def test_credentials_creation(self):
        """Test creating AWS credentials."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            session_token="AQoEXAMPLEH4aoAH0gNCAPy...",
            region="us-east-1"
        )
        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert creds.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert creds.session_token == "AQoEXAMPLEH4aoAH0gNCAPy..."
        assert creds.region == "us-east-1"
    
    def test_credentials_minimal(self):
        """Test creating credentials with minimal fields."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert creds.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert creds.session_token is None
        assert creds.region == "us-east-1"  # Default
    
    def test_credentials_validation(self):
        """Test credential field validation."""
        # Invalid access key format
        with pytest.raises(ValueError, match="Invalid AWS access key format"):
            AWSCredentials(
                access_key_id="invalid-key",
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            )
        
        # Empty secret key
        with pytest.raises(ValueError, match="Secret access key cannot be empty"):
            AWSCredentials(
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key=""
            )


class TestValidateCredentials:
    """Test credential validation functionality."""
    
    @patch('boto3.client')
    def test_validate_valid_credentials(self, mock_boto_client):
        """Test validating valid credentials."""
        # Mock STS client
        mock_sts = Mock()
        mock_boto_client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            'UserId': 'AIDAI23456789EXAMPLE',
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/TestUser'
        }
        
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        
        result = validate_credentials(creds)
        
        assert result['valid'] is True
        assert result['account_id'] == '123456789012'
        assert result['user_arn'] == 'arn:aws:iam::123456789012:user/TestUser'
        assert 'error' not in result
        
        # Verify STS was called correctly
        mock_boto_client.assert_called_once_with(
            'sts',
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token=None,
            region_name="us-east-1"
        )
    
    @patch('boto3.client')
    def test_validate_invalid_credentials(self, mock_boto_client):
        """Test validating invalid credentials."""
        # Mock STS client to raise exception
        mock_sts = Mock()
        mock_boto_client.return_value = mock_sts
        mock_sts.get_caller_identity.side_effect = Exception("Invalid credentials")
        
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="invalid-secret-key"
        )
        
        result = validate_credentials(creds)
        
        assert result['valid'] is False
        assert 'error' in result
        assert 'Invalid credentials' in result['error']
        assert 'account_id' not in result
        assert 'user_arn' not in result
    
    @patch('boto3.client')
    def test_validate_credentials_with_session_token(self, mock_boto_client):
        """Test validating credentials with session token."""
        # Mock STS client
        mock_sts = Mock()
        mock_boto_client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            'UserId': 'AROA123DEFGHIJKLMNOP:session-name',
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/TestRole/session-name'
        }
        
        creds = AWSCredentials(
            access_key_id="ASIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            session_token="AQoEXAMPLEH4aoAH0gNCAPy..."
        )
        
        result = validate_credentials(creds)
        
        assert result['valid'] is True
        assert result['account_id'] == '123456789012'
        assert result['user_arn'] == 'arn:aws:sts::123456789012:assumed-role/TestRole/session-name'
        
        # Verify session token was passed
        mock_boto_client.assert_called_once_with(
            'sts',
            aws_access_key_id="ASIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token="AQoEXAMPLEH4aoAH0gNCAPy...",
            region_name="us-east-1"
        )
    
    def test_validate_credentials_with_invalid_input(self):
        """Test credential validation with invalid input."""
        with pytest.raises(CredentialValidationError, match="Invalid credentials format"):
            validate_credentials(None)
        
        with pytest.raises(CredentialValidationError, match="Invalid credentials format"):
            validate_credentials("not-a-credential-object")


class TestValidateRoleArn:
    """Test role ARN validation."""
    
    def test_valid_role_arn(self):
        """Test validating valid role ARNs."""
        valid_arns = [
            "arn:aws:iam::123456789012:role/TestRole",
            "arn:aws:iam::123456789012:role/service-role/TestServiceRole",
            "arn:aws:iam::123456789012:role/path/to/TestRole",
            "arn:aws-us-gov:iam::123456789012:role/TestRole",
            "arn:aws-cn:iam::123456789012:role/TestRole"
        ]
        
        for arn in valid_arns:
            assert validate_role_arn(arn) is True
    
    def test_invalid_role_arn(self):
        """Test validating invalid role ARNs."""
        invalid_arns = [
            "not-an-arn",
            "arn:aws:iam::123456789012:user/TestUser",  # User, not role
            "arn:aws:s3:::bucket-name",  # S3 ARN
            "arn:aws:iam::invalid-account:role/TestRole",  # Invalid account ID
            "",
            None
        ]
        
        for arn in invalid_arns:
            assert validate_role_arn(arn) is False


class TestValidateSessionToken:
    """Test session token validation."""
    
    def test_valid_session_tokens(self):
        """Test validating valid session tokens."""
        valid_tokens = [
            "AQoEXAMPLEH4aoAH0gNCAPyLYsE3TYbQrNA5Ze6NMZmO6FqJLu",
            "FwoGZXIvYXdzEPT//////////wEaDPU",
            "IQoJb3JpZ2luX2VjEPT//////////wEaCmFw"
        ]
        
        for token in valid_tokens:
            assert validate_session_token(token) is True
    
    def test_invalid_session_tokens(self):
        """Test validating invalid session tokens."""
        invalid_tokens = [
            "",
            None,
            "too-short",
            "contains spaces in token",
            "contains@special!characters"
        ]
        
        for token in invalid_tokens:
            assert validate_session_token(token) is False