import html as html_module
import logging
import mimetypes
import socket
import sys
import threading

# Workaround for macOS permission errors with mimetypes.init()
# On macOS, mimetypes.init() tries to read /etc/apache2/ which may require special permissions.
# The problem: mimetypes.add_type() internally calls init() if not already initialized.
# Solution: Mark the module as initialized before adding types, preventing filesystem access.
# The module's hardcoded knownfiles will be skipped, but we add the types we need manually.
if not mimetypes.inited:
    # Mark as initialized to prevent init() from being called and reading system files
    mimetypes.inited = True
    mimetypes._db = mimetypes.MimeTypes()

    # Add common web types we need
    _common_types = {
        ".html": "text/html",
        ".htm": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".txt": "text/plain",
        ".xml": "application/xml",
        ".pdf": "application/pdf",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".eot": "application/vnd.ms-fontobject",
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".webp": "image/webp",
        ".zip": "application/zip",
    }
    for ext, mime_type in _common_types.items():
        mimetypes.add_type(mime_type, ext)

from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from math import isinf
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote_plus, urlparse

from meerk40t.kernel import Module

# ThreadingHTTPServer was added in Python 3.7
# For Python 3.6 compatibility, create it manually
if sys.version_info >= (3, 7):
    from http.server import ThreadingHTTPServer
else:

    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        """Threaded HTTP server for Python 3.6 compatibility."""

        daemon_threads = True


def plugin(kernel, lifecycle: Optional[str] = None) -> None:
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("module/WebServer", WebServer)


class WebRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for the web server.
    Handles GET and POST requests with proper HTTP/1.1 protocol.
    """

    def _get_server_instance(self) -> Optional["WebServer"]:
        """
        Safely retrieve the associated WebServer instance from the HTTPServer.
        This keeps server state scoped per HTTPServer instead of globally.
        """
        # self.server is the HTTPServer / ThreadingHTTPServer instance
        return getattr(self.server, "server_instance", None)

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use kernel's logging instead of stderr"""
        # Only log non-GET requests to avoid spam from auto-refresh
        if self.command != "GET":
            server_instance = self._get_server_instance()
            if server_instance and server_instance.events_channel:
                server_instance.events_channel(
                    f"{self.address_string()} - {format % args}"
                )

    def log_error(self, format: str, *args: Any) -> None:
        """Override to use kernel's logging for errors"""
        server_instance = self._get_server_instance()
        if server_instance and server_instance.events_channel:
            server_instance.events_channel(
                f"ERROR: {self.address_string()} - {format % args}"
            )

    def send_response_headers(
        self, content_type: str = "text/html", content_length: int = 0
    ) -> None:
        """Send common HTTP headers"""
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Connection", "close")
        self.send_header("Server", "MeerK40t-WebServer")
        self.send_header(
            "Date", datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        )
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()

    def send_html_response(self, html_content: str, status_code: int = 200) -> None:
        """Send HTML response with proper headers"""
        content = html_content.encode("utf-8")
        self.send_response(status_code)
        self.send_response_headers("text/html; charset=utf-8", len(content))
        self.wfile.write(content)

    def send_error_page(self, status_code: int, message: str) -> None:
        """Send a formatted error page"""
        # HTML-escape message to prevent XSS
        safe_message = html_module.escape(message, quote=True)
        html_string = f"""<!DOCTYPE html>
<html>
<head><title>Error {status_code}</title></head>
<body>
<h1>Error {status_code}</h1>
<p>{safe_message}</p>
</body>
</html>"""
        self.send_html_response(html_string, status_code)

    def do_GET(self) -> None:
        """Handle GET requests"""
        try:
            server_instance = self._get_server_instance()
            if server_instance is None:
                self.send_error_page(500, "Server not properly initialized")
                return

            # Parse URL and query parameters
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)

            # Check for command in query
            command = None
            if "cmd" in query_params:
                command = query_params["cmd"][0]

            # Generate response
            html_content = server_instance.build_html_page(command)
            self.send_html_response(html_content)

        except Exception as e:
            self.log_error(f"Error in GET: {e}")
            self.send_error_page(500, f"Internal Server Error: {str(e)}")

    def do_POST(self) -> None:
        """Handle POST requests"""
        try:
            server_instance = self._get_server_instance()
            if server_instance is None:
                self.send_error_page(500, "Server not properly initialized")
                return

            # Read POST data
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")

            # Parse POST parameters
            post_params = parse_qs(post_data)

            # Check for job command first
            if "job_cmd" in post_params:
                job_cmd = post_params["job_cmd"][0]
                try:
                    job_idx_str, operation = job_cmd.split(":", 1)
                    job_idx = int(job_idx_str)
                    result = server_instance.handle_job_command(job_idx, operation)
                    # Display result as message without executing as command
                    html_content = server_instance.build_html_page(message=result)
                    self.send_html_response(html_content)
                except (ValueError, IndexError) as e:
                    error_msg = f"Error: Invalid job command format: {str(e)}"
                    html_content = server_instance.build_html_page(message=error_msg)
                    self.send_html_response(html_content)
                return

            # Check for regular console command
            command = None
            if "cmd" in post_params:
                command = post_params["cmd"][0]

            # Generate response
            html_content = server_instance.build_html_page(command)
            self.send_html_response(html_content)

        except Exception as e:
            self.log_error(f"Error in POST: {e}")
            self.send_error_page(500, f"Internal Server Error: {str(e)}")


class WebServer(Module):
    """
    WebServer opens up a localhost HTTP server and waits for connections.
    Uses ThreadingHTTPServer for concurrent request handling.
    """

    def __init__(
        self, context, name: str, port: int = 23, bind_address: str = "127.0.0.1"
    ) -> None:
        """
        Web Server initialization.

        @param context: Context at which this module is attached.
        @param name: Name of this module
        @param port: Port being used for the server.
        @param bind_address: Address to bind to (default: localhost only for security)
        """
        Module.__init__(self, context, name)
        self.port = port
        self.bind_address = bind_address

        self.httpd = None
        self.events_channel = self.context.channel(f"server-web-{port}")
        self.data_channel = self.context.channel(f"data-web-{port}")

        # Store job references for operations
        self._job_map = {}  # Maps display_idx to (device, job_object, spooler)
        self._job_map_lock = threading.Lock()

        # Console output buffer (stores last 100 messages)
        self._console_buffer = []
        self._console_max_lines = 100
        self._console_buffer_lock = threading.Lock()

        # Watch regular console channel for command output
        self.console_channel = self.context.channel("console")
        self.console_channel.watch(self._console_watcher)

        # Create dedicated channel for web server debug messages (internal logging only, not displayed)
        self.debug_channel = self.context.channel(f"web-debug-{port}")

        # Set up handover for command execution
        self.handover = None
        root = self.context.root
        for result in root.find("gui/handover"):
            # Do we have a thread handover routine?
            if result is not None:
                self.handover, _path, suffix_path = result
                break

        # Start server in thread
        self.context.threaded(self.run_server, thread_name=f"web-{port}", daemon=True)

    def _console_watcher(self, message: Any) -> None:
        """Watch console channel and buffer messages"""
        with self._console_buffer_lock:
            # Add message to buffer
            self._console_buffer.append(str(message))

            # Keep buffer at max size
            if len(self._console_buffer) > self._console_max_lines:
                self._console_buffer.pop(0)

    def _ansi_to_html(self, text):
        """Convert ANSI escape codes to HTML formatting"""
        import re

        # ANSI color mapping
        ansi_colors = {
            "30": "#000000",
            "31": "#cd3131",
            "32": "#0dbc79",
            "33": "#e5e510",
            "34": "#2472c8",
            "35": "#bc3fbc",
            "36": "#11a8cd",
            "37": "#e5e5e5",
            "90": "#666666",
            "91": "#f14c4c",
            "92": "#23d18b",
            "93": "#f5f543",
            "94": "#3b8eea",
            "95": "#d670d6",
            "96": "#29b8db",
            "97": "#ffffff",
        }

        # Remove ANSI codes and convert to HTML
        result = []
        current_color = None
        is_bold = False
        span_open = False

        # Split by ANSI escape sequences
        parts = re.split(r"(\x1b\[[0-9;]*m)", text)

        for part in parts:
            if part.startswith("\x1b["):
                # Parse ANSI code
                codes = part[2:-1].split(";")
                for code in codes:
                    if code == "0" or code == "":
                        # Reset - close any open span
                        if span_open:
                            result.append("</span>")
                            span_open = False
                        current_color = None
                        is_bold = False
                    elif code == "1":
                        # Bold
                        is_bold = True
                    elif code in ansi_colors:
                        # Foreground color
                        current_color = ansi_colors[code]

                # Close previous span if open
                if span_open:
                    result.append("</span>")
                    span_open = False

                # Open new span with current styles
                if current_color or is_bold:
                    styles = []
                    if current_color:
                        styles.append(f"color: {current_color}")
                    if is_bold:
                        styles.append("font-weight: bold")
                    result.append(f'<span style="{"; ".join(styles)}">')
                    span_open = True
            else:
                # Regular text - escape HTML entities
                escaped = (
                    part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                result.append(escaped)

        # Always close any open span at the end of the line
        if span_open:
            result.append("</span>")

        return "".join(result)

    def handle_job_command(self, job_idx: int, operation: str) -> str:
        """
        Handle job-specific operations like stop, remove, pause, resume

        @param job_idx: Display index of the job
        @param operation: Operation to perform (stop_job, remove_job, pause_device, resume_device)
        @return: Success message or error
        """
        with self._job_map_lock:
            if job_idx not in self._job_map:
                return f"Error: Job {job_idx} not found"

            device, job, spooler = self._job_map[job_idx]

        try:
            if operation == "stop_job":
                # Stop the specific job
                if hasattr(job, "stop"):
                    job.stop()
                    return f"Stopped job {job_idx}"
                else:
                    return f"Job {job_idx} cannot be stopped"

            elif operation == "remove_job":
                # Remove job from spooler queue
                spooler.remove(job)
                return f"Removed job {job_idx} from queue"

            elif operation == "pause_device":
                # Pause the device (affects all jobs)
                if hasattr(device.driver, "pause"):
                    device.driver.pause()
                    return f"Paused device {device.label}"
                else:
                    return f"Device {device.label} cannot be paused"

            elif operation == "resume_device":
                # Resume the device
                if hasattr(device.driver, "resume"):
                    device.driver.resume()
                    return f"Resumed device {device.label}"
                elif hasattr(device.driver, "pause"):
                    # Some drivers use pause() to toggle - check if already paused
                    if getattr(device.driver, "paused", False):
                        device.driver.pause()  # Toggle from paused to running
                        return f"Resumed device {device.label}"
                    else:
                        return f"Device {device.label} is not paused"
                else:
                    return f"Device {device.label} cannot be resumed"

            else:
                return f"Unknown operation: {operation}"

        except Exception as e:
            return f"Error: {str(e)}"

    def stop(self) -> None:
        """Stop the server"""
        self.state = "terminate"
        if self.httpd:
            self.httpd.shutdown()

    def module_close(self, *args: Any, **kwargs: Any) -> None:
        """Clean up when module closes"""
        _ = self.context._
        self.events_channel(_("Shutting down server."))
        self.state = "terminate"

        # Unwatch console channel
        if hasattr(self, "console_channel"):
            try:
                self.console_channel.unwatch(self._console_watcher)
            except:
                pass

        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except:
                pass
            self.httpd = None

    def send_command(self, command: str) -> None:
        """Send command to kernel for execution"""
        if command:
            # Log to web debug channel
            self.debug_channel(f"[WEB CMD] {command}")

            if self.handover is None:
                self.context(f"{command}\n")
            else:
                self.handover(command)

    def _get_html_styles(self) -> str:
        """Generate CSS styles for the web interface"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 30px;
        }
        .section h2 {
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        .device-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .device-info strong {
            color: #667eea;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 0.9em;
        }
        table th {
            background: #667eea;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
        }
        table td {
            padding: 10px 8px;
            border-bottom: 1px solid #e9ecef;
        }
        table tr:hover {
            background: #f8f9fa;
        }
        table tr:last-child td {
            border-bottom: none;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
        .command-form {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 600;
        }
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
            transition: border-color 0.3s;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:active {
            transform: translateY(0);
        }
        .alert {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .alert-info {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .alert code {
            background: rgba(0,0,0,0.1);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9em;
        }
        .auto-refresh {
            background: #e7f3ff;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            margin-bottom: 20px;
            color: #0066cc;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .refresh-status {
            font-weight: 600;
        }
        .refresh-controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .refresh-btn {
            background: #0066cc;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover {
            background: #0052a3;
        }
        .pause-icon {
            cursor: pointer;
            font-size: 18px;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-running { background: #28a745; color: white; }
        .status-queued { background: #ffc107; color: #333; }
        .status-paused { background: #6c757d; color: white; }
        .status-error { background: #dc3545; color: white; }
        .status-idle { background: #e9ecef; color: #6c757d; }
        .progress-bar-container {
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 4px;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }
        .job-controls {
            display: flex;
            gap: 5px;
            justify-content: center;
        }
        .job-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.2s;
        }
        .job-btn:hover { background: #5568d3; }
        .job-btn.danger { background: #dc3545; }
        .job-btn.danger:hover { background: #c82333; }
        .job-btn.warning { background: #ffc107; color: #333; }
        .job-btn.warning:hover { background: #e0a800; }
        .device-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 15px;
            border-radius: 5px;
            background: #f8f9fa;
            border: 2px solid #e9ecef;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .status-dot.idle { background: #6c757d; animation: none; }
        .status-dot.busy { background: #28a745; }
        .status-dot.error { background: #dc3545; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .command-history {
            margin-bottom: 10px;
        }
        .command-history select {
            width: 100%;
            padding: 8px;
            border: 2px solid #e9ecef;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        }
        .toast {
            background: white;
            padding: 15px 20px;
            margin-bottom: 10px;
            border-radius: 5px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-left: 4px solid #667eea;
            min-width: 300px;
            animation: slideIn 0.3s ease;
        }
        .toast.success { border-left-color: #28a745; }
        .toast.error { border-left-color: #dc3545; }
        .toast.warning { border-left-color: #ffc107; }
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .copy-btn {
            background: transparent;
            border: 1px solid #667eea;
            color: #667eea;
            padding: 3px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px;
            margin-left: 8px;
        }
        .copy-btn:hover {
            background: #667eea;
            color: white;
        }
        .keyboard-hint {
            font-size: 0.85em;
            color: #6c757d;
            margin-top: 5px;
        }
        .console-output {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #333;
        }
        .console-output::-webkit-scrollbar {
            width: 8px;
        }
        .console-output::-webkit-scrollbar-track {
            background: #2d2d2d;
        }
        .console-output::-webkit-scrollbar-thumb {
            background: #555;
            border-radius: 4px;
        }
        .console-output::-webkit-scrollbar-thumb:hover {
            background: #777;
        }
        """

    def _get_html_scripts(self) -> str:
        """Generate JavaScript code for the web interface"""
        return """
        let refreshInterval = null;
        let isPaused = false;
        let countdown = 5;
        let commandHistory = JSON.parse(localStorage.getItem('commandHistory') || '[]');

        function updateCountdown() {
            if (!isPaused) {
                countdown--;
                if (countdown <= 0) {
                    refreshJobTable();
                    countdown = 5;
                }
                document.getElementById('countdown').textContent = countdown;
            }
        }

        function refreshJobTable() {
            fetch(window.location.href)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newJobsSection = doc.querySelector('#jobs-section');
                    const currentJobsSection = document.querySelector('#jobs-section');
                    if (newJobsSection && currentJobsSection) {
                        currentJobsSection.innerHTML = newJobsSection.innerHTML;
                    }
                    // Update console output
                    const newConsoleOutput = doc.getElementById('console-output');
                    if (newConsoleOutput) {
                        const consoleDiv = document.getElementById('console-output');
                        const wasScrolledToBottom = Math.abs(consoleDiv.scrollHeight - consoleDiv.scrollTop - consoleDiv.clientHeight) < 5;
                        consoleDiv.innerHTML = newConsoleOutput.innerHTML;
                        // Auto-scroll to bottom if it was already at bottom
                        if (wasScrolledToBottom) {
                            consoleDiv.scrollTop = consoleDiv.scrollHeight;
                        }
                    }
                })
                .catch(err => console.error('Refresh failed:', err));
        }

        function togglePause() {
            isPaused = !isPaused;
            const pauseBtn = document.getElementById('pause-btn');
            const status = document.getElementById('refresh-status');
            if (isPaused) {
                pauseBtn.textContent = '▶';
                pauseBtn.title = 'Resume auto-refresh';
                status.textContent = 'Auto-refresh paused';
            } else {
                pauseBtn.textContent = '⏸';
                pauseBtn.title = 'Pause auto-refresh';
                status.textContent = 'Auto-refresh active';
                countdown = 5;
            }
        }

        function manualRefresh() {
            refreshJobTable();
            countdown = 5;
            document.getElementById('countdown').textContent = countdown;
        }

        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            container.appendChild(toast);

            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => container.removeChild(toast), 300);
            }, 3000);
        }

        function addToHistory(command) {
            if (command && !commandHistory.includes(command)) {
                commandHistory.unshift(command);
                if (commandHistory.length > 10) commandHistory.pop();
                localStorage.setItem('commandHistory', JSON.stringify(commandHistory));
                updateHistoryDropdown();
            }
        }

        function updateHistoryDropdown() {
            const select = document.getElementById('history-select');
            if (select) {
                select.innerHTML = '<option value="">-- Recent Commands --</option>';
                commandHistory.forEach(cmd => {
                    const option = document.createElement('option');
                    option.value = cmd;
                    option.textContent = cmd.substring(0, 50) + (cmd.length > 50 ? '...' : '');
                    select.appendChild(option);
                });
            }
        }

        function loadHistoryCommand() {
            const select = document.getElementById('history-select');
            const textarea = document.getElementById('cmd');
            if (select && textarea && select.value) {
                textarea.value = select.value;
                textarea.focus();
            }
        }

        function sendJobCommand(jobId, operation) {
            fetch(window.location.href, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `job_cmd=${encodeURIComponent(jobId + ':' + operation)}`
            })
            .then(() => {
                showToast(`Command sent: ${operation}`, 'success');
                refreshJobTable();
            })
            .catch(err => showToast('Command failed', 'error'));
        }

        function sendDeviceCommand(command) {
            fetch(window.location.href, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `cmd=${encodeURIComponent(command)}`
            })
            .then(() => {
                showToast(`Device command: ${command}`, 'success');
                // Refresh entire page to update device state
                setTimeout(() => { location.reload(); }, 500);
            })
            .catch(err => showToast('Command failed', 'error'));
        }

        window.addEventListener('load', function() {
            // Start countdown timer
            refreshInterval = setInterval(updateCountdown, 1000);

            // Initialize history dropdown
            updateHistoryDropdown();

            // Pause auto-refresh when user is typing
            const textarea = document.getElementById('cmd');
            if (textarea) {
                textarea.addEventListener('focus', function() {
                    if (!isPaused) {
                        togglePause();
                    }
                });

                // Keyboard shortcuts
                textarea.addEventListener('keydown', function(e) {
                    // Ctrl+Enter to submit
                    if (e.ctrlKey && e.key === 'Enter') {
                        e.preventDefault();
                        const form = textarea.closest('form');
                        if (form) {
                            const cmd = textarea.value.trim();
                            if (cmd) addToHistory(cmd);
                            form.submit();
                        }
                    }
                    // Escape to clear
                    if (e.key === 'Escape') {
                        textarea.value = '';
                    }
                });
            }

            // Add submit listener to track commands
            const form = document.querySelector('form');
            if (form) {
                form.addEventListener('submit', function(e) {
                    const cmd = textarea.value.trim();
                    if (cmd) addToHistory(cmd);
                });
            }
        });
        """

    def _get_html_body(
        self,
        command_result: str,
        device_controls: str,
        spooler_html: str,
        console_output: str,
    ) -> str:
        """Generate the HTML body content

        @param command_result: HTML for command result/message display
        @param device_controls: HTML for device control buttons
        @param spooler_html: HTML for spooler table
        @param console_output: HTML for console output
        @return: Complete body HTML
        """
        return f"""
    <div class="toast-container" id="toast-container"></div>

    <div class="container">
        <div class="header">
            <h1>{self.context.kernel.name} {self.context.kernel.version}</h1>
            <p>Web Console Interface</p>
        </div>

        <div class="content">
            <div class="auto-refresh">
                <span class="refresh-status" id="refresh-status">Auto-refresh active</span>
                <div class="refresh-controls">
                    <span>Next refresh in: <span id="countdown">5</span>s</span>
                    <button class="refresh-btn" onclick="manualRefresh()" title="Refresh now">↻</button>
                    <span class="pause-icon" id="pause-btn" onclick="togglePause()" title="Pause auto-refresh">⏸</span>
                </div>
            </div>

            {command_result}

            <div class="section">
                <h2>Active Device</h2>
                <div class="device-info">
                    <div class="device-status">
                        <span class="status-dot busy" id="device-status-dot"></span>
                        <strong>{self.context.device.label}</strong>
                    </div>
                    <div class="job-controls" style="margin-top: 10px;">
                        {device_controls}
                    </div>
                </div>
            </div>

            <div class="section" id="jobs-section">
                <h2>Current Jobs</h2>
                {spooler_html}
            </div>

            <div class="section">
                <h2>Console Commands</h2>
                <div class="command-form">
                    <form method="post" action="/">
                        <div class="command-history">
                            <select id="history-select" onchange="loadHistoryCommand()">
                                <option value="">-- Recent Commands --</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="cmd">Enter Command:</label>
                            <textarea id="cmd" name="cmd" rows="5" placeholder="Type your command here (e.g., help, status, circle 1in 1in 0.5in)"></textarea>
                            <div class="keyboard-hint">💡 Tip: Press Ctrl+Enter to submit, ESC to clear</div>
                        </div>
                        <button type="submit" class="btn">Execute Command</button>
                    </form>
                </div>
            </div>

            <div class="section">
                <h2>Console Output</h2>
                <div class="console-output" id="console-output">{console_output}</div>
            </div>
        </div>

        <div class="footer">
            Powered by MeerK40t &copy; 2025 | Server running on port {self.port}
        </div>
    </div>
        """

    def build_html_page(
        self, command: Optional[str] = None, message: Optional[str] = None
    ) -> str:
        """
        Build the main HTML page with spooler info and command interface.

        @param command: Command to execute and display result
        @param message: Message to display without executing (for feedback)
        @return: Complete HTML page as string
        """
        # Execute command if provided
        command_result = ""
        if command:
            self.send_command(command)
            # HTML-escape command to prevent XSS
            safe_command = html_module.escape(command, quote=True)
            command_result = f"<div class='alert alert-success'>Command executed: <code>{safe_command}</code></div>"
        elif message:
            # Display message without executing, HTML-escape to prevent XSS
            safe_message = html_module.escape(message, quote=True)
            command_result = f"<div class='alert alert-info'>{safe_message}</div>"

        # Build components
        spooler_html = self._build_spooler_table()
        device_controls = self._build_device_controls()
        console_output = self._get_console_output()

        # Assemble complete page
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.context.kernel.name} - Web Console</title>
    <style>
{self._get_html_styles()}
    </style>
    <script>
{self._get_html_scripts()}
    </script>
</head>
<body>
{self._get_html_body(command_result, device_controls, spooler_html, console_output)}
</body>
</html>"""
        return html

    def _build_device_controls(self) -> str:
        """Build device control buttons based on driver state"""
        html = ""
        try:
            device = self.context.device
            driver = device.driver

            # Check if driver is paused
            is_paused = getattr(driver, "paused", False)

            if is_paused:
                # Show Resume button
                html += '<button class="job-btn" onclick="sendDeviceCommand(\'resume\')" title="Resume Device">▶ Resume</button>'
            else:
                # Show Pause button
                html += '<button class="job-btn warning" onclick="sendDeviceCommand(\'pause\')" title="Pause Device">⏸ Pause</button>'

            # Always show Stop button
            html += '<button class="job-btn danger" onclick="sendDeviceCommand(\'estop\')" title="Emergency Stop" style="margin-left: 5px;">⏹ Stop</button>'

        except (AttributeError, KeyError):
            # Device or driver not available
            html = '<span style="color: #999;">Device controls unavailable</span>'

        return html

    def _get_console_output(self) -> str:
        """Get recent console output as HTML with ANSI codes converted"""
        with self._console_buffer_lock:
            if not self._console_buffer:
                return "No console output yet..."
            # Return last 50 messages (or all if less)
            recent = self._console_buffer[-50:]
        # Convert each line's ANSI codes to HTML
        html_lines = [self._ansi_to_html(line) for line in recent]
        return "<br>".join(html_lines)

    def _build_spooler_table(self) -> str:
        """Build HTML table for spooler queue"""
        _ = self.context._
        rows = []
        has_jobs = False

        # Clear job map for this render
        with self._job_map_lock:
            self._job_map.clear()

        # Use global counter across all devices to prevent key collisions
        global_job_idx = 0

        available_devices = self.context.kernel.services("device")
        for device in available_devices:
            spooler = device.spooler
            if spooler is None:
                continue

            def _name_str(named_obj):
                try:
                    return named_obj.__name__
                except AttributeError:
                    return str(named_obj)

            for idx, e in enumerate(spooler.queue):
                global_job_idx += 1
                has_jobs = True
                spool_obj = e

                # Store job reference for operations (using global index)
                with self._job_map_lock:
                    self._job_map[global_job_idx] = (device, spool_obj, spooler)

                # Build row data
                row_data = {
                    "idx": global_job_idx,
                    "device": device.label,
                    "name": "",
                    "items": 1,
                    "status": getattr(spool_obj, "status", "-"),
                    "type": "-",
                    "steps": "-",
                    "passes": "-",
                    "priority": "-",
                    "runtime": "-",
                    "estimate": "-",
                }

                # Job name
                if hasattr(spool_obj, "label") and spool_obj.label:
                    row_data["name"] = str(spool_obj.label)
                    # Clean up label if it ends with " items"
                    if row_data["name"].endswith(" items"):
                        cpos = row_data["name"].rfind(":")
                        if cpos > 0:
                            row_data["name"] = row_data["name"][:cpos]
                else:
                    row_data["name"] = _name_str(spool_obj)

                # Items count
                try:
                    if hasattr(spool_obj, "items"):
                        row_data["items"] = len(spool_obj.items)
                    elif hasattr(spool_obj, "elements"):
                        row_data["items"] = len(spool_obj.elements)
                except AttributeError:
                    pass

                # Type
                try:
                    row_data["type"] = str(spool_obj.__class__.__name__)
                except AttributeError:
                    pass

                # Steps
                try:
                    if spool_obj.steps_total == 0:
                        spool_obj.calc_steps()
                    row_data[
                        "steps"
                    ] = f"{spool_obj.steps_done}/{spool_obj.steps_total}"
                except AttributeError:
                    pass

                # Passes
                try:
                    loop = spool_obj.loops_executed or 0
                    total = spool_obj.loops or 1
                    if isinf(total):
                        total = "∞"
                    row_data["passes"] = f"{loop}/{total}"
                except AttributeError:
                    pass

                # Priority
                try:
                    row_data["priority"] = str(spool_obj.priority)
                except AttributeError:
                    pass

                # Runtime
                try:
                    t = spool_obj.elapsed_time()
                    hours, remainder = divmod(t, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    row_data[
                        "runtime"
                    ] = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                except AttributeError:
                    pass

                # Estimate
                try:
                    t = spool_obj.estimate_time()
                    if isinf(t):
                        row_data["estimate"] = "∞"
                    else:
                        hours, remainder = divmod(t, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        row_data[
                            "estimate"
                        ] = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                except AttributeError:
                    pass

                rows.append(row_data)

        if not has_jobs:
            return "<div class='empty-state'>No jobs in queue</div>"

        # Build HTML table with enhanced UI
        html = "<table>\n"
        html += "<thead><tr>"
        html += "<th>#</th><th>Name</th><th>Status</th><th>Progress</th>"
        html += "<th>Items</th><th>Passes</th><th>Runtime</th><th>Estimate</th>"
        html += "<th>Controls</th>"
        html += "</tr></thead>\n<tbody>\n"

        for row in rows:
            # Calculate progress percentage
            try:
                steps_parts = row["steps"].split("/")
                if len(steps_parts) == 2:
                    done = int(steps_parts[0])
                    total = int(steps_parts[1])
                    progress = (done / total * 100) if total > 0 else 0
                else:
                    progress = 0
            except:
                progress = 0

            # Determine status badge class
            status_lower = row["status"].lower()
            if "run" in status_lower or "active" in status_lower:
                badge_class = "status-running"
            elif "queue" in status_lower or "wait" in status_lower:
                badge_class = "status-queued"
            elif "pause" in status_lower:
                badge_class = "status-paused"
            elif "error" in status_lower or "fail" in status_lower:
                badge_class = "status-error"
            else:
                badge_class = "status-idle"

            html += "<tr>"
            html += f"<td><strong>#{row['idx']}</strong></td>"
            html += f"<td>{row['name']}<br><small style='color:#6c757d'>{row['type']}</small></td>"
            html += f"<td><span class='status-badge {badge_class}'>{row['status']}</span></td>"
            html += f"<td>"
            html += f"<div style='min-width:100px'>"
            html += f"<small>{row['steps']}</small>"
            html += f"<div class='progress-bar-container'>"
            html += f"<div class='progress-bar' style='width: {progress:.0f}%'></div>"
            html += f"</div>"
            html += f"</div>"
            html += f"</td>"
            html += f"<td>{row['items']}</td>"
            html += f"<td>{row['passes']}</td>"
            html += f"<td>{row['runtime']}</td>"
            html += f"<td>{row['estimate']}</td>"
            html += f"<td>"
            html += f"<div class='job-controls'>"

            # Show different buttons based on job status
            status_lower = row["status"].lower()
            job_idx = row["idx"]

            if "run" in status_lower or "active" in status_lower:
                # Running job: Show device pause + Stop job
                html += f"<button class='job-btn warning' onclick=\"sendJobCommand({job_idx}, 'pause_device')\" title='Pause Device'>⏸</button>"
                html += f"<button class='job-btn danger' onclick=\"sendJobCommand({job_idx}, 'stop_job')\" title='Stop This Job'>⏹</button>"
            elif "pause" in status_lower:
                # Paused: Resume device + Stop job
                html += f"<button class='job-btn' onclick=\"sendJobCommand({job_idx}, 'resume_device')\" title='Resume Device'>▶</button>"
                html += f"<button class='job-btn danger' onclick=\"sendJobCommand({job_idx}, 'stop_job')\" title='Stop This Job'>⏹</button>"
            elif "queue" in status_lower or "wait" in status_lower:
                # Queued: Remove from queue
                html += f"<button class='job-btn danger' onclick=\"sendJobCommand({job_idx}, 'remove_job')\" title='Remove from Queue'>🗑</button>"
            else:
                # Default: Stop
                html += f"<button class='job-btn danger' onclick=\"sendJobCommand({job_idx}, 'stop_job')\" title='Stop Job'>⏹</button>"

            html += f"</div>"
            html += f"</td>"
            html += "</tr>\n"

        html += "</tbody>\n</table>"
        return html

    def run_server(self) -> None:
        """
        Run the HTTP server in a thread.
        Uses ThreadingHTTPServer for concurrent request handling.
        """
        _ = self.context._

        try:
            # Create threaded HTTP server
            self.httpd = ThreadingHTTPServer(
                (self.bind_address, self.port), WebRequestHandler
            )

            # Attach this WebServer instance to the HTTPServer (not the handler class)
            self.httpd.server_instance = self

            self.events_channel(
                _("Web server listening on {address}:{port}...").format(
                    address=self.bind_address, port=self.port
                )
            )

            # Serve until stopped
            self.httpd.serve_forever()

        except OSError as e:
            self.events_channel(
                _("Could not start web server: {error}").format(error=str(e))
            )
        except Exception as e:
            self.events_channel(f"Web server error: {e}")
        finally:
            if self.httpd:
                self.httpd.server_close()
                self.httpd = None
            self.events_channel(_("Web server stopped."))
