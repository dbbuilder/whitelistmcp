"""Unit tests for IP validation utilities."""

import pytest
import ipaddress
from unittest.mock import patch, Mock
from awswhitelist.utils.ip_validator import (
    validate_ip_address,
    validate_cidr_block,
    is_private_ip,
    is_public_ip,
    get_current_ip,
    normalize_ip_input,
    IPValidationError
)


class TestValidateIPAddress:
    """Test IP address validation."""
    
    def test_valid_ipv4_addresses(self):
        """Test validating valid IPv4 addresses."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "1.1.1.1",
            "255.255.255.255",
            "0.0.0.0"
        ]
        
        for ip in valid_ips:
            assert validate_ip_address(ip) is True
    
    def test_valid_ipv6_addresses(self):
        """Test validating valid IPv6 addresses."""
        valid_ips = [
            "2001:db8::1",
            "fe80::1",
            "::1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "2001:db8:85a3::8a2e:370:7334"
        ]
        
        for ip in valid_ips:
            assert validate_ip_address(ip) is True
    
    def test_invalid_ip_addresses(self):
        """Test validating invalid IP addresses."""
        invalid_ips = [
            "256.256.256.256",
            "192.168.1",
            "192.168.1.1.1",
            "not-an-ip",
            "192.168.1.1/24",  # CIDR, not IP
            "",
            None,
            "localhost",
            "google.com"
        ]
        
        for ip in invalid_ips:
            assert validate_ip_address(ip) is False


class TestValidateCIDRBlock:
    """Test CIDR block validation."""
    
    def test_valid_ipv4_cidr_blocks(self):
        """Test validating valid IPv4 CIDR blocks."""
        valid_cidrs = [
            "192.168.1.0/24",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "0.0.0.0/0",
            "192.168.1.1/32"
        ]
        
        for cidr in valid_cidrs:
            assert validate_cidr_block(cidr) is True
    
    def test_valid_ipv6_cidr_blocks(self):
        """Test validating valid IPv6 CIDR blocks."""
        valid_cidrs = [
            "2001:db8::/32",
            "fe80::/10",
            "::/0",
            "2001:db8::1/128"
        ]
        
        for cidr in valid_cidrs:
            assert validate_cidr_block(cidr) is True
    
    def test_invalid_cidr_blocks(self):
        """Test validating invalid CIDR blocks."""
        invalid_cidrs = [
            "192.168.1.0/33",  # Invalid prefix length for IPv4
            # Note: "192.168.1.0" without prefix is actually valid (defaults to /32)
            "192.168.1.0/",  # Missing prefix number
            "not-a-cidr",
            "",
            None,
            "192.168.1.0/24/32",  # Multiple prefixes
            "2001:db8::/129"  # Invalid prefix length for IPv6
        ]
        
        for cidr in invalid_cidrs:
            assert validate_cidr_block(cidr) is False


class TestPrivatePublicIP:
    """Test private/public IP detection."""
    
    def test_is_private_ip(self):
        """Test detecting private IP addresses."""
        private_ips = [
            "192.168.1.1",
            "192.168.255.255",
            "10.0.0.1",
            "10.255.255.255",
            "172.16.0.1",
            "172.31.255.255",
            "127.0.0.1",  # Loopback
            "169.254.1.1"  # Link-local
        ]
        
        for ip in private_ips:
            assert is_private_ip(ip) is True
    
    def test_is_public_ip(self):
        """Test detecting public IP addresses."""
        public_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "172.32.0.1",  # Outside private range
            "192.169.0.1",  # Outside private range
            "11.0.0.1"  # Outside private range
        ]
        
        for ip in public_ips:
            assert is_public_ip(ip) is True
    
    def test_private_public_mutual_exclusion(self):
        """Test that IPs are either private or public, not both."""
        test_ips = [
            "192.168.1.1",
            "8.8.8.8",
            "10.0.0.1",
            "172.16.0.1",
            "1.1.1.1"
        ]
        
        for ip in test_ips:
            # An IP should be either private or public, not both
            assert is_private_ip(ip) != is_public_ip(ip)


class TestNormalizeIPInput:
    """Test IP input normalization."""
    
    def test_normalize_single_ip(self):
        """Test normalizing single IP addresses."""
        # Single IP should be converted to /32 CIDR
        assert normalize_ip_input("192.168.1.1") == "192.168.1.1/32"
        assert normalize_ip_input("10.0.0.1") == "10.0.0.1/32"
    
    def test_normalize_cidr_block(self):
        """Test normalizing CIDR blocks."""
        # CIDR blocks should remain unchanged
        assert normalize_ip_input("192.168.1.0/24") == "192.168.1.0/24"
        assert normalize_ip_input("10.0.0.0/8") == "10.0.0.0/8"
    
    def test_normalize_with_whitespace(self):
        """Test normalizing IPs with whitespace."""
        assert normalize_ip_input("  192.168.1.1  ") == "192.168.1.1/32"
        assert normalize_ip_input("\t10.0.0.0/24\n") == "10.0.0.0/24"
    
    def test_normalize_special_values(self):
        """Test normalizing special values."""
        # "current" should trigger IP detection (mocked in tests)
        
        # Mock successful IP detection
        with patch('awswhitelist.utils.ip_validator.get_current_ip') as mock_get_ip:
            mock_get_ip.return_value = {'ip': '203.0.113.1', 'source': 'test'}
            assert normalize_ip_input("current") == "203.0.113.1/32"
        
        # Mock failed IP detection
        with patch('awswhitelist.utils.ip_validator.get_current_ip') as mock_get_ip:
            mock_get_ip.return_value = {'ip': None, 'source': 'failed'}
            with pytest.raises(IPValidationError):
                normalize_ip_input("current")
    
    def test_normalize_invalid_input(self):
        """Test normalizing invalid input."""
        with pytest.raises(IPValidationError):
            normalize_ip_input("not-an-ip")
        
        with pytest.raises(IPValidationError):
            normalize_ip_input("")
        
        with pytest.raises(IPValidationError):
            normalize_ip_input("192.168.1.0/33")


class TestGetCurrentIP:
    """Test current IP detection."""
    
    def test_get_current_ip_with_working_service(self):
        """Test get_current_ip with working external service."""
        # Mock successful response from ipify
        with patch('awswhitelist.utils.ip_validator.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {'ip': '203.0.113.1'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = get_current_ip()
            assert isinstance(result, dict)
            assert result['ip'] == '203.0.113.1'
            assert 'api.ipify.org' in result['source']
            assert validate_ip_address(result['ip'])
    
    @patch('awswhitelist.utils.ip_validator.socket.socket')
    @patch('awswhitelist.utils.ip_validator.requests.get')
    def test_get_current_ip_with_fallback(self, mock_get, mock_socket_class):
        """Test get_current_ip fallback to socket method."""
        # Mock all HTTP requests failing
        mock_get.side_effect = Exception("Network error")
        
        # Mock socket
        mock_sock_instance = Mock()
        mock_sock_instance.getsockname.return_value = ('192.168.1.100', 0)
        mock_sock_instance.__enter__ = Mock(return_value=mock_sock_instance)
        mock_sock_instance.__exit__ = Mock(return_value=None)
        mock_socket_class.return_value = mock_sock_instance
        
        result = get_current_ip()
        assert result['ip'] == '192.168.1.100'
        assert result['source'] == 'local_socket'
    
    @patch('awswhitelist.utils.ip_validator.socket.socket')
    @patch('awswhitelist.utils.ip_validator.requests.get')
    def test_get_current_ip_total_failure(self, mock_get, mock_socket_class):
        """Test get_current_ip when all methods fail."""
        # Mock all HTTP requests failing
        mock_get.side_effect = Exception("Network error")
        
        # Mock socket also failing
        mock_socket_class.side_effect = Exception("Socket error")
        
        result = get_current_ip()
        assert result['ip'] is None
        assert result['source'] == 'failed'