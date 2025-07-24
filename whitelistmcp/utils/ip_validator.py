"""IP address validation utilities."""

import ipaddress
import socket
from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException


class IPValidationError(Exception):
    """Exception raised for IP validation errors."""
    pass


def validate_ip_address(ip: Optional[str]) -> bool:
    """Validate if a string is a valid IP address (IPv4 or IPv6).
    
    Args:
        ip: IP address string to validate
    
    Returns:
        True if valid IP address, False otherwise
    """
    if not ip:
        return False
    
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_cidr_block(cidr: Optional[str]) -> bool:
    """Validate if a string is a valid CIDR block.
    
    Args:
        cidr: CIDR block string to validate (e.g., "192.168.1.0/24")
    
    Returns:
        True if valid CIDR block, False otherwise
    """
    if not cidr:
        return False
    
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except ValueError:
        return False


def is_private_ip(ip: str) -> bool:
    """Check if an IP address is private (RFC 1918).
    
    Args:
        ip: IP address to check
    
    Returns:
        True if private IP, False otherwise
    
    Raises:
        ValueError: If IP address is invalid
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
    except ValueError as e:
        raise ValueError(f"Invalid IP address: {ip}") from e


def is_public_ip(ip: str) -> bool:
    """Check if an IP address is public (routable on the internet).
    
    Args:
        ip: IP address to check
    
    Returns:
        True if public IP, False otherwise
    
    Raises:
        ValueError: If IP address is invalid
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        return not (ip_obj.is_private or ip_obj.is_loopback or 
                   ip_obj.is_link_local or ip_obj.is_multicast or 
                   ip_obj.is_reserved or ip_obj.is_unspecified)
    except ValueError as e:
        raise ValueError(f"Invalid IP address: {ip}") from e


def get_current_ip() -> Dict[str, Optional[str]]:
    """Get the current public IP address of this machine.
    
    Returns:
        Dictionary with:
        - ip: Current public IP address
        - source: Source of the IP information
    """
    # Try multiple services for redundancy
    services = [
        ("https://api.ipify.org?format=json", lambda r: r.json().get('ip')),
        ("https://ifconfig.me/ip", lambda r: r.text.strip()),
        ("https://icanhazip.com", lambda r: r.text.strip()),
        ("https://ident.me", lambda r: r.text.strip())
    ]
    
    for url, parser in services:
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            ip = parser(response)
            
            # Validate the returned IP
            if validate_ip_address(ip):
                return {
                    'ip': ip,
                    'source': url
                }
        except (RequestException, KeyError, ValueError, Exception):
            # Catch all exceptions to ensure we try all services
            continue
    
    # Fallback to local socket method
    try:
        # This gets the local IP that would be used to connect to the internet
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            
            return {
                'ip': local_ip,
                'source': 'local_socket'
            }
    except Exception:
        return {
            'ip': None,
            'source': 'failed'
        }


def normalize_ip_input(ip_input: str) -> str:
    """Normalize IP input to CIDR format.
    
    Args:
        ip_input: IP address or CIDR block, or "current" for current IP
    
    Returns:
        Normalized CIDR block (e.g., "192.168.1.1/32")
    
    Raises:
        IPValidationError: If input is invalid
    """
    if not ip_input:
        raise IPValidationError("IP input cannot be empty")
    
    # Clean whitespace
    ip_input = ip_input.strip()
    
    # Handle special case for current IP
    if ip_input.lower() == "current":
        current = get_current_ip()
        if not current['ip']:
            raise IPValidationError("Failed to detect current IP address")
        ip_input = current['ip']
    
    # Check if it's already a CIDR block
    if '/' in ip_input:
        if validate_cidr_block(ip_input):
            return ip_input
        else:
            raise IPValidationError(f"Invalid CIDR block: {ip_input}")
    
    # Check if it's a valid IP address
    if validate_ip_address(ip_input):
        # Convert single IP to /32 (IPv4) or /128 (IPv6) CIDR
        ip_obj = ipaddress.ip_address(ip_input)
        if isinstance(ip_obj, ipaddress.IPv4Address):
            return f"{ip_input}/32"
        else:
            return f"{ip_input}/128"
    
    raise IPValidationError(f"Invalid IP address or CIDR block: {ip_input}")


def ip_in_cidr(ip: str, cidr: str) -> bool:
    """Check if an IP address is within a CIDR block.
    
    Args:
        ip: IP address to check
        cidr: CIDR block to check against
    
    Returns:
        True if IP is in CIDR block, False otherwise
    
    Raises:
        ValueError: If IP or CIDR is invalid
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        network = ipaddress.ip_network(cidr, strict=False)
        return ip_obj in network
    except ValueError as e:
        raise ValueError(f"Invalid IP or CIDR: {e}") from e


def cidr_overlap(cidr1: str, cidr2: str) -> bool:
    """Check if two CIDR blocks overlap.
    
    Args:
        cidr1: First CIDR block
        cidr2: Second CIDR block
    
    Returns:
        True if CIDR blocks overlap, False otherwise
    
    Raises:
        ValueError: If either CIDR is invalid
    """
    try:
        network1 = ipaddress.ip_network(cidr1, strict=False)
        network2 = ipaddress.ip_network(cidr2, strict=False)
        return network1.overlaps(network2)
    except ValueError as e:
        raise ValueError(f"Invalid CIDR block: {e}") from e