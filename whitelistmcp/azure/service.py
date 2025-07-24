"""Azure Network Security Group service for whitelisting operations."""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import (
    NetworkSecurityGroup,
    SecurityRule,
    SecurityRuleProtocol,
    SecurityRuleAccess,
    SecurityRuleDirection
)
from azure.core.exceptions import AzureError, ResourceNotFoundError

from whitelistmcp.utils.ip_validator import normalize_ip_input, IPValidationError
from whitelistmcp.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AzureCredentials:
    """Azure credential information."""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    subscription_id: str = ""
    use_default_credential: bool = False


@dataclass
class NSGRule:
    """Azure Network Security Group rule representation."""
    nsg_name: str
    resource_group: str
    name: str
    priority: int
    direction: str = "Inbound"
    access: str = "Allow"
    protocol: str = "Tcp"
    source_address_prefix: str = "*"
    source_port_range: str = "*"
    destination_address_prefix: str = "*"
    destination_port_range: str = "*"
    description: Optional[str] = None


@dataclass
class WhitelistResult:
    """Result of a whitelist operation."""
    success: bool
    message: str
    rule: Optional[NSGRule] = None
    error: Optional[str] = None


def create_rule_description(
    template: str,
    user: str = "MCP",
    reason: str = "Access",
    service_name: Optional[str] = None
) -> str:
    """Create a rule description from template."""
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M")
    description = template.format(
        user=user,
        reason=reason,
        timestamp=timestamp,
        service=service_name or "custom"
    )
    return description[:140]  # Azure limit is 140 characters


class AzureService:
    """Azure Network Security Group service."""
    
    def __init__(self, credentials: AzureCredentials):
        """Initialize Azure service with credentials."""
        self.credentials = credentials
        self._client = None
        
    @property
    def client(self) -> NetworkManagementClient:
        """Get or create Azure Network Management client."""
        if self._client is None:
            if self.credentials.use_default_credential:
                credential = DefaultAzureCredential()
            else:
                if not all([
                    self.credentials.client_id,
                    self.credentials.client_secret,
                    self.credentials.tenant_id
                ]):
                    raise ValueError("Azure credentials incomplete")
                    
                credential = ClientSecretCredential(
                    tenant_id=self.credentials.tenant_id,
                    client_id=self.credentials.client_id,
                    client_secret=self.credentials.client_secret
                )
            
            self._client = NetworkManagementClient(
                credential=credential,
                subscription_id=self.credentials.subscription_id
            )
            
        return self._client
    
    def _get_next_priority(self, nsg: NetworkSecurityGroup, direction: str = "Inbound") -> int:
        """Get the next available priority for a new rule."""
        if not nsg.security_rules:
            return 100
            
        priorities = [
            rule.priority for rule in nsg.security_rules
            if rule.direction == direction and rule.priority < 4000
        ]
        
        if not priorities:
            return 100
            
        # Find gap in priorities
        priorities.sort()
        for i in range(100, 4000, 10):
            if i not in priorities:
                return i
                
        raise ValueError("No available priority slots in NSG")
    
    def add_whitelist_rule(self, rule: NSGRule) -> WhitelistResult:
        """Add a whitelist rule to an NSG."""
        try:
            # Get the NSG
            nsg = self.client.network_security_groups.get(
                resource_group_name=rule.resource_group,
                network_security_group_name=rule.nsg_name
            )
            
            # Auto-assign priority if not set
            if rule.priority == 0:
                rule.priority = self._get_next_priority(nsg, rule.direction)
            
            # Create the security rule
            security_rule = SecurityRule(
                name=rule.name or f"rule-{rule.source_address_prefix.replace('/', '-')}-{rule.destination_port_range}",
                priority=rule.priority,
                direction=rule.direction,
                access=rule.access,
                protocol=rule.protocol,
                source_address_prefix=rule.source_address_prefix,
                source_port_range=rule.source_port_range,
                destination_address_prefix=rule.destination_address_prefix,
                destination_port_range=rule.destination_port_range,
                description=rule.description
            )
            
            # Create or update the rule
            operation = self.client.security_rules.begin_create_or_update(
                resource_group_name=rule.resource_group,
                network_security_group_name=rule.nsg_name,
                security_rule_name=security_rule.name,
                security_rule_parameters=security_rule
            )
            
            result = operation.result()
            
            logger.info(
                f"Added rule to NSG {rule.nsg_name}: "
                f"{rule.source_address_prefix} -> {rule.destination_port_range}"
            )
            
            return WhitelistResult(
                success=True,
                message=f"Successfully added rule to NSG {rule.nsg_name}",
                rule=rule
            )
            
        except ResourceNotFoundError:
            return WhitelistResult(
                success=False,
                message=f"NSG {rule.nsg_name} not found in resource group {rule.resource_group}",
                error="NSG_NOT_FOUND"
            )
        except Exception as e:
            logger.error(f"Failed to add rule: {str(e)}")
            return WhitelistResult(
                success=False,
                message="Failed to add rule",
                error=str(e)
            )
    
    def remove_whitelist_rule(
        self,
        nsg_name: str,
        resource_group: str,
        ip_address: Optional[str] = None,
        port: Optional[Union[int, str]] = None,
        service_name: Optional[str] = None,
        protocol: str = "Tcp"
    ) -> WhitelistResult:
        """Remove whitelist rules based on flexible criteria."""
        try:
            # Get the NSG
            nsg = self.client.network_security_groups.get(
                resource_group_name=resource_group,
                network_security_group_name=nsg_name
            )
            
            if not nsg.security_rules:
                return WhitelistResult(
                    success=False,
                    message="No rules found in NSG",
                    error="NO_RULES"
                )
            
            # Normalize IP if provided
            if ip_address:
                try:
                    ip_address = normalize_ip_input(ip_address)
                except IPValidationError:
                    return WhitelistResult(
                        success=False,
                        message=f"Invalid IP address: {ip_address}",
                        error="INVALID_IP"
                    )
            
            # Convert port to string for comparison
            port_str = str(port) if port else None
            
            # Find rules to remove
            rules_to_remove = []
            for rule in nsg.security_rules:
                match = True
                
                # Check IP match
                if ip_address and rule.source_address_prefix != ip_address:
                    match = False
                
                # Check port match
                if port_str and rule.destination_port_range != port_str:
                    match = False
                
                # Check service name match (in description)
                if service_name and (not rule.description or service_name not in rule.description):
                    match = False
                
                # Check protocol match
                if protocol and rule.protocol.lower() != protocol.lower():
                    match = False
                
                if match:
                    rules_to_remove.append(rule)
            
            if not rules_to_remove:
                criteria = []
                if ip_address:
                    criteria.append(f"IP={ip_address}")
                if port_str:
                    criteria.append(f"port={port_str}")
                if service_name:
                    criteria.append(f"service={service_name}")
                
                return WhitelistResult(
                    success=False,
                    message=f"No matching rules found for {', '.join(criteria)}",
                    error="NO_MATCHING_RULES"
                )
            
            # Remove the rules
            removed_count = 0
            for rule in rules_to_remove:
                try:
                    self.client.security_rules.begin_delete(
                        resource_group_name=resource_group,
                        network_security_group_name=nsg_name,
                        security_rule_name=rule.name
                    ).result()
                    removed_count += 1
                    logger.info(f"Removed rule {rule.name} from NSG {nsg_name}")
                except Exception as e:
                    logger.error(f"Failed to remove rule {rule.name}: {str(e)}")
            
            return WhitelistResult(
                success=True,
                message=f"Successfully removed {removed_count} rule(s) from NSG {nsg_name}"
            )
            
        except Exception as e:
            logger.error(f"Failed to remove rules: {str(e)}")
            return WhitelistResult(
                success=False,
                message="Failed to remove rules",
                error=str(e)
            )
    
    def list_whitelist_rules(self, nsg_name: str, resource_group: str) -> List[NSGRule]:
        """List all whitelist rules in an NSG."""
        try:
            nsg = self.client.network_security_groups.get(
                resource_group_name=resource_group,
                network_security_group_name=nsg_name
            )
            
            rules = []
            if nsg.security_rules:
                for rule in nsg.security_rules:
                    if rule.direction == "Inbound" and rule.access == "Allow":
                        rules.append(NSGRule(
                            nsg_name=nsg_name,
                            resource_group=resource_group,
                            name=rule.name,
                            priority=rule.priority,
                            direction=rule.direction,
                            access=rule.access,
                            protocol=rule.protocol,
                            source_address_prefix=rule.source_address_prefix,
                            source_port_range=rule.source_port_range,
                            destination_address_prefix=rule.destination_address_prefix,
                            destination_port_range=rule.destination_port_range,
                            description=rule.description
                        ))
            
            return rules
            
        except Exception as e:
            logger.error(f"Failed to list rules: {str(e)}")
            return []
    
    def check_whitelist_rule(
        self,
        nsg_name: str,
        resource_group: str,
        ip_address: str,
        port: Optional[Union[int, str]] = None,
        protocol: str = "Tcp"
    ) -> bool:
        """Check if an IP/port combination is whitelisted."""
        try:
            ip_address = normalize_ip_input(ip_address)
            rules = self.list_whitelist_rules(nsg_name, resource_group)
            
            port_str = str(port) if port else None
            
            for rule in rules:
                # Check IP match
                if rule.source_address_prefix != ip_address:
                    continue
                
                # Check port match if specified
                if port_str and rule.destination_port_range != port_str:
                    continue
                
                # Check protocol match
                if rule.protocol.lower() != protocol.lower():
                    continue
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check rule: {str(e)}")
            return False