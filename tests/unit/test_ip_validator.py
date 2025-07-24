"""Unit tests for IP validation utilities."""

import pytest
from ipaddress import IPv4Network, IPv6Network

from whitelistmcp.utils.ip_validator import (
    validate_ip_address,
    validate_cidr_block,
    normalize_ip_input,
    IPValidationError,
    ip_in_cidr,
    is_private_ip,
    is_public_ip,
    cidr_overlap
)


class TestValidateIPAddress:
    """Test validate_ip_address function."""
    
    def test_valid_ipv4(self):
        """Test valid IPv4 addresses."""
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("10.0.0.0") is True
        assert validate_ip_address("172.16.0.1") is True
        assert validate_ip_address("8.8.8.8") is True
        assert validate_ip_address("255.255.255.255") is True
        assert validate_ip_address("0.0.0.0") is True
    
    def test_invalid_ipv4(self):
        """Test invalid IPv4 addresses."""
        assert validate_ip_address("256.1.1.1") is False
        assert validate_ip_address("192.168.1") is False
        assert validate_ip_address("192.168.1.1.1") is False
        assert validate_ip_address("192.168.-1.1") is False
        assert validate_ip_address("192.168.a.1") is False
        assert validate_ip_address("") is False
        assert validate_ip_address("not-an-ip") is False
        assert validate_ip_address(None) is False
    
    def test_valid_ipv6(self):
        """Test valid IPv6 addresses."""
        assert validate_ip_address("2001:db8::1") is True
        assert validate_ip_address("::1") is True
        assert validate_ip_address("fe80::1") is True
        assert validate_ip_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334") is True
    
    def test_cidr_notation(self):
        """Test that CIDR notation is not considered a valid IP."""
        assert validate_ip_address("192.168.1.0/24") is False
        assert validate_ip_address("10.0.0.0/8") is False
        assert validate_ip_address("2001:db8::/32") is False


class TestValidateCIDRBlock:
    """Test validate_cidr_block function."""
    
    def test_valid_ipv4_cidr(self):
        """Test valid IPv4 CIDR blocks."""
        assert validate_cidr_block("192.168.1.0/24") is True
        assert validate_cidr_block("10.0.0.0/8") is True
        assert validate_cidr_block("172.16.0.0/16") is True
        assert validate_cidr_block("0.0.0.0/0") is True
        assert validate_cidr_block("192.168.1.1/32") is True
    
    def test_invalid_ipv4_cidr(self):
        """Test invalid IPv4 CIDR blocks."""
        assert validate_cidr_block("192.168.1.0/33") is False
        assert validate_cidr_block("192.168.1.0/-1") is False
        assert validate_cidr_block("192.168.1.0/") is False
        assert validate_cidr_block("192.168.1.0") is True  # Plain IPs are valid (treated as /32)
        assert validate_cidr_block("256.1.1.1/24") is False
        assert validate_cidr_block("192.168.1.0/24/24") is False
        assert validate_cidr_block(None) is False
    
    def test_valid_ipv6_cidr(self):
        """Test valid IPv6 CIDR blocks."""
        assert validate_cidr_block("2001:db8::/32") is True
        assert validate_cidr_block("fe80::/10") is True
        assert validate_cidr_block("::/0") is True
        assert validate_cidr_block("2001:db8::1/128") is True
    
    def test_edge_cases(self):
        """Test edge cases."""
        assert validate_cidr_block("") is False
        assert validate_cidr_block("/24") is False
        assert validate_cidr_block("192.168.1.0/a") is False


class TestNormalizeIPInput:
    """Test normalize_ip_input function."""
    
    def test_single_ip_normalization(self):
        """Test normalization of single IP addresses."""
        assert normalize_ip_input("192.168.1.1") == "192.168.1.1/32"
        assert normalize_ip_input("10.0.0.1") == "10.0.0.1/32"
        assert normalize_ip_input("0.0.0.0") == "0.0.0.0/32"
    
    def test_cidr_normalization(self):
        """Test normalization of CIDR blocks."""
        assert normalize_ip_input("192.168.1.0/24") == "192.168.1.0/24"
        assert normalize_ip_input("10.0.0.0/8") == "10.0.0.0/8"
        assert normalize_ip_input("172.16.0.0/16") == "172.16.0.0/16"
    
    def test_ipv6_normalization(self):
        """Test normalization of IPv6 addresses."""
        assert normalize_ip_input("2001:db8::1") == "2001:db8::1/128"
        assert normalize_ip_input("2001:db8::/32") == "2001:db8::/32"
        assert normalize_ip_input("::1") == "::1/128"
    
    def test_whitespace_handling(self):
        """Test handling of whitespace."""
        assert normalize_ip_input("  192.168.1.1  ") == "192.168.1.1/32"
        assert normalize_ip_input("\t10.0.0.0/8\n") == "10.0.0.0/8"
    
    def test_invalid_input(self):
        """Test invalid input handling."""
        with pytest.raises(IPValidationError, match="IP input cannot be empty"):
            normalize_ip_input("")
        
        with pytest.raises(IPValidationError, match="Invalid IP address or CIDR"):
            normalize_ip_input("not-an-ip")
        
        with pytest.raises(IPValidationError, match="Invalid IP address or CIDR"):
            normalize_ip_input("256.1.1.1")
        
        with pytest.raises(IPValidationError, match="Invalid CIDR block"):
            normalize_ip_input("192.168.1.0/33")


class TestIPInCIDR:
    """Test ip_in_cidr function."""
    
    def test_ip_in_range(self):
        """Test IP address in range."""
        assert ip_in_cidr("192.168.1.100", "192.168.1.0/24") is True
        assert ip_in_cidr("10.0.0.1", "10.0.0.0/8") is True
        assert ip_in_cidr("172.16.5.5", "172.16.0.0/16") is True
    
    def test_ip_not_in_range(self):
        """Test IP address not in range."""
        assert ip_in_cidr("192.168.2.1", "192.168.1.0/24") is False
        assert ip_in_cidr("11.0.0.1", "10.0.0.0/8") is False
        assert ip_in_cidr("172.17.0.1", "172.16.0.0/16") is False
    
    def test_exact_match(self):
        """Test exact IP match."""
        assert ip_in_cidr("192.168.1.1", "192.168.1.1/32") is True
        assert ip_in_cidr("192.168.1.2", "192.168.1.1/32") is False
    
    def test_edge_addresses(self):
        """Test network and broadcast addresses."""
        assert ip_in_cidr("192.168.1.0", "192.168.1.0/24") is True
        assert ip_in_cidr("192.168.1.255", "192.168.1.0/24") is True
    
    def test_ipv6_in_range(self):
        """Test IPv6 addresses in range."""
        assert ip_in_cidr("2001:db8::1", "2001:db8::/32") is True
        assert ip_in_cidr("2001:db9::1", "2001:db8::/32") is False
    
    def test_invalid_input(self):
        """Test invalid input handling."""
        with pytest.raises(ValueError, match="Invalid IP or CIDR"):
            ip_in_cidr("invalid", "192.168.1.0/24")
        
        with pytest.raises(ValueError, match="Invalid IP or CIDR"):
            ip_in_cidr("192.168.1.1", "invalid")


class TestIsPrivateIP:
    """Test is_private_ip function."""
    
    def test_private_ipv4(self):
        """Test private IPv4 addresses."""
        assert is_private_ip("192.168.1.1") is True
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True
    
    def test_public_ipv4(self):
        """Test public IPv4 addresses."""
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False
        assert is_private_ip("172.32.0.1") is False
    
    def test_special_addresses(self):
        """Test special addresses."""
        assert is_private_ip("127.0.0.1") is True  # Loopback
        assert is_private_ip("169.254.1.1") is True  # Link-local


class TestIsPublicIP:
    """Test is_public_ip function."""
    
    def test_public_ipv4(self):
        """Test public IPv4 addresses."""
        assert is_public_ip("8.8.8.8") is True
        assert is_public_ip("1.1.1.1") is True
        assert is_public_ip("172.32.0.1") is True
    
    def test_private_ipv4(self):
        """Test private IPv4 addresses."""
        assert is_public_ip("192.168.1.1") is False
        assert is_public_ip("10.0.0.1") is False
        assert is_public_ip("172.16.0.1") is False


class TestCIDROverlap:
    """Test cidr_overlap function."""
    
    def test_overlapping_cidrs(self):
        """Test overlapping CIDR blocks."""
        assert cidr_overlap("192.168.1.0/24", "192.168.1.128/25") is True
        assert cidr_overlap("10.0.0.0/8", "10.10.0.0/16") is True
        assert cidr_overlap("0.0.0.0/0", "192.168.1.0/24") is True
    
    def test_non_overlapping_cidrs(self):
        """Test non-overlapping CIDR blocks."""
        assert cidr_overlap("192.168.1.0/24", "192.168.2.0/24") is False
        assert cidr_overlap("10.0.0.0/16", "172.16.0.0/16") is False
    
    def test_same_cidr(self):
        """Test same CIDR blocks."""
        assert cidr_overlap("192.168.1.0/24", "192.168.1.0/24") is True
    
    def test_invalid_cidrs(self):
        """Test invalid CIDR inputs."""
        with pytest.raises(ValueError, match="Invalid CIDR block"):
            cidr_overlap("invalid", "192.168.1.0/24")
        
        with pytest.raises(ValueError, match="Invalid CIDR block"):
            cidr_overlap("192.168.1.0/24", "invalid")


class TestIPValidationError:
    """Test IPValidationError exception."""
    
    def test_error_creation(self):
        """Test error creation and message."""
        error = IPValidationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_error_raising(self):
        """Test raising the error."""
        with pytest.raises(IPValidationError) as exc_info:
            raise IPValidationError("Custom validation error")
        
        assert "Custom validation error" in str(exc_info.value)