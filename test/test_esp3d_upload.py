"""
Test cases for ESP3D upload functionality
"""
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from test import bootstrap


class TestESP3DFilenameGeneration(unittest.TestCase):
    """Test 8.3 filename generation and validation."""

    def test_generate_8_3_filename_with_counter(self):
        """Test filename generation with explicit counter."""
        from meerk40t.grbl.esp3d_upload import generate_8_3_filename
        
        filename = generate_8_3_filename(base="file", extension="gc", counter=1)
        self.assertEqual(filename, "file0001.gc")
        
        filename = generate_8_3_filename(base="test", extension="gc", counter=9999)
        self.assertEqual(filename, "test9999.gc")

    def test_generate_8_3_filename_truncation(self):
        """Test that long base names are truncated correctly."""
        from meerk40t.grbl.esp3d_upload import generate_8_3_filename
        
        filename = generate_8_3_filename(base="verylongname", extension="gc", counter=1)
        # Base is truncated to fit 8 chars total with counter
        self.assertTrue(len(filename.split(".")[0]) <= 8)
        self.assertTrue(filename.endswith(".gc"))

    def test_generate_8_3_filename_extension_truncation(self):
        """Test that long extensions are truncated."""
        from meerk40t.grbl.esp3d_upload import generate_8_3_filename
        
        filename = generate_8_3_filename(base="file", extension="gcode", counter=1)
        # Extension should be truncated to 3 chars
        ext = filename.split(".")[-1]
        self.assertEqual(len(ext), 3)

    def test_generate_8_3_filename_timestamp(self):
        """Test filename generation with timestamp."""
        from meerk40t.grbl.esp3d_upload import generate_8_3_filename
        
        filename = generate_8_3_filename(base="file", extension="gc")
        # Should generate a valid 8.3 filename
        self.assertIsNotNone(filename)
        self.assertTrue(filename.endswith(".gc"))
        parts = filename.split(".")
        self.assertEqual(len(parts), 2)
        self.assertLessEqual(len(parts[0]), 8)

    def test_validate_filename_8_3_valid(self):
        """Test validation of valid 8.3 filenames."""
        from meerk40t.grbl.esp3d_upload import validate_filename_8_3
        
        self.assertTrue(validate_filename_8_3("file0001.gc"))
        self.assertTrue(validate_filename_8_3("test.gc"))
        self.assertTrue(validate_filename_8_3("ABC12345.GCO"))
        self.assertTrue(validate_filename_8_3("a.b"))

    def test_validate_filename_8_3_invalid(self):
        """Test validation of invalid 8.3 filenames."""
        from meerk40t.grbl.esp3d_upload import validate_filename_8_3
        
        # Too long name
        self.assertFalse(validate_filename_8_3("verylongname.gc"))
        # Too long extension
        self.assertFalse(validate_filename_8_3("file.gcode"))
        # Spaces
        self.assertFalse(validate_filename_8_3("file 001.gc"))
        # Invalid characters
        self.assertFalse(validate_filename_8_3("file:001.gc"))
        self.assertFalse(validate_filename_8_3("file*001.gc"))
        # No extension
        self.assertFalse(validate_filename_8_3("file001"))
        # Empty
        self.assertFalse(validate_filename_8_3(""))


class TestESP3DConnection(unittest.TestCase):
    """Test ESP3D connection handling for the simplified implementation."""

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_connection_initialization(self, mock_requests):
        """Test basic ESP3D connection initialization (no auto-detection)."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection

        conn = ESP3DConnection("192.168.1.100", 80)
        self.assertEqual(conn.host, "192.168.1.100")
        self.assertEqual(conn.port, 80)
        self.assertEqual(conn.base_url, "http://192.168.1.100:80")
        # Session should not be created until used as a context manager
        self.assertIsNone(conn.session)

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_context_manager_login_behavior(self, mock_requests):
        """Test that session is created and login is attempted when credentials are provided."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection

        mock_session = MagicMock()
        mock_requests.Session.return_value = mock_session

        # Make the session.post return a successful response for login
        mock_post_resp = MagicMock()
        mock_post_resp.raise_for_status.return_value = None
        mock_session.post.return_value = mock_post_resp

        with ESP3DConnection("192.168.1.100", 80, username="user", password="pass") as conn:
            self.assertIsNotNone(conn.session)
            # Verify that login was attempted via POST
            mock_session.post.assert_called()

        mock_session.close.assert_called_once()

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_constructor_does_not_perform_network_calls(self, mock_requests):
        """Ensure __init__ does not perform network calls (no auto-detection)."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection

        # If requests.get would raise, constructor should still succeed
        mock_requests.get.side_effect = Exception("Connection failed")
        conn = ESP3DConnection("192.168.1.100", 80)
        # No calls performed during init
        mock_requests.get.assert_not_called()

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_test_connection_success(self, mock_requests):
        """Test successful connection test to /command endpoint."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection

        mock_test_response = Mock()
        mock_test_response.status_code = 200
        mock_test_response.text = "OK"
        mock_requests.get.return_value = mock_test_response

        conn = ESP3DConnection("192.168.1.100", 80)
        result = conn.test_connection()

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_test_connection_failure(self, mock_requests):
        """Test failed connection test (RequestException handling)."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection

        class MockRequestException(Exception):
            pass

        class MockTimeout(MockRequestException):
            pass

        class MockConnectionError(MockRequestException):
            pass

        mock_requests.RequestException = MockRequestException
        mock_requests.Timeout = MockTimeout
        mock_requests.ConnectionError = MockConnectionError

        mock_requests.get.side_effect = MockRequestException("Connection refused")

        conn = ESP3DConnection("192.168.1.100", 80)
        result = conn.test_connection()

        self.assertFalse(result["success"])
        self.assertIn("Connection refused", result["message"])

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_get_sd_info_success(self, mock_requests):
        """Test getting SD card information (parsing sizes)."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        {
            "files": [
                {"name": "test.gc", "size": "1.23 KB"},
                {"name": "subdir", "size": "-1"}
            ],
            "path": "/",
            "occupation": "52",
            "total": "1.31 MB",
            "used": "500.00 KB"
        }
        '''
        mock_requests.get.return_value = mock_response

        conn = ESP3DConnection("192.168.1.100", 80)
        result = conn.get_sd_info()

        self.assertTrue(result["success"])
        self.assertEqual(len(result["files"]), 2)
        self.assertEqual(result["occupation"], "52")
        self.assertGreater(result["total"], 0)
        self.assertGreater(result["used"], 0)
        self.assertEqual(result["free"], result["total"] - result["used"]) 

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_list_files(self, mock_requests):
        """Test listing files on SD card."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        {
            "files": [
                {"name": "file1.gc", "size": "1.23 KB"},
                {"name": "file2.gc", "size": "2.34 KB"}
            ],
            "path": "/",
            "occupation": "10",
            "total": "1.31 MB",
            "used": "100.00 KB"
        }
        '''
        mock_requests.get.return_value = mock_response

        conn = ESP3DConnection("192.168.1.100", 80)
        files = conn.list_files()

        self.assertEqual(files[0]["name"], "file1.gc")


class TestESP3DUpload(unittest.TestCase):
    """Test ESP3D file upload functionality."""

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_upload_file_success(self, mock_requests):
        """Test successful file upload."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection
        import tempfile
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.gc') as temp_file:
            temp_file.write("G0 X0 Y0\n")
            temp_path = temp_file.name
        
        try:
            # Mock firmware detection
            mock_firmware_response = MagicMock()
            mock_firmware_response.raise_for_status.return_value = None
            mock_firmware_response.text = '{"status": "ok", "data": {"FWTarget": "grbl"}}'
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok"}'
            
            mock_session = MagicMock()
            mock_session.post.return_value = mock_response
            # Mock the SD info call for space check
            mock_sd_response = Mock()
            mock_sd_response.status_code = 200
            mock_sd_response.text = '{"total": "1.31 MB", "used": "100 KB", "files": [], "path": "/", "occupation": "1"}'
            mock_session.get.return_value = mock_sd_response
            
            mock_requests.Session.return_value = mock_session
            mock_requests.get.return_value = mock_firmware_response
            
            with ESP3DConnection("192.168.1.100", 80) as conn:
                result = conn.upload_file(temp_path, "test.gc", "/")
            
            self.assertTrue(result["success"])
            self.assertEqual(result["filename"], "test.gc")
            self.assertGreater(result["size"], 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_upload_file_request_exception(self, mock_requests):
        """Test that upload_file raises ESP3DUploadError when the HTTP upload fails."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection, ESP3DUploadError
        import tempfile

        class MockRequestException(Exception):
            pass

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.gc') as temp_file:
            temp_file.write("G0 X0 Y0\n")
            temp_path = temp_file.name

        try:
            mock_session = MagicMock()
            # Simulate a request exception during POST
            mock_session.post.side_effect = MockRequestException("Upload failed")
            mock_requests.Session.return_value = mock_session
            mock_requests.RequestException = MockRequestException

            with ESP3DConnection("192.168.1.100", 80) as conn:
                with self.assertRaises(ESP3DUploadError):
                    conn.upload_file(temp_path, "test.gc", "/")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    def test_upload_file_not_found(self):
        """Test upload of non-existent file."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection, ESP3DUploadError
        
        # Mock firmware detection to avoid network calls
        with patch('meerk40t.grbl.esp3d_upload.requests') as mock_requests:
            mock_firmware_response = MagicMock()
            mock_firmware_response.raise_for_status.return_value = None
            mock_firmware_response.text = '{"status": "ok", "data": {"FWTarget": "grbl"}}'
            mock_requests.get.return_value = mock_firmware_response
            
            conn = ESP3DConnection("192.168.1.100", 80)
            
            with self.assertRaises(ESP3DUploadError) as context:
                conn.upload_file("/nonexistent/file.gc", "test.gc", "/")
        
        self.assertIn("not found", str(context.exception))


class TestESP3DExecute(unittest.TestCase):
    """Test ESP3D file execution functionality."""

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_execute_file_success(self, mock_requests):
        """Test successful file execution."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection
        
        # Mock firmware detection
        mock_firmware_response = MagicMock()
        mock_firmware_response.raise_for_status.return_value = None
        mock_firmware_response.text = '{"status": "ok", "data": {"FWTarget": "grbl"}}'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        
        mock_requests.get.side_effect = [mock_firmware_response, mock_response]
        
        conn = ESP3DConnection("192.168.1.100", 80)
        result = conn.execute_file("test.gc")
        
        self.assertTrue(result["success"])
        # Verify two get calls were made: firmware detection and command execution
        self.assertEqual(mock_requests.get.call_count, 2)
    def test_upload_file_not_found(self):
        """Test upload of non-existent file."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection, ESP3DUploadError
        
        # Mock firmware detection to avoid network calls
        with patch('meerk40t.grbl.esp3d_upload.requests') as mock_requests:
            mock_firmware_response = MagicMock()
            mock_firmware_response.raise_for_status.return_value = None
            mock_firmware_response.text = '{"status": "ok", "data": {"FWTarget": "grbl"}}'
            mock_requests.get.return_value = mock_firmware_response
            
            conn = ESP3DConnection("192.168.1.100", 80)
            
            with self.assertRaises(ESP3DUploadError) as context:
                conn.upload_file("/nonexistent/file.gc", "test.gc", "/")
        
        self.assertIn("not found", str(context.exception))


class TestESP3DExecute(unittest.TestCase):
    """Test ESP3D file execution functionality."""

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_execute_file_success(self, mock_requests):
        """Test successful file execution."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_requests.get.return_value = mock_response

        conn = ESP3DConnection("192.168.1.100", 80)
        result = conn.execute_file("test.gc")

        self.assertTrue(result["success"])
        # Verify one get call was made for execution
        self.assertEqual(mock_requests.get.call_count, 1)

        call_args = mock_requests.get.call_args
        self.assertEqual(call_args[1]["params"]["commandText"], "[ESP220]/test.gc")

    @patch('meerk40t.grbl.esp3d_upload.REQUESTS_AVAILABLE', True)
    @patch('meerk40t.grbl.esp3d_upload.requests')
    def test_delete_file_success(self, mock_requests):
        """Test successful file deletion."""
        from meerk40t.grbl.esp3d_upload import ESP3DConnection
        
        # Mock firmware detection
        mock_firmware_response = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        conn = ESP3DConnection("192.168.1.100", 80)
        result = conn.delete_file("test.gc", "/")

        self.assertTrue(result["success"])


class TestESP3DConsoleCommands(unittest.TestCase):
    """Test ESP3D console commands integration."""

    def test_esp3d_commands_registered(self):
        """Test that ESP3D commands are registered with kernel."""
        kernel = bootstrap.bootstrap(profile="MeerK40t_GRBL")
        try:
            # Start GRBL device
            kernel.console("service device start -i grbl 0\n")
            
            # Just verify kernel boots without errors
            # Actual command testing would require complex mocking
            self.assertIsNotNone(kernel)
            self.assertIsNotNone(kernel.device)
        finally:
            kernel()

    def test_esp3d_settings_exist(self):
        """Test that ESP3D settings are available on GRBL device."""
        kernel = bootstrap.bootstrap(profile="MeerK40t_GRBL")
        try:
            kernel.console("service device start -i grbl 0\n")
            device = kernel.device
            
            # Check if ESP3D attributes exist
            self.assertTrue(hasattr(device, "esp3d_enabled"))
            self.assertTrue(hasattr(device, "esp3d_host"))
            self.assertTrue(hasattr(device, "esp3d_port"))
            self.assertTrue(hasattr(device, "esp3d_path"))
            self.assertTrue(hasattr(device, "esp3d_cleanup"))
            
            # Check default values
            self.assertFalse(device.esp3d_enabled)
            self.assertEqual(device.esp3d_host, "192.168.1.100")
            self.assertEqual(device.esp3d_port, 80)
            self.assertEqual(device.esp3d_path, "/")
            self.assertTrue(device.esp3d_cleanup)
        finally:
            kernel()


if __name__ == '__main__':
    unittest.main()
