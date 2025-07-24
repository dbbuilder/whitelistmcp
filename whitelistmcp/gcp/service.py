"""Google Cloud Platform VPC Firewall service for whitelisting operations."""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime

from google.cloud import compute_v1
from google.cloud.compute_v1.types import Firewall, Allowed
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPIError, NotFound
import google.auth

from whitelistmcp.utils.ip_validator import normalize_ip_input, IPValidationError
from whitelistmcp.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GCPCredentials:
    """GCP credential information."""
    project_id: str
    credentials_path: Optional[str] = None
    credentials_json: Optional[Dict[str, Any]] = None
    use_default_credential: bool = False


@dataclass
class FirewallRule:
    """GCP VPC Firewall rule representation."""
    name: str
    project_id: str
    network: str = "default"
    direction: str = "INGRESS"
    priority: int = 1000
    source_ranges: List[str] = None
    destination_ranges: List[str] = None
    allowed: List[Dict[str, Any]] = None
    denied: List[Dict[str, Any]] = None
    target_tags: List[str] = None
    target_service_accounts: List[str] = None
    description: Optional[str] = None
    disabled: bool = False


@dataclass
class WhitelistResult:
    """Result of a whitelist operation."""
    success: bool
    message: str
    rule: Optional[FirewallRule] = None
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
    return description[:256]  # GCP limit is 256 characters


class GCPService:
    """Google Cloud Platform VPC Firewall service."""
    
    def __init__(self, credentials: GCPCredentials, additive_only: bool = True):
        """Initialize GCP service with credentials."""
        self.credentials = credentials
        self.additive_only = additive_only
        self._client = None
        self._credentials = None
        
    @property
    def client(self) -> compute_v1.FirewallsClient:
        """Get or create GCP Compute client."""
        if self._client is None:
            if self.credentials.use_default_credential:
                # Use Application Default Credentials
                credentials, project = google.auth.default()
                self._credentials = credentials
            elif self.credentials.credentials_path:
                # Use service account from file
                self._credentials = service_account.Credentials.from_service_account_file(
                    self.credentials.credentials_path,
                    scopes=['https://www.googleapis.com/auth/compute']
                )
            elif self.credentials.credentials_json:
                # Use service account from JSON dict
                self._credentials = service_account.Credentials.from_service_account_info(
                    self.credentials.credentials_json,
                    scopes=['https://www.googleapis.com/auth/compute']
                )
            else:
                raise ValueError("No GCP credentials provided")
            
            self._client = compute_v1.FirewallsClient(credentials=self._credentials)
            
        return self._client
    
    def _generate_rule_name(self, ip_address: str, port: Union[int, str], service_name: Optional[str] = None) -> str:
        """Generate a unique rule name."""
        # Clean IP for use in name
        clean_ip = ip_address.replace('.', '-').replace('/', '-')
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        if service_name:
            return f"allow-{service_name}-{clean_ip}-{timestamp}"
        else:
            return f"allow-port{port}-{clean_ip}-{timestamp}"
    
    
    def add_whitelist_rule(self, rule: FirewallRule) -> WhitelistResult:
        """Add a whitelist rule to GCP VPC Firewall (always creates new rule, never modifies existing)."""
        try:
            # In additive mode, we always create a new rule without touching existing ones
            # This ensures we never accidentally break existing configurations
            
            # Create new firewall rule
            firewall_rule = Firewall()
            firewall_rule.name = rule.name
            firewall_rule.network = f"projects/{self.credentials.project_id}/global/networks/{rule.network}"
            firewall_rule.direction = rule.direction
            firewall_rule.priority = rule.priority
            firewall_rule.source_ranges = rule.source_ranges or []
            firewall_rule.description = rule.description
            firewall_rule.disabled = rule.disabled
            
            # Set allowed rules
            if rule.allowed:
                firewall_rule.allowed = []
                for allowed in rule.allowed:
                    allowed_rule = Allowed()
                    allowed_rule.I_p_protocol = allowed.get('IPProtocol', 'tcp')
                    if 'ports' in allowed:
                        allowed_rule.ports = allowed['ports']
                    firewall_rule.allowed.append(allowed_rule)
            
            # Set target tags if provided
            if rule.target_tags:
                firewall_rule.target_tags = rule.target_tags
            
            # Create the firewall rule
            operation = self.client.insert(
                project=self.credentials.project_id,
                firewall_resource=firewall_rule
            )
            
            self._wait_for_operation(operation)
            
            logger.info(f"Created firewall rule {rule.name}")
            
            return WhitelistResult(
                success=True,
                message=f"Successfully created firewall rule {rule.name}",
                rule=rule
            )
            
        except NotFound:
            return WhitelistResult(
                success=False,
                message=f"Network {rule.network} not found",
                error="NETWORK_NOT_FOUND"
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
        project_id: str,
        ip_address: Optional[str] = None,
        port: Optional[Union[int, str]] = None,
        service_name: Optional[str] = None,
        protocol: str = "tcp"
    ) -> WhitelistResult:
        """Remove whitelist rules based on flexible criteria."""
        if self.additive_only:
            return WhitelistResult(
                success=False,
                message="Removal operations are disabled in additive-only mode",
                error="ADDITIVE_ONLY_MODE"
            )
        
        try:
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
            
            # List all firewall rules
            rules = self.client.list(project=project_id)
            
            # Find rules to remove or update
            rules_to_remove = []
            rules_to_update = []
            
            for rule in rules:
                if rule.direction != "INGRESS" or not rule.allowed:
                    continue
                
                # Check if rule matches criteria
                ip_match = False
                port_match = False
                service_match = False
                
                # Check IP match
                if ip_address and rule.source_ranges:
                    ip_match = ip_address in rule.source_ranges
                
                # Check port match
                if port and rule.allowed:
                    for allowed in rule.allowed:
                        if str(port) in (allowed.ports or []):
                            port_match = True
                            break
                
                # Check service name match (in description or name)
                if service_name:
                    service_match = (
                        (rule.description and service_name in rule.description) or
                        (service_name in rule.name)
                    )
                
                # Determine action based on matches
                if ip_address and not port and not service_name and ip_match:
                    # Remove IP from all rules
                    if len(rule.source_ranges) > 1:
                        rules_to_update.append((rule, ip_address))
                    else:
                        rules_to_remove.append(rule)
                elif port and not ip_address and not service_name and port_match:
                    # Remove entire rules with this port
                    rules_to_remove.append(rule)
                elif service_name and not ip_address and not port and service_match:
                    # Remove entire rules with this service
                    rules_to_remove.append(rule)
                elif all([ip_match, port_match]) or all([ip_match, service_match]):
                    # Remove specific combination
                    if len(rule.source_ranges) > 1:
                        rules_to_update.append((rule, ip_address))
                    else:
                        rules_to_remove.append(rule)
            
            removed_count = 0
            updated_count = 0
            
            # Remove entire rules
            for rule in rules_to_remove:
                try:
                    operation = self.client.delete(
                        project=project_id,
                        firewall=rule.name
                    )
                    self._wait_for_operation(operation)
                    removed_count += 1
                    logger.info(f"Removed firewall rule {rule.name}")
                except Exception as e:
                    logger.error(f"Failed to remove rule {rule.name}: {str(e)}")
            
            # Update rules (remove specific IPs)
            for rule, ip_to_remove in rules_to_update:
                try:
                    rule.source_ranges.remove(ip_to_remove)
                    operation = self.client.update(
                        project=project_id,
                        firewall=rule.name,
                        firewall_resource=rule
                    )
                    self._wait_for_operation(operation)
                    updated_count += 1
                    logger.info(f"Updated firewall rule {rule.name} (removed {ip_to_remove})")
                except Exception as e:
                    logger.error(f"Failed to update rule {rule.name}: {str(e)}")
            
            total_affected = removed_count + updated_count
            if total_affected == 0:
                return WhitelistResult(
                    success=False,
                    message="No matching rules found",
                    error="NO_MATCHING_RULES"
                )
            
            return WhitelistResult(
                success=True,
                message=f"Successfully removed {removed_count} rule(s) and updated {updated_count} rule(s)"
            )
            
        except Exception as e:
            logger.error(f"Failed to remove rules: {str(e)}")
            return WhitelistResult(
                success=False,
                message="Failed to remove rules",
                error=str(e)
            )
    
    def list_whitelist_rules(self, project_id: str, network: str = "default") -> List[FirewallRule]:
        """List all ingress allow firewall rules."""
        try:
            rules = self.client.list(project=project_id)
            
            firewall_rules = []
            for rule in rules:
                if rule.direction == "INGRESS" and rule.allowed:
                    # Convert to our FirewallRule format
                    allowed_list = []
                    for allowed in rule.allowed:
                        allowed_dict = {
                            'IPProtocol': allowed.I_p_protocol,
                            'ports': list(allowed.ports) if allowed.ports else []
                        }
                        allowed_list.append(allowed_dict)
                    
                    firewall_rule = FirewallRule(
                        name=rule.name,
                        project_id=project_id,
                        network=rule.network.split('/')[-1],
                        direction=rule.direction,
                        priority=rule.priority,
                        source_ranges=list(rule.source_ranges) if rule.source_ranges else [],
                        allowed=allowed_list,
                        target_tags=list(rule.target_tags) if rule.target_tags else [],
                        description=rule.description,
                        disabled=rule.disabled
                    )
                    
                    firewall_rules.append(firewall_rule)
            
            return firewall_rules
            
        except Exception as e:
            logger.error(f"Failed to list rules: {str(e)}")
            return []
    
    def check_whitelist_rule(
        self,
        project_id: str,
        ip_address: str,
        port: Optional[Union[int, str]] = None,
        protocol: str = "tcp"
    ) -> bool:
        """Check if an IP/port combination is whitelisted."""
        try:
            ip_address = normalize_ip_input(ip_address)
            rules = self.list_whitelist_rules(project_id)
            
            for rule in rules:
                if rule.disabled:
                    continue
                
                # Check if IP is in source ranges
                if ip_address not in (rule.source_ranges or []):
                    continue
                
                # Check if port/protocol is allowed
                if port:
                    port_str = str(port)
                    for allowed in (rule.allowed or []):
                        if allowed.get('IPProtocol', '').lower() == protocol.lower():
                            if not allowed.get('ports') or port_str in allowed.get('ports', []):
                                return True
                else:
                    # No specific port, just check if any rule allows this IP
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check rule: {str(e)}")
            return False
    
    def _rules_match_ports(self, allowed1: List[Any], allowed2: List[Dict[str, Any]]) -> bool:
        """Check if two allowed rule sets have matching ports/protocols."""
        # Convert to comparable format
        set1 = set()
        for rule in allowed1:
            proto = rule.I_p_protocol
            if rule.ports:
                for port in rule.ports:
                    set1.add(f"{proto}:{port}")
            else:
                set1.add(f"{proto}:all")
        
        set2 = set()
        for rule in allowed2:
            proto = rule.get('IPProtocol', 'tcp')
            if rule.get('ports'):
                for port in rule['ports']:
                    set2.add(f"{proto}:{port}")
            else:
                set2.add(f"{proto}:all")
        
        return bool(set1.intersection(set2))
    
    def _wait_for_operation(self, operation):
        """Wait for a GCP operation to complete."""
        # For zonal/regional operations, we'd need more complex handling
        # For now, assume global operations
        while not operation.done():
            operation = self.client.get(
                project=self.credentials.project_id,
                operation=operation.name
            )