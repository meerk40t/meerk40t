"""
ESP3D Upload Module

Handles HTTP communication with ESP3D-WEBUI for uploading and executing G-code files
on network-connected GRBL lasers with ESP3D firmware.
"""

import os
import re
import tempfile
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
    def _command_request(self, command_text):
        """Send one command via MKS / ESP3D ``/command?commandText=`` API."""
        url = f"{self.base_url}/command"
        params = {"commandText": command_text, "PAGEID": "0"}
        session = self.session if self.session else requests
        response = session.get(url, params=params, timeout=self.timeout)
        return response

    def query_grbl_status(self):
        """
        Query GRBL status report (``?``) over HTTP.

        Returns:
            dict: Parsed status with raw response text
        """
        try:
            response = self._command_request("?")
            body = (response.text or "").strip()
            state = None
            if body.startswith("<") and "|" in body:
                state = body.split("|", 1)[0].lstrip("<").strip()
            return {
                "success": response.status_code < 400,
                "state": state,
                "response": body,
                "status_code": response.status_code,
            }
        except requests.RequestException as e:
            raise ESP3DUploadError(f"Status query failed: {e}")

    def execute_file(self, filename, path="/", verify_started=True):
        """
        Execute a G-code file on the device.

        Args:
            filename: Name of file to execute
            path: Path prefix (ignored for OEM firmwares like MKS DLC32)
            verify_started: After ESP220, poll ``?`` to catch silent SD read failures

        Returns:
            dict: Execution result with success flag and human-readable message
        """
        try:
            if filename.startswith("/"):
                filename = filename[1:]
            command_text = f"[ESP220]/{filename}"

            response = self._command_request(command_text)
            body = (response.text or "").strip()
            parsed = interpret_esp3d_command_response(body, response.status_code)

            if parsed["success"] is False:
                return {
                    "success": False,
                    "message": parsed["message"],
                    "response": body,
                    "status_code": response.status_code,
                }

            if verify_started:
                time.sleep(0.4)
                status = self.query_grbl_status()
                grbl_state = (status.get("state") or "").lower()
                if grbl_state == "run":
                    return {
                        "success": True,
                        "message": f"File running: {filename}",
                        "response": body or status.get("response", ""),
                        "grbl_state": grbl_state,
                    }
                if grbl_state == "alarm":
                    return {
                        "success": False,
                        "message": (
                            "GRBL is in Alarm. Send $X, then $HY and $HX, and try again."
                        ),
                        "response": status.get("response", body),
                        "grbl_state": grbl_state,
                    }
                if grbl_state == "hold":
                    return {
                        "success": True,
                        "message": f"File started (Hold): {filename}",
                        "response": body or status.get("response", ""),
                        "grbl_state": grbl_state,
                    }
                if parsed["success"] is None or grbl_state in ("", "idle"):
                    return {
                        "success": False,
                        "message": (
                            f"File did not start ({filename}). "
                            "Old SD files often use CR-only lines — the board needs LF. "
                            "Delete the file, run esp3d_upload_run -e in the console, "
                            "then Execute the new file."
                        ),
                        "response": body or status.get("response", ""),
                        "grbl_state": grbl_state or "idle",
                    }

            return {
                "success": True,
                "message": parsed["message"] or f"File execution started: {filename}",
                "response": body,
                "status_code": response.status_code,
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
            response = self._command_request(command)
            body = (response.text or "").strip()
            parsed = interpret_esp3d_command_response(body, response.status_code)
            success = parsed["success"] is not False
            return {
                "success": success,
                "message": parsed["message"] or f"Command sent: {command}",
                "response": body,
                "status_code": response.status_code,
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


def interpret_esp3d_command_response(body, status_code):
    """
    Parse MKS / ESP3D ``/command`` HTTP response for ESP220 and other commands.

    Returns dict with ``success`` True / False / None (ambiguous empty body).
    """
    text = (body or "").strip()
    lower = text.lower()

    if status_code >= 500:
        return {
            "success": False,
            "message": text or f"HTTP {status_code} server error",
        }

    if status_code >= 400:
        return {
            "success": False,
            "message": text or f"HTTP {status_code}",
        }

    if lower == "alarm":
        return {
            "success": False,
            "message": "GRBL is in Alarm. Send $X, then $HY and $HX.",
        }

    if lower == "busy":
        return {
            "success": False,
            "message": "GRBL is busy (not Idle). Wait or stop the current job first.",
        }

    if lower.startswith("error"):
        return {"success": False, "message": text}

    for phrase in (
        "cannot stat file",
        "cannot delete",
        "no sd card",
        "sd card busy",
        "missing file name",
    ):
        if phrase in lower:
            return {"success": False, "message": text}

    if lower == "ok":
        return {"success": True, "message": "ok"}

    if text.startswith("<") and "|" in text:
        state = text.split("|", 1)[0].lstrip("<").strip().lower()
        if state == "run":
            return {"success": True, "message": "Job running"}
        if state == "hold":
            return {"success": True, "message": "Job on hold"}
        if state == "alarm":
            return {
                "success": False,
                "message": "GRBL is in Alarm. Send $X, then $HY and $HX.",
            }

    if not text:
        return {"success": None, "message": "Empty response (check GRBL state)"}

    return {"success": True, "message": text}


def normalize_sd_file_entry(entry):
    """
    Normalize one file record from MKS / ESP3D ``/upload`` JSON.

    MKS DLC32 uses ``datetime`` (not ``time``) and may include ``shortname``.
    """
    name = entry.get("name") or entry.get("shortname") or ""
    size = entry.get("size", "-1")
    if size is None:
        size = "-1"
    size = str(size)
    timestamp = entry.get("time") or entry.get("datetime") or ""
    is_dir = size == "-1"
    return {"name": name, "size": size, "time": timestamp, "is_dir": is_dir}


def prepare_sd_gcode_file(path, use_m3=True, force_lf=True, strip_g28=True):
    """
    Patch exported G-code for MKS DLC32 SD execution.

    - LF line endings (board readFileLine splits on \\n only)
    - M3 instead of M4 when use_m3 (CO2 + $32=1 often needs constant PWM)
    - Optional removal of G28 (DLC32: home with $HY / $HX before Execute, not G28)

    Streams line-by-line so large raster exports (100+ MB) do not freeze the UI.
    """
    g28_pat = re.compile(
        rb"^G28(\.\d+)?(\s+[XYZ]-?\d*\.?\d*)*\s*$", re.IGNORECASE
    )
    m4_pat = re.compile(rb"^M4\b", re.IGNORECASE)
    dirname = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(suffix=".sdtmp", dir=dirname)
    os.close(fd)
    try:
        with open(path, "rb") as src, open(tmp_path, "wb") as dst:
            buf = b""
            chunk_size = 8 * 1024 * 1024
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                buf += chunk
                parts = re.split(br"[\r\n]+", buf)
                buf = parts.pop()
                for line in parts:
                    if not line.strip():
                        continue
                    if strip_g28 and g28_pat.match(line):
                        continue
                    if use_m3:
                        line = m4_pat.sub(b"M3", line, count=1)
                    dst.write(line + b"\n")
            if buf.strip():
                line = buf
                if not (strip_g28 and g28_pat.match(line)):
                    if use_m3:
                        line = m4_pat.sub(b"M3", line, count=1)
                    dst.write(line + b"\n")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    return path


def normalize_8_3_filename(name, default_ext="gc"):
    """
    Normalize user input to a valid 8.3 SD filename.

    Adds .gc when no extension is given, strips invalid characters, and truncates.
    Returns None when the result would be empty.
    """
    if not name:
        return None
    name = name.strip()
    if not name:
        return None
    if "." not in name:
        name = f"{name}.{default_ext}"
    base, ext = name.rsplit(".", 1)
    base = re.sub(r"[^A-Za-z0-9_]", "", base)[:8]
    ext = re.sub(r"[^A-Za-z0-9]", "", ext)[:3] or default_ext[:3]
    if not base:
        return None
    return f"{base}.{ext}"


def suggest_esp3d_filename(project_label=None, last=None, extension="gc"):
    """
    Suggest an 8.3 filename for ESP3D SD upload.

    Prefers the last successful upload name, then the project/window label,
    then a short job#### style name.
    """
    extension = extension[:3]
    if last:
        normalized = normalize_8_3_filename(last, default_ext=extension)
        if normalized and validate_filename_8_3(normalized):
            return normalized
    if project_label:
        label = project_label
        if os.sep in label or (len(label) > 1 and label[1] == ":"):
            label = os.path.splitext(os.path.basename(label))[0]
        clean = re.sub(r"[^A-Za-z0-9]", "", label)[:8]
        if clean:
            return f"{clean.lower()}.{extension}"
    return generate_8_3_filename("job", extension)


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
