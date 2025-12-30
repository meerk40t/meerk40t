"""
ESP3D Emulator Server

A simple HTTP server that emulates ESP3D-WEBUI API for testing purposes.
Provides endpoints for connection testing, file upload, SD card management, and file execution.

Usage:
    python -m meerk40t.grbl.esp3d_emulator [--port PORT] [--host HOST]
"""

import argparse
import json
import os
import tempfile
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import cgi


class ESP3DEmulator(BaseHTTPRequestHandler):
    """Emulates ESP3D-WEBUI HTTP API endpoints."""
    
    # Simulated SD card storage
    sd_files = {}
    sd_total = 2 * 1024 * 1024 * 1024  # 2 GB
    sd_used = 0
    
    # Execution state
    execution_state = "idle"  # idle, running, paused
    current_file = None
    
    def log_message(self, format, *args):
        """Override to add timestamps to logs."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")
    
    def send_json_response(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_text_response(self, text, status=200):
        """Send text response."""
        self.send_response(status)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(text.encode())
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # Command endpoint
        if path == '/command':
            self.handle_command(params)
        
        # SD files endpoint
        elif path == '/sdfiles':
            action = params.get('action', [None])[0]
            if action == 'delete':
                self.handle_delete_file(params)
            else:
                self.handle_list_files(params)
        
        # Root page
        elif path == '/':
            self.handle_root()
        
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Login endpoint
        if path == '/login':
            self.handle_login()
        
        # Upload endpoint
        elif path == '/sdfiles':
            self.handle_upload()
        
        else:
            self.send_error(404, "Not Found")
    
    def handle_root(self):
        """Handle root page request."""
        state_color = {
            "idle": "#e8f5e9",
            "running": "#fff3e0",
            "paused": "#ffebee"
        }.get(self.execution_state, "#e8f5e9")
        
        current_file_info = f"<div class='info'>Current file: {self.current_file}</div>" if self.current_file else ""
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ESP3D-WEBUI Emulator</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                .status {{ background: {state_color}; padding: 20px; border-radius: 5px; }}
                .info {{ margin: 10px 0; }}
                .command {{ background: #f5f5f5; padding: 10px; border-radius: 3px; margin: 5px 0; }}
            </style>
        </head>
        <body>
            <h1>ESP3D-WEBUI Emulator</h1>
            <div class="status">
                <h2>Server Status: Running</h2>
                <div class="info">Emulating ESP3D-WEBUI API v3.0</div>
                <div class="info">SD Card: {num_files} files, {used_mb:.2f} MB used / {total_mb:.2f} MB total</div>
                <div class="info">Execution State: <strong>{exec_state}</strong></div>
                {current_file}
            </div>
            <h3>Available Endpoints:</h3>
            <ul>
                <li>GET /command?cmd=[ESP800] - Get system info</li>
                <li>GET /command?cmd=? - Query current state (GRBL status)</li>
                <li>GET /sdfiles?path=/ - List SD card files</li>
                <li>POST /sdfiles - Upload file</li>
                <li>GET /command?cmd=[ESP700]/sd/file.gc - Execute file</li>
                <li>GET /command?cmd=! - Pause execution</li>
                <li>GET /command?cmd=~ - Resume execution</li>
                <li>GET /command?cmd=\\x18 - Stop/Reset execution</li>
            </ul>
            <h3>Control Commands:</h3>
            <div class="command">Status: <code>curl "http://localhost:8080/command?cmd=?"</code></div>
            <div class="command">Pause: <code>curl "http://localhost:8080/command?cmd=!"</code></div>
            <div class="command">Resume: <code>curl "http://localhost:8080/command?cmd=~"</code></div>
            <div class="command">Stop: <code>curl "http://localhost:8080/command?cmd=%5Cx18"</code></div>
        </body>
        </html>
        """.format(
            state_color=state_color,
            num_files=len(self.sd_files),
            used_mb=self.sd_used / (1024 * 1024),
            total_mb=self.sd_total / (1024 * 1024),
            exec_state=self.execution_state.upper(),
            current_file=current_file_info
        )
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_login(self):
        """Handle login request."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        self.log_message("Login attempt")
        
        # Always accept login for emulator
        response = {
            "status": "ok",
            "authentication": "Enabled",
            "session_id": "emulator_session_123"
        }
        self.send_json_response(response)
    
    def handle_command(self, params):
        """Handle ESP3D command requests."""
        cmd = params.get('cmd', [''])[0]
        
        self.log_message(f"Command: {cmd}")
        
        # [ESP800] - Get system info
        if cmd.startswith('[ESP800]'):
            response = f"ESP3D Emulator v1.0 | FW: 3.0.0-alpha | Chip: ESP32 | State: {self.execution_state}"
            self.send_text_response(response)
        
        # [ESP700] - Execute file
        elif cmd.startswith('[ESP700]'):
            filename = cmd.replace('[ESP700]', '').strip()
            if filename.startswith('/sd/'):
                filename = filename[4:]
            
            if filename in self.sd_files:
                self.log_message(f"Executing file: {filename}")
                self.execution_state = "running"
                self.current_file = filename
                response = f"ok\nExecuting: {filename}\nState: {self.execution_state}"
                self.send_text_response(response)
            else:
                self.send_text_response(f"Error: File not found: {filename}", 404)
        
        # Pause command (!)
        elif cmd == '!':
            if self.execution_state == "running":
                self.execution_state = "paused"
                self.log_message(f"Paused execution (file: {self.current_file})")
                response = f"ok\nPaused\nFile: {self.current_file}\nState: {self.execution_state}"
            elif self.execution_state == "paused":
                response = f"ok\nAlready paused\nFile: {self.current_file}\nState: {self.execution_state}"
            else:
                response = "ok\nNothing to pause\nState: idle"
            self.send_text_response(response)
        
        # Resume command (~)
        elif cmd == '~':
            if self.execution_state == "paused":
                self.execution_state = "running"
                self.log_message(f"Resumed execution (file: {self.current_file})")
                response = f"ok\nResumed\nFile: {self.current_file}\nState: {self.execution_state}"
            elif self.execution_state == "running":
                response = f"ok\nAlready running\nFile: {self.current_file}\nState: {self.execution_state}"
            else:
                response = "ok\nNothing to resume\nState: idle"
            self.send_text_response(response)
        
        # Stop/Reset command (Ctrl-X / \x18)
        elif cmd == '\x18' or cmd == '^X':
            if self.execution_state in ["running", "paused"]:
                old_file = self.current_file
                self.execution_state = "idle"
                self.current_file = None
                self.log_message(f"Emergency stop (was: {old_file})")
                response = f"ok\nEmergency stop\nStopped file: {old_file}\nState: {self.execution_state}"
            else:
                response = "ok\nAlready stopped\nState: idle"
            self.send_text_response(response)
        
        # Status query command (?)
        elif cmd == '?':
            # Return GRBL-style status report
            grbl_state = {
                "idle": "Idle",
                "running": "Run",
                "paused": "Hold"
            }.get(self.execution_state, "Idle")
            
            # Format: <State|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000>
            # Simplified for emulator - just report state
            response = f"<{grbl_state}|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000|FS:0,0>\n"
            if self.current_file:
                response += f"File: {self.current_file}\n"
            response += "ok"
            self.send_text_response(response)
        
        else:
            response = "ok"
            self.send_text_response(response)
    
    def handle_list_files(self, params):
        """Handle SD card file listing."""
        path = params.get('path', ['/'])[0]
        
        self.log_message(f"Listing files in: {path}")
        
        # Build file list
        files = []
        for filename, content in self.sd_files.items():
            size_bytes = len(content)
            size_str = self.format_size(size_bytes)
            
            files.append({
                "name": filename,
                "size": size_str,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Calculate space
        used_str = self.format_size(self.sd_used)
        total_str = self.format_size(self.sd_total)
        occupation = int((self.sd_used / self.sd_total) * 100) if self.sd_total > 0 else 0
        
        response = {
            "files": files,
            "path": path,
            "total": total_str,
            "used": used_str,
            "occupation": str(occupation),
            "status": "ok"
        }
        
        self.send_json_response(response)
    
    def handle_upload(self):
        """Handle file upload."""
        content_type = self.headers['Content-Type']
        
        if 'multipart/form-data' not in content_type:
            self.send_error(400, "Expected multipart/form-data")
            return
        
        # Parse multipart form data
        content_length = int(self.headers['Content-Length'])
        
        # Create a file-like object for cgi
        class RequestFile:
            def __init__(self, rfile, length):
                self.rfile = rfile
                self.length = length
                self.read_bytes = 0
            
            def read(self, size=-1):
                if size == -1:
                    size = self.length - self.read_bytes
                data = self.rfile.read(min(size, self.length - self.read_bytes))
                self.read_bytes += len(data)
                return data
            
            def readline(self, size=-1):
                return self.rfile.readline(size)
        
        # Parse form data
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': str(content_length),
        }
        
        form = cgi.FieldStorage(
            fp=RequestFile(self.rfile, content_length),
            headers=self.headers,
            environ=environ
        )
        
        # Get uploaded file
        if 'myfiles' in form:
            file_item = form['myfiles']
            if file_item.file:
                filename = file_item.filename
                file_data = file_item.file.read()
                
                # Store file
                self.sd_files[filename] = file_data
                self.sd_used += len(file_data)
                
                self.log_message(f"File uploaded: {filename} ({len(file_data)} bytes)")
                
                response = {
                    "status": "ok",
                    "message": f"File uploaded: {filename}"
                }
                self.send_json_response(response)
                return
        
        self.send_error(400, "No file uploaded")
    
    def handle_delete_file(self, params):
        """Handle file deletion."""
        filename = params.get('filename', [''])[0]
        
        if filename in self.sd_files:
            file_size = len(self.sd_files[filename])
            del self.sd_files[filename]
            self.sd_used -= file_size
            
            self.log_message(f"File deleted: {filename}")
            
            response = {
                "status": "ok",
                "message": f"File deleted: {filename}"
            }
            self.send_json_response(response)
        else:
            self.send_json_response({
                "status": "error",
                "message": f"File not found: {filename}"
            }, 404)
    
    @staticmethod
    def format_size(size_bytes):
        """Format size in bytes to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def run_emulator(host='localhost', port=8080):
    """Run the ESP3D emulator server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, ESP3DEmulator)
    
    print("=" * 60)
    print("ESP3D-WEBUI Emulator Server")
    print("=" * 60)
    print(f"Server running at: http://{host}:{port}")
    print(f"Configure MeerK40t ESP3D settings:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ESP3D-WEBUI Emulator Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on (default: 8080)')
    
    args = parser.parse_args()
    
    run_emulator(host=args.host, port=args.port)
