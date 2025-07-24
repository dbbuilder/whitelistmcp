"""AWS credential validation utilities."""

import re
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from pydantic import BaseModel, field_validator


class CredentialValidationError(Exception):
    """Exception raised for credential validation errors."""
    pass


class AWSCredentials(BaseModel):
    """AWS credentials model."""
    
    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None
    region: str = "us-east-1"
    
    @field_validator("access_key_id")
    def validate_access_key(cls, v: str) -> str:
        """Validate AWS access key format."""
        # AWS access keys are 20 characters long and start with AKIA or ASIA
        if not re.match(r"^(AKIA|ASIA)[A-Z0-9]{16}$", v):
            raise ValueError("Invalid AWS access key format")
        return v
    
    @field_validator("secret_access_key")
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret access key is not empty."""
        if not v or not v.strip():
            raise ValueError("Secret access key cannot be empty")
        return v
    
    @field_validator("region")
    def validate_region(cls, v: str) -> str:
        """Validate AWS region format."""
        # AWS region pattern: xx-xxxx-n
        pattern = r"^[a-z]{2}-[a-z]+-\d{1,2}$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v


def validate_credentials(credentials: AWSCredentials) -> Dict[str, Any]:
    """Validate AWS credentials by attempting to get caller identity.
    
    Args:
        credentials: AWS credentials to validate
    
    Returns:
        Dictionary with validation results:
        - valid: Boolean indicating if credentials are valid
        - account_id: AWS account ID (if valid)
        - user_arn: User/role ARN (if valid)
        - error: Error message (if invalid)
    
    Raises:
        CredentialValidationError: If credentials format is invalid
    """
    if not isinstance(credentials, AWSCredentials):
        raise CredentialValidationError("Invalid credentials format")
    
    try:
        # Create STS client with provided credentials
        sts_client = boto3.client(
            'sts',
            aws_access_key_id=credentials.access_key_id,
            aws_secret_access_key=credentials.secret_access_key,
            aws_session_token=credentials.session_token,
            region_name=credentials.region
        )
        
        # Try to get caller identity
        response = sts_client.get_caller_identity()
        
        return {
            'valid': True,
            'account_id': response['Account'],
            'user_arn': response['Arn']
        }
        
    except (ClientError, BotoCoreError) as e:
        return {
            'valid': False,
            'error': str(e)
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f"Unexpected error: {str(e)}"
        }


def validate_role_arn(role_arn: Optional[str]) -> bool:
    """Validate AWS role ARN format.
    
    Args:
        role_arn: ARN to validate
    
    Returns:
        True if valid role ARN, False otherwise
    """
    if not role_arn:
        return False
    
    # Role ARN pattern
    # arn:partition:iam::account-id:role/role-name
    pattern = r"^arn:(aws|aws-cn|aws-us-gov):iam::\d{12}:role/[\w+=,.@/-]+$"
    return bool(re.match(pattern, role_arn))


def validate_session_token(token: Optional[str]) -> bool:
    """Validate AWS session token format.
    
    Args:
        token: Session token to validate
    
    Returns:
        True if valid session token format, False otherwise
    """
    if not token:
        return False
    
    # Session tokens are base64 encoded and typically 20+ characters
    # They should not contain spaces or special characters except +/=
    if len(token) < 20:
        return False
    
    # Check for valid base64-like characters
    pattern = r"^[A-Za-z0-9+/=]+$"
    return bool(re.match(pattern, token))


def extract_account_id_from_arn(arn: str) -> Optional[str]:
    """Extract AWS account ID from an ARN.
    
    Args:
        arn: AWS ARN
    
    Returns:
        Account ID if found, None otherwise
    """
    # ARN format: arn:partition:service:region:account-id:resource
    match = re.match(r"^arn:[^:]+:[^:]+:[^:]*:(\d{12}):", arn)
    if match:
        return match.group(1)
    return None


def is_temporary_credentials(access_key_id: str) -> bool:
    """Check if credentials are temporary (session) credentials.
    
    Args:
        access_key_id: AWS access key ID
    
    Returns:
        True if temporary credentials, False if permanent
    """
    # Temporary credentials start with ASIA, permanent with AKIA
    return access_key_id.startswith("ASIA")