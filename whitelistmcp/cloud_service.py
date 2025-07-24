"""Unified cloud service interface for multi-cloud whitelisting operations."""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from whitelistmcp.config import CloudProvider, Config
from whitelistmcp.utils.logging import get_logger

# Import cloud-specific services
from whitelistmcp.aws.service import (
    AWSService, 
    AWSCredentials, 
    SecurityGroupRule as AWSRule
)
from whitelistmcp.azure.service import (
    AzureService,
    AzureCredentials,
    NSGRule as AzureRule
)
from whitelistmcp.gcp.service import (
    GCPService,
    GCPCredentials,
    FirewallRule as GCPRule
)

logger = get_logger(__name__)


@dataclass
class CloudCredentials:
    """Unified cloud credentials container."""
    cloud: CloudProvider
    aws_credentials: Optional[AWSCredentials] = None
    azure_credentials: Optional[AzureCredentials] = None
    gcp_credentials: Optional[GCPCredentials] = None


@dataclass
class UnifiedWhitelistResult:
    """Result from multi-cloud whitelist operation."""
    cloud: CloudProvider
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CloudServiceManager:
    """Manages whitelisting operations across multiple cloud providers."""
    
    def __init__(self, config: Config):
        """Initialize cloud service manager."""
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def _get_aws_service(self, credentials: AWSCredentials) -> AWSService:
        """Get AWS service instance."""
        return AWSService(credentials)
    
    def _get_azure_service(self, credentials: AzureCredentials) -> AzureService:
        """Get Azure service instance."""
        return AzureService(credentials)
    
    def _get_gcp_service(self, credentials: GCPCredentials) -> GCPService:
        """Get GCP service instance."""
        return GCPService(credentials, additive_only=self.config.default_parameters.gcp_additive_only)
    
    def add_whitelist_rule(
        self,
        credentials: CloudCredentials,
        target: str,  # security_group_id, nsg_name, or firewall_name
        ip_address: str,
        port: Optional[int] = None,
        protocol: str = "tcp",
        description: Optional[str] = None,
        service_name: Optional[str] = None,
        resource_group: Optional[str] = None  # For Azure
    ) -> List[UnifiedWhitelistResult]:
        """Add whitelist rule to specified cloud(s)."""
        results = []
        
        # Use default port if not specified
        if port is None:
            port = self.config.default_parameters.port
        
        # Determine which clouds to target
        clouds = []
        if credentials.cloud == CloudProvider.ALL:
            if credentials.aws_credentials:
                clouds.append(CloudProvider.AWS)
            if credentials.azure_credentials:
                clouds.append(CloudProvider.AZURE)
            if credentials.gcp_credentials:
                clouds.append(CloudProvider.GCP)
        else:
            clouds.append(credentials.cloud)
        
        # Execute operations in parallel
        futures = {}
        
        for cloud in clouds:
            if cloud == CloudProvider.AWS and credentials.aws_credentials:
                future = self.executor.submit(
                    self._add_aws_rule,
                    credentials.aws_credentials,
                    target,
                    ip_address,
                    port,
                    protocol,
                    description,
                    service_name
                )
                futures[future] = CloudProvider.AWS
                
            elif cloud == CloudProvider.AZURE and credentials.azure_credentials:
                future = self.executor.submit(
                    self._add_azure_rule,
                    credentials.azure_credentials,
                    target,
                    resource_group or self.config.default_parameters.azure_resource_group,
                    ip_address,
                    port,
                    protocol,
                    description,
                    service_name
                )
                futures[future] = CloudProvider.AZURE
                
            elif cloud == CloudProvider.GCP and credentials.gcp_credentials:
                future = self.executor.submit(
                    self._add_gcp_rule,
                    credentials.gcp_credentials,
                    ip_address,
                    port,
                    protocol,
                    description,
                    service_name
                )
                futures[future] = CloudProvider.GCP
        
        # Collect results
        for future in as_completed(futures):
            cloud = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to add rule to {cloud}: {str(e)}")
                results.append(UnifiedWhitelistResult(
                    cloud=cloud,
                    success=False,
                    message=f"Failed to add rule to {cloud}",
                    error=str(e)
                ))
        
        return results
    
    def remove_whitelist_rule(
        self,
        credentials: CloudCredentials,
        target: str,  # security_group_id, nsg_name, or project_id
        ip_address: Optional[str] = None,
        port: Optional[Union[int, str]] = None,
        service_name: Optional[str] = None,
        protocol: str = "tcp",
        resource_group: Optional[str] = None  # For Azure
    ) -> List[UnifiedWhitelistResult]:
        """Remove whitelist rules based on flexible criteria."""
        results = []
        
        # Determine which clouds to target
        clouds = []
        if credentials.cloud == CloudProvider.ALL:
            if credentials.aws_credentials:
                clouds.append(CloudProvider.AWS)
            if credentials.azure_credentials:
                clouds.append(CloudProvider.AZURE)
            if credentials.gcp_credentials:
                clouds.append(CloudProvider.GCP)
        else:
            clouds.append(credentials.cloud)
        
        # Execute operations in parallel
        futures = {}
        
        for cloud in clouds:
            if cloud == CloudProvider.AWS and credentials.aws_credentials:
                future = self.executor.submit(
                    self._remove_aws_rule,
                    credentials.aws_credentials,
                    target,
                    ip_address,
                    port,
                    service_name,
                    protocol
                )
                futures[future] = CloudProvider.AWS
                
            elif cloud == CloudProvider.AZURE and credentials.azure_credentials:
                future = self.executor.submit(
                    self._remove_azure_rule,
                    credentials.azure_credentials,
                    target,
                    resource_group or self.config.default_parameters.azure_resource_group,
                    ip_address,
                    port,
                    service_name,
                    protocol
                )
                futures[future] = CloudProvider.AZURE
                
            elif cloud == CloudProvider.GCP and credentials.gcp_credentials:
                future = self.executor.submit(
                    self._remove_gcp_rule,
                    credentials.gcp_credentials,
                    target,
                    ip_address,
                    port,
                    service_name,
                    protocol
                )
                futures[future] = CloudProvider.GCP
        
        # Collect results
        for future in as_completed(futures):
            cloud = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to remove rule from {cloud}: {str(e)}")
                results.append(UnifiedWhitelistResult(
                    cloud=cloud,
                    success=False,
                    message=f"Failed to remove rule from {cloud}",
                    error=str(e)
                ))
        
        return results
    
    def _add_aws_rule(
        self,
        credentials: AWSCredentials,
        security_group_id: str,
        ip_address: str,
        port: int,
        protocol: str,
        description: Optional[str],
        service_name: Optional[str]
    ) -> UnifiedWhitelistResult:
        """Add rule to AWS security group."""
        try:
            from whitelistmcp.utils.ip_validator import normalize_ip_input
            from whitelistmcp.aws.service import create_rule_description
            
            service = self._get_aws_service(credentials)
            
            # Create rule
            rule = AWSRule(
                group_id=security_group_id,
                ip_protocol=protocol,
                from_port=port,
                to_port=port,
                cidr_ip=normalize_ip_input(ip_address),
                description=description or create_rule_description(
                    self.config.default_parameters.description_template,
                    service_name=service_name
                )
            )
            
            result = service.add_whitelist_rule(rule)
            
            return UnifiedWhitelistResult(
                cloud=CloudProvider.AWS,
                success=result.success,
                message=result.message,
                details={"rule": rule.__dict__} if result.success else None,
                error=result.error
            )
            
        except Exception as e:
            return UnifiedWhitelistResult(
                cloud=CloudProvider.AWS,
                success=False,
                message="Failed to add AWS rule",
                error=str(e)
            )
    
    def _add_azure_rule(
        self,
        credentials: AzureCredentials,
        nsg_name: str,
        resource_group: str,
        ip_address: str,
        port: int,
        protocol: str,
        description: Optional[str],
        service_name: Optional[str]
    ) -> UnifiedWhitelistResult:
        """Add rule to Azure NSG."""
        try:
            from whitelistmcp.utils.ip_validator import normalize_ip_input
            from whitelistmcp.azure.service import create_rule_description
            
            service = self._get_azure_service(credentials)
            
            # Create rule
            rule = AzureRule(
                nsg_name=nsg_name,
                resource_group=resource_group,
                name=f"allow-{ip_address.replace('.', '-').replace('/', '-')}-{port}",
                priority=0,  # Will be auto-assigned
                protocol=protocol.capitalize(),
                source_address_prefix=normalize_ip_input(ip_address),
                destination_port_range=str(port),
                description=description or create_rule_description(
                    self.config.default_parameters.description_template,
                    service_name=service_name
                )
            )
            
            result = service.add_whitelist_rule(rule)
            
            return UnifiedWhitelistResult(
                cloud=CloudProvider.AZURE,
                success=result.success,
                message=result.message,
                details={"rule": rule.__dict__} if result.success else None,
                error=result.error
            )
            
        except Exception as e:
            return UnifiedWhitelistResult(
                cloud=CloudProvider.AZURE,
                success=False,
                message="Failed to add Azure rule",
                error=str(e)
            )
    
    def _add_gcp_rule(
        self,
        credentials: GCPCredentials,
        ip_address: str,
        port: int,
        protocol: str,
        description: Optional[str],
        service_name: Optional[str]
    ) -> UnifiedWhitelistResult:
        """Add rule to GCP firewall."""
        try:
            from whitelistmcp.utils.ip_validator import normalize_ip_input
            from whitelistmcp.gcp.service import create_rule_description
            
            service = self._get_gcp_service(credentials)
            
            # Generate rule name
            clean_ip = ip_address.replace('.', '-').replace('/', '-')
            rule_name = f"allow-{service_name or 'port'}-{clean_ip}-{port}"
            
            # Create rule
            rule = GCPRule(
                name=rule_name,
                project_id=credentials.project_id,
                network=self.config.default_parameters.gcp_network,
                source_ranges=[normalize_ip_input(ip_address)],
                allowed=[{
                    'IPProtocol': protocol,
                    'ports': [str(port)]
                }],
                description=description or create_rule_description(
                    self.config.default_parameters.description_template,
                    service_name=service_name
                )
            )
            
            result = service.add_whitelist_rule(rule)
            
            return UnifiedWhitelistResult(
                cloud=CloudProvider.GCP,
                success=result.success,
                message=result.message,
                details={"rule": rule.__dict__} if result.success else None,
                error=result.error
            )
            
        except Exception as e:
            return UnifiedWhitelistResult(
                cloud=CloudProvider.GCP,
                success=False,
                message="Failed to add GCP rule",
                error=str(e)
            )
    
    def _remove_aws_rule(
        self,
        credentials: AWSCredentials,
        security_group_id: str,
        ip_address: Optional[str],
        port: Optional[Union[int, str]],
        service_name: Optional[str],
        protocol: str
    ) -> UnifiedWhitelistResult:
        """Remove rule from AWS security group."""
        try:
            service = self._get_aws_service(credentials)
            result = service.remove_whitelist_rule(
                security_group_id,
                ip_address,
                port,
                service_name,
                protocol
            )
            
            return UnifiedWhitelistResult(
                cloud=CloudProvider.AWS,
                success=result.success,
                message=result.message,
                error=result.error
            )
            
        except Exception as e:
            return UnifiedWhitelistResult(
                cloud=CloudProvider.AWS,
                success=False,
                message="Failed to remove AWS rule",
                error=str(e)
            )
    
    def _remove_azure_rule(
        self,
        credentials: AzureCredentials,
        nsg_name: str,
        resource_group: str,
        ip_address: Optional[str],
        port: Optional[Union[int, str]],
        service_name: Optional[str],
        protocol: str
    ) -> UnifiedWhitelistResult:
        """Remove rule from Azure NSG."""
        try:
            service = self._get_azure_service(credentials)
            result = service.remove_whitelist_rule(
                nsg_name,
                resource_group,
                ip_address,
                port,
                service_name,
                protocol
            )
            
            return UnifiedWhitelistResult(
                cloud=CloudProvider.AZURE,
                success=result.success,
                message=result.message,
                error=result.error
            )
            
        except Exception as e:
            return UnifiedWhitelistResult(
                cloud=CloudProvider.AZURE,
                success=False,
                message="Failed to remove Azure rule",
                error=str(e)
            )
    
    def _remove_gcp_rule(
        self,
        credentials: GCPCredentials,
        project_id: str,
        ip_address: Optional[str],
        port: Optional[Union[int, str]],
        service_name: Optional[str],
        protocol: str
    ) -> UnifiedWhitelistResult:
        """Remove rule from GCP firewall."""
        try:
            service = self._get_gcp_service(credentials)
            result = service.remove_whitelist_rule(
                project_id,
                ip_address,
                port,
                service_name,
                protocol
            )
            
            return UnifiedWhitelistResult(
                cloud=CloudProvider.GCP,
                success=result.success,
                message=result.message,
                error=result.error
            )
            
        except Exception as e:
            return UnifiedWhitelistResult(
                cloud=CloudProvider.GCP,
                success=False,
                message="Failed to remove GCP rule",
                error=str(e)
            )