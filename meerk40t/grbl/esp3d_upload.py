"""
ESP3D Upload Module

Handles HTTP communication with ESP3D-WEBUI for uploading and executing G-code files
on network-connected GRBL lasers with ESP3D firmware.
"""

import os
import time
import random
from urllib.parse import urlencode, quote

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False


class ESP3DUploadError(Exception):
    """Exception raised for ESP3D upload errors."""
    pass


class ESP3DConnection:
    """
    Manages HTTP connection to ESP3D-WEBUI for file upload and execution.
    """

    def __init__(self, host, port=80, username=None, password=None, timeout=30):
        """
        Initialize ESP3D connection.

        Args:
            host: IP address or hostname of ESP3D device
            port: HTTP port (default: 80)
            username: Optional authentication username
            password: Optional authentication password
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.session = None

        if not REQUESTS_AVAILABLE:
            raise ESP3DUploadError(
                "requests library not available. Install with: pip install requests"
            )

    def __enter__(self):
        """Context manager entry."""
        self.session = requests.Session()
        if self.username and self.password:
            self._login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            self.session.close()
        return False

    def _login(self):
        """
        Authenticate with ESP3D device.
        """
        login_url = f"{self.base_url}/login"
        data = {
            "SUBMIT": "yes",
            "PASSWORD": self.password,
            "USER": self.username
        }
        try:
            response = self.session.post(login_url, data=data, timeout=self.timeout)
            response.raise_for_status()
            # ESP3D returns session info or authentication token
            return True
        except requests.RequestException as e:
            raise ESP3DUploadError(f"Authentication failed: {e}")

    def test_connection(self):
        """
        Test connection to ESP3D device.

        Returns:
            dict: Connection status and device info
        """
        try:
            url = f"{self.base_url}/command"
            params = {"cmd": "[ESP800]"}
            
            session = self.session if self.session else requests
            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "Connection successful",
                "response": response.text[:200]  # First 200 chars
            }
        except requests.Timeout:
            return {
                "success": False,
                "message": "Connection timed out. Check host and port."
            }
        except requests.ConnectionError as e:
            return {
                "success": False,
                "message": f"Connection error: Unable to reach host. {e}"
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Connection failed: {e}"
            }


    def get_sd_info(self):
        """
        Get SD card information (space, files, etc.) from OEM ESP3D firmware.
        Uses /upload?path=/&PAGEID=0 endpoint which returns JSON file list.
        """
        try:
            url = f"{self.base_url}/upload"
            params = {"path": "/", "PAGEID": "0"}
            
            session = self.session if self.session else requests
            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            import json
            data = json.loads(response.text)
            
            # Parse size strings to bytes
            def parse_size(size_str):
                """Convert size string like '1.23 MB' to bytes."""
                if not size_str or size_str == "-1":
                    return 0
                    
                units = {
                    "B": 1,
                    "KB": 1024,
                    "MB": 1024 * 1024,
                    "GB": 1024 * 1024 * 1024
                }
                
                parts = size_str.strip().split()
                if len(parts) == 2:
                    try:
                        value = float(parts[0])
                        unit = parts[1]
                        return int(value * units.get(unit, 1))
                    except (ValueError, KeyError):
                        return 0
                return 0
            
            total = parse_size(data.get("total", "0"))
            used = parse_size(data.get("used", "0"))
            
            return {
                "success": True,
                "total": total,
                "used": used,
                "free": total - used,
                "occupation": data.get("occupation", "0"),
                "files": data.get("files", []),
                "path": data.get("path", "/"),
                "status": data.get("status", "unknown")
            }
        except requests.RequestException as e:
            raise ESP3DUploadError(f"Failed to get SD info: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            raise ESP3DUploadError(f"Failed to parse SD info: {e}")

    def list_files(self, path="/"):
        """
        List files on SD card.

        Args:
            path: Directory path to list

        Returns:
            list: List of files with name, size, and time information
        """
        try:
            info = self.get_sd_info()
            return info.get("files", [])
        except ESP3DUploadError:
            raise

    def upload_file(self, local_path, remote_filename, remote_path="/", progress_callback=None):
        """
        Upload a file to ESP3D SD card.

        Args:
            local_path: Path to local file
            remote_filename: Name for file on SD card (8.3 format recommended)
            remote_path: Target directory on SD card (ignored for OEM firmwares like MKS DLC32)
            progress_callback: Optional callback function (not implemented in this version)

        Returns:
            dict: Upload result with success status and message
        """
        if not os.path.exists(local_path):
            raise ESP3DUploadError(f"Local file not found: {local_path}")

        file_size = os.path.getsize(local_path)

        # Use /upload endpoint as required by OEM ESP3D firmwares
        url = f"{self.base_url}/upload"

        try:
            with open(local_path, "rb") as f:
                # Send file using the same format as working curl command
                files_data = {"file": (remote_filename, f, "application/octet-stream")}

                session = self.session if self.session else requests
                response = session.post(
                    url,
                    files=files_data,
                    timeout=self.timeout * 3  # Longer timeout for upload
                )
                response.raise_for_status()

                # If we get here, upload was successful
                return {
                    "success": True,
                    "message": f"File uploaded successfully: {remote_filename}",
                    "filename": remote_filename,
                    "size": file_size
                }

        except requests.RequestException as e:
            raise ESP3DUploadError(f"Upload failed: {e}")
        except IOError as e:
            raise ESP3DUploadError(f"File read error: {e}")

    def delete_file(self, filename, path="/"):
        """
        Delete a file from SD card on OEM ESP3D firmware.
        Uses /upload?path=/&action=delete&filename=...&PAGEID=0
        """
        try:
            url = f"{self.base_url}/upload"
            params = {
                "path": "/",
                "action": "delete",
                "filename": filename,
                "PAGEID": "0"
            }
            
            session = self.session if self.session else requests
            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # Note: Your firmware may not return JSON, but HTTP 200 means success
            return {
                "success": True,
                "message": f"File deleted: {filename}"
            }
        except requests.RequestException as e:
            raise ESP3DUploadError(f"Delete failed: {e}")
    def execute_file(self, filename, path="/"):
        """
        Execute a G-code file on the device.

        Args:
            filename: Name of file to execute
            path: Path prefix (ignored for OEM firmwares like MKS DLC32)

        Returns:
            dict: Execution result
        """
        try:
            # Use the correct prefix and parameter for MKS DLC32 V2.1 firmware
            if filename.startswith("/"):
                filename = filename[1:]
            command_text = f"[ESP220]/{filename}"
            
            url = f"{self.base_url}/command"
            params = {"commandText": command_text}
            
            session = self.session if self.session else requests
            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return {
                "success": True,
                "message": f"File execution started: {filename}",
                "response": response.text
            }
        except requests.RequestException as e:
            raise ESP3DUploadError(f"Execute failed: {e}")

    def send_command(self, command):
        """
        Send a raw command to the ESP3D device.

        Args:
            command: Command string to send

        Returns:
            dict: Command result
        """
        try:
            url = f"{self.base_url}/command"
            params = {"cmd": command}
            
            session = self.session if self.session else requests
            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return {
                "success": True,
                "message": f"Command sent: {command}",
                "response": response.text
            }
        except requests.RequestException as e:
            raise ESP3DUploadError(f"Command failed: {e}")

    def pause(self):
        """
        Pause current execution on the device.

        Returns:
            dict: Pause result
        """
        try:
            # Send pause character (! for GRBL)
            return self.send_command("!")
        except ESP3DUploadError as e:
            raise ESP3DUploadError(f"Pause failed: {e}")

    def resume(self):
        """
        Resume paused execution on the device.

        Returns:
            dict: Resume result
        """
        try:
            # Send resume character (~ for GRBL)
            return self.send_command("~")
        except ESP3DUploadError as e:
            raise ESP3DUploadError(f"Resume failed: {e}")

    def stop(self):
        """
        Emergency stop execution on the device.

        Returns:
            dict: Stop result
        """
        try:
            # Send reset character (Ctrl-X for GRBL)
            return self.send_command("\x18")
        except ESP3DUploadError as e:
            raise ESP3DUploadError(f"Stop failed: {e}")


def generate_8_3_filename(base="file", extension="gc", counter=None):
    """
    Generate a filename following 8.3 convention (8 chars name, 3 chars extension).

    Args:
        base: Base name (will be truncated to fit)
        extension: File extension (3 chars max)
        counter: Optional counter value, or None for timestamp+random-based

    Returns:
        str: Filename in 8.3 format (e.g., "file0001.gc" or "file3a7f.gc")
    """
    extension = extension[:3]  # Max 3 chars for extension
    
    if counter is not None:
        # Use provided counter
        suffix = f"{counter:04d}"  # 4 digit counter
    else:
        # Use timestamp (last 4 digits) + random hex (4 hex digits) for uniqueness
        # This provides ~65k combinations per second instead of repeating every 2.7 hours
        time_part = int(time.time()) % 10000  # Last 4 digits of timestamp
        random_part = random.randint(0, 0xFFFF)  # 16-bit random number
        # Combine: 2 digits time + 2 hex digits random for better distribution
        suffix = f"{time_part % 100:02d}{random_part:04x}"[:4]
    
    # Calculate available space for base name (8 - len(suffix))
    max_base_len = 8 - len(suffix)
    base = base[:max_base_len]
    
    filename = f"{base}{suffix}.{extension}"
    return filename


def validate_filename_8_3(filename):
    """
    Validate if filename follows 8.3 convention.

    Args:
        filename: Filename to validate

    Returns:
        bool: True if valid 8.3 format
    """
    if not filename or "." not in filename:
        return False
    
    parts = filename.rsplit(".", 1)
    if len(parts) != 2:
        return False
    
    name, ext = parts
    
    # Check length constraints
    if len(name) > 8 or len(ext) > 3:
        return False
    
    # Check for invalid characters
    invalid_chars = set(' \\/:*?"<>|')
    if any(c in invalid_chars for c in filename):
        return False
    
    return True
