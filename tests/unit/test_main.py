"""Unit tests for main server application."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

from awswhitelist.main import MCPServer, main


class TestMCPServer:
    """Test MCP server functionality."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server instance."""
        with patch('awswhitelist.main.setup_logging') as mock_logging:
            mock_logging.return_value = Mock()
            server = MCPServer()
            return server
    
    def test_server_initialization(self):
        """Test server initialization."""
        with patch('awswhitelist.main.setup_logging') as mock_logging:
            with patch('awswhitelist.main.load_config') as mock_config:
                mock_logger = Mock()
                mock_logging.return_value = mock_logger
                
                server = MCPServer()
                
                assert server.config is not None
                assert server.handler is not None
                assert server.logger == mock_logger
                mock_logger.info.assert_called()
    
    def test_process_request_success(self, server):
        """Test processing a valid request."""
        request_data = json.dumps({
            "jsonrpc": "2.0",
            "id": "test-123",
            "method": "whitelist/list",
            "params": {
                "credentials": {
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "secret"
                },
                "security_group_id": "sg-123456"
            }
        })
        
        # Mock handler response
        with patch.object(server.handler, 'handle_request') as mock_handle:
            from awswhitelist.mcp.handler import MCPResponse
            mock_handle.return_value = MCPResponse(
                id="test-123",
                result={"success": True, "rules": []}
            )
            
            response_str = server.process_request(request_data)
            response = json.loads(response_str)
            
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "test-123"
            assert response["result"]["success"] is True
            assert "error" not in response
    
    def test_process_request_parse_error(self, server):
        """Test processing invalid JSON."""
        request_data = "not valid json"
        
        response_str = server.process_request(request_data)
        response = json.loads(response_str)
        
        assert response["error"]["code"] == -32700
        assert "Parse error" in response["error"]["message"]
    
    def test_process_request_invalid_request(self, server):
        """Test processing invalid MCP request."""
        request_data = json.dumps({
            "jsonrpc": "1.0",  # Invalid version
            "id": "test-123",
            "method": "test"
        })
        
        response_str = server.process_request(request_data)
        response = json.loads(response_str)
        
        assert response["error"]["code"] == -32600
        assert "Invalid Request" in response["error"]["message"]
    
    def test_process_request_handler_error(self, server):
        """Test processing when handler raises error."""
        request_data = json.dumps({
            "jsonrpc": "2.0",
            "id": "test-123",
            "method": "whitelist/add",
            "params": {}
        })
        
        with patch.object(server.handler, 'handle_request') as mock_handle:
            mock_handle.side_effect = Exception("Handler error")
            
            response_str = server.process_request(request_data)
            response = json.loads(response_str)
            
            assert response["error"]["code"] == -32603
            assert "Internal error" in response["error"]["message"]
    
    @patch('sys.stdin', StringIO('{"jsonrpc":"2.0","id":"1","method":"test","params":{}}\n'))
    @patch('sys.stdout', new_callable=StringIO)
    def test_run_server(self, mock_stdout, server):
        """Test running the server."""
        # Mock handler
        with patch.object(server.handler, 'handle_request') as mock_handle:
            from awswhitelist.mcp.handler import MCPResponse
            mock_handle.return_value = MCPResponse(
                id="1",
                result={"success": True}
            )
            
            # Run server (will process one line and exit)
            server.run()
            
            # Check output
            output = mock_stdout.getvalue()
            assert output.strip()  # Should have written response
            
            response = json.loads(output.strip())
            assert response["result"]["success"] is True
    
    @patch('sys.stdin', StringIO(''))
    def test_run_server_empty_input(self, server):
        """Test running server with empty input."""
        server.run()
        # Should complete without error
    
    @patch('sys.stdin')
    def test_run_server_keyboard_interrupt(self, mock_stdin, server):
        """Test handling keyboard interrupt."""
        mock_stdin.__iter__.side_effect = KeyboardInterrupt()
        
        server.run()
        # Should log and exit gracefully
        # Check that info was called with the expected message
        calls = [call[0][0] for call in server.logger.info.call_args_list]
        assert "Server interrupted by user" in calls


class TestMain:
    """Test main entry point."""
    
    @patch('sys.argv', ['awswhitelist'])
    @patch('awswhitelist.main.MCPServer')
    def test_main_default(self, mock_server_class):
        """Test main with default arguments."""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        
        main()
        
        mock_server_class.assert_called_once_with(config_path=None)
        mock_server.run.assert_called_once()
    
    @patch('sys.argv', ['awswhitelist', '-c', 'config.json'])
    @patch('awswhitelist.main.MCPServer')
    def test_main_with_config(self, mock_server_class):
        """Test main with config file."""
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        
        main()
        
        mock_server_class.assert_called_once_with(config_path='config.json')
        mock_server.run.assert_called_once()
    
    @patch('sys.argv', ['awswhitelist', '-v'])
    @patch('awswhitelist.main.MCPServer')
    def test_main_verbose(self, mock_server_class):
        """Test main with verbose flag."""
        mock_server = Mock()
        mock_server.logger = Mock()
        mock_server_class.return_value = mock_server
        
        main()
        
        mock_server.logger.setLevel.assert_called_once_with("DEBUG")
    
    @patch('sys.argv', ['awswhitelist', '--version'])
    def test_main_version(self):
        """Test showing version."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0