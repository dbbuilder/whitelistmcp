"""AWS service wrapper for security group management."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from pydantic import BaseModel, field_validator

from awswhitelist.utils.credential_validator import AWSCredentials
from awswhitelist.utils.ip_validator import validate_cidr_block


class AWSServiceError(Exception):
    """Exception raised for AWS service errors."""
    pass


class SecurityGroupRule(BaseModel):
    """Security group rule model."""
    
    group_id: str
    ip_protocol: str = "tcp"
    from_port: int = 22
    to_port: int = 22
    cidr_ip: str
    description: str = ""
    
    @field_validator("cidr_ip")
    def validate_cidr(cls, v):
        """Validate CIDR block format."""
        if not validate_cidr_block(v):
            raise ValueError(f"Invalid CIDR block: {v}")
        return v
    
    @field_validator("from_port", "to_port")
    def validate_ports(cls, v):
        """Validate port numbers."""
        if not 0 <= v <= 65535:
            raise ValueError(f"Port must be between 0 and 65535, got {v}")
        return v
    
    @field_validator("ip_protocol")
    def validate_protocol(cls, v):
        """Validate IP protocol."""
        valid_protocols = ["tcp", "udp", "icmp", "-1"]
        if v not in valid_protocols:
            raise ValueError(f"Invalid protocol: {v}. Must be one of {valid_protocols}")
        return v
    
    def to_aws_dict(self) -> Dict[str, Any]:
        """Convert to AWS API format."""
        return {
            "IpProtocol": self.ip_protocol,
            "FromPort": self.from_port,
            "ToPort": self.to_port,
            "IpRanges": [{
                "CidrIp": self.cidr_ip,
                "Description": self.description
            }]
        }


class WhitelistResult(BaseModel):
    """Result of a whitelist operation."""
    
    success: bool
    rule: Optional[SecurityGroupRule] = None
    message: Optional[str] = None
    error: Optional[str] = None


def create_rule_description(template: str, **kwargs) -> str:
    """Create rule description from template.
    
    Args:
        template: Description template with placeholders
        **kwargs: Values to substitute in template
    
    Returns:
        Formatted description string
    
    Available placeholders:
        - {date}: Current date in ISO format
        - {user}: User identifier
        - {reason}: Reason for access
        - Any other custom placeholders
    """
    # Add default values
    values = {
        'date': datetime.now(timezone.utc).isoformat(),
        **kwargs
    }
    
    # Simple template substitution
    description = template
    for key, value in values.items():
        placeholder = f"{{{key}}}"
        if placeholder in description:
            description = description.replace(placeholder, str(value))
    
    return description


class AWSService:
    """AWS service wrapper for security group operations."""
    
    def __init__(self, credentials: AWSCredentials):
        """Initialize AWS service with credentials.
        
        Args:
            credentials: AWS credentials for authentication
        """
        self.credentials = credentials
        self.ec2_client = self._create_ec2_client()
    
    def _create_ec2_client(self):
        """Create EC2 client with credentials."""
        return boto3.client(
            'ec2',
            aws_access_key_id=self.credentials.access_key_id,
            aws_secret_access_key=self.credentials.secret_access_key,
            aws_session_token=self.credentials.session_token,
            region_name=self.credentials.region
        )
    
    def get_security_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get security group details.
        
        Args:
            group_id: Security group ID
        
        Returns:
            Security group details or None if not found
        """
        try:
            response = self.ec2_client.describe_security_groups(
                GroupIds=[group_id]
            )
            
            if response['SecurityGroups']:
                return response['SecurityGroups'][0]
            return None
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidGroup.NotFound':
                return None
            raise AWSServiceError(f"Failed to get security group: {str(e)}")
        except Exception as e:
            raise AWSServiceError(f"Unexpected error: {str(e)}")
    
    def add_whitelist_rule(self, rule: SecurityGroupRule) -> WhitelistResult:
        """Add IP whitelist rule to security group.
        
        Args:
            rule: Security group rule to add
        
        Returns:
            WhitelistResult indicating success or failure
        """
        try:
            # Check if security group exists
            sg = self.get_security_group(rule.group_id)
            if not sg:
                return WhitelistResult(
                    success=False,
                    error=f"Security group {rule.group_id} not found"
                )
            
            # Add the rule
            response = self.ec2_client.authorize_security_group_ingress(
                GroupId=rule.group_id,
                IpPermissions=[rule.to_aws_dict()]
            )
            
            return WhitelistResult(
                success=True,
                rule=rule,
                message=f"Rule added successfully to {rule.group_id}"
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'InvalidPermission.Duplicate':
                return WhitelistResult(
                    success=False,
                    error="Rule already exists in security group"
                )
            elif error_code == 'RulesPerSecurityGroupLimitExceeded':
                return WhitelistResult(
                    success=False,
                    error="Security group rule limit exceeded"
                )
            else:
                return WhitelistResult(
                    success=False,
                    error=f"Failed to add rule: {str(e)}"
                )
                
        except Exception as e:
            return WhitelistResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    def remove_whitelist_rule(self, rule: SecurityGroupRule) -> WhitelistResult:
        """Remove IP whitelist rule from security group.
        
        Args:
            rule: Security group rule to remove
        
        Returns:
            WhitelistResult indicating success or failure
        """
        try:
            response = self.ec2_client.revoke_security_group_ingress(
                GroupId=rule.group_id,
                IpPermissions=[rule.to_aws_dict()]
            )
            
            return WhitelistResult(
                success=True,
                rule=rule,
                message=f"Rule removed successfully from {rule.group_id}"
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'InvalidPermission.NotFound':
                return WhitelistResult(
                    success=False,
                    error="Rule not found in security group"
                )
            else:
                return WhitelistResult(
                    success=False,
                    error=f"Failed to remove rule: {str(e)}"
                )
                
        except Exception as e:
            return WhitelistResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    def list_whitelist_rules(self, group_id: str) -> List[SecurityGroupRule]:
        """List all IP whitelist rules for a security group.
        
        Args:
            group_id: Security group ID
        
        Returns:
            List of SecurityGroupRule objects
        
        Raises:
            AWSServiceError: If listing fails
        """
        try:
            sg = self.get_security_group(group_id)
            if not sg:
                raise AWSServiceError(f"Security group {group_id} not found")
            
            rules = []
            
            # Parse ingress rules
            for permission in sg.get('IpPermissions', []):
                protocol = permission.get('IpProtocol', 'tcp')
                from_port = permission.get('FromPort', 0)
                to_port = permission.get('ToPort', 0)
                
                # Handle IP ranges (IPv4)
                for ip_range in permission.get('IpRanges', []):
                    rule = SecurityGroupRule(
                        group_id=group_id,
                        ip_protocol=protocol,
                        from_port=from_port,
                        to_port=to_port,
                        cidr_ip=ip_range['CidrIp'],
                        description=ip_range.get('Description', '')
                    )
                    rules.append(rule)
                
                # Handle IPv6 ranges if needed
                for ipv6_range in permission.get('Ipv6Ranges', []):
                    rule = SecurityGroupRule(
                        group_id=group_id,
                        ip_protocol=protocol,
                        from_port=from_port,
                        to_port=to_port,
                        cidr_ip=ipv6_range['CidrIpv6'],
                        description=ipv6_range.get('Description', '')
                    )
                    rules.append(rule)
            
            return rules
            
        except AWSServiceError:
            raise
        except Exception as e:
            raise AWSServiceError(f"Failed to list rules: {str(e)}")
    
    def check_rule_exists(self, rule: SecurityGroupRule) -> bool:
        """Check if a specific rule already exists in a security group.
        
        Args:
            rule: Security group rule to check
        
        Returns:
            True if rule exists, False otherwise
        """
        try:
            existing_rules = self.list_whitelist_rules(rule.group_id)
            
            for existing in existing_rules:
                if (existing.ip_protocol == rule.ip_protocol and
                    existing.from_port == rule.from_port and
                    existing.to_port == rule.to_port and
                    existing.cidr_ip == rule.cidr_ip):
                    return True
            
            return False
            
        except Exception:
            return False