import socket
from math import isinf
from urllib.parse import unquote_plus

from meerk40t.kernel import Module

def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("module/WebServer", WebServer)


class WebServer(Module):
    """
    WebServer opens up a localhost server and waits. Any connection is given its own handler.
    """

    def __init__(self, context, name, port=23):
        """
        Laser Server init.

        @param context: Context at which this module is attached.
        @param name: Name of this module
        @param port: Port being used for the server.
        """
        Module.__init__(self, context, name)
        self.port = port

        self.socket = None
        self.events_channel = self.context.channel(f"server-web-{port}")
        self.data_channel = self.context.channel(f"data-web-{port}")
        self.context.threaded(
            self.run_server, thread_name=f"web-{port}", daemon=True
        )
        self.server_headers = dict()
        self.client_headers = dict()
        self.handover = None
        root = self.context.root
        for result in root.find("gui/handover"):
            # Do we have a thread handover routine?
            if result is not None:
                self.handover, _path, suffix_path  = result
                break

    def stop(self):
        self.state = "terminate"

    def module_close(self, *args, **kwargs):
        _ = self.context._
        self.events_channel(_("Shutting down server."))
        self.state = "terminate"
        if self.socket is not None:
            self.socket.close()
            self.socket = None
    
    def send(self, command):
        if self.handover is None:
            self.context(f"{command}\n")
        else:
            self.handover(command)


    def receive(self, data):
        def parse_received_data():
            self.client_headers.clear()
            self.client_headers["TYPE"] = "UNKNOWN"
            self.client_headers["PAGE"] = "/"
            content = data if isinstance(data, str) else data.decode()
            lines = content.split("\n")
            if len(lines) > 0:
                # split the first line to get the query type
                urls = lines[0].split()
                self.client_headers["TYPE"] = urls[0]
                self.client_headers["PAGE"] = urls[1]
            header_mode = True
            key_prefix = ""
            separator = ":"
            for line in lines[1:]:

                idx = line.find(separator)
                if idx < 0:
                    header_mode = False
                    separator = "="
                    key_prefix = "post_"
                    idx = line.find(separator)
                if idx >= 0:
                    key = line[:idx].strip()
                    value = unquote_plus(line[idx + 1:].strip())
                    self.client_headers[key_prefix + key] = value

            # for key, value in self.client_headers.items():
            #     print (f"{key}: {value}")


        def execute_data():
            content = ""
            content_type = "html"
            if self.client_headers["TYPE"] == "GET":
                content = "---"
                pattern = "?cmd="
                p = self.client_headers.get("PAGE", "")
                idx = p.find(pattern)
                if idx >= 0:
                    command = unquote_plus(p[idx + len(pattern):])
                    self.context(command + "\n")
                    content = f"Received command: '{command}'"
            elif self.client_headers["TYPE"] == "POST" and "post_cmd" in self.client_headers:
                command = self.client_headers["post_cmd"]
                self.send(command)
                content = f"Received command: '{command}'"
            return content_type, content

        def build_response(content):
            def build_spooler_content():
                content_table = [
                    "<h2>Current jobs</h2>",
                    "<table>",
                    "<tr><td>#</td><td>Device</td><td>Name</td><td>Items</td><td>Status</td><td>Type</td><td>Steps</td><td>Passes</td><td>Priority</td><td>Runtime</td><td>Estimate</td></tr>",
                ]
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
                    queue_idx = 0
                    for idx, e in enumerate(spooler.queue):
                        queue_idx += 1
                        m = "<tr>"
                        # Idx, Status, Type, Passes, Priority, Runtime, Estimate
                        m += f"<td>#{queue_idx}"
                        spool_obj = e
                        m += f"<td>{device.label}</td>"
                        # Jobname
                        to_display = ""
                        if hasattr(spool_obj, "label"):
                            to_display = spool_obj.label
                            if to_display is None:
                                to_display = ""
                        if to_display == "":
                            to_display = _name_str(spool_obj)
                        if to_display.endswith(" items"):
                            # Look for last ':' and remove everything from there
                            cpos = -1
                            lpos = -1
                            while True:
                                lpos = to_display.find(":", lpos + 1)
                                if lpos == -1:
                                    break
                                cpos = lpos
                            if cpos > 0:
                                to_display = to_display[:cpos]

                            m += f"<td>{to_display}</td>"
                            # Entries
                            joblen = 1
                            try:
                                if hasattr(spool_obj, "items"):
                                    joblen = len(spool_obj.items)
                                elif hasattr(spool_obj, "elements"):
                                    joblen = len(spool_obj.elements)
                            except AttributeError:
                                joblen = 1
                            m += f"<td>{joblen}</td>"

                            # STATUS
                            m += f"<td>{spool_obj.status}</td>"

                            # TYPE
                            try:
                                content = str(spool_obj.__class__.__name__)
                            except AttributeError:
                                content = ""
                            m += f"<td>{content}</td>"

                            # STEPS
                            try:
                                if spool_obj.steps_total == 0:
                                    spool_obj.calc_steps()
                                content = f"{spool_obj.steps_done}/{spool_obj.steps_total}",
                            except AttributeError:
                                content = "-"
                            m += f"<td>{content}</td>"

                            # PASSES
                            try:
                                loop = spool_obj.loops_executed
                                total = spool_obj.loops
                                # No invalid values please
                                if loop is None:
                                    loop = 0
                                if total is None:
                                    total = 1

                                if isinf(total):
                                    total = "∞"
                                content = f"{loop}/{total}"
                            except AttributeError:
                                content = "-"
                            m += f"<td>{content}</td>"

                            # Priority
                            try:
                                content = f"{spool_obj.priority}"
                            except AttributeError:
                                content = "-"
                            m += f"<td>{content}</td>"

                            # Runtime
                            try:
                                t = spool_obj.elapsed_time()
                                hours, remainder = divmod(t, 3600)
                                minutes, seconds = divmod(remainder, 60)
                                content = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                            except AttributeError:
                                content = "-"
                            m += f"<td>{content}</td>"

                            # Estimate Time
                            try:
                                t = spool_obj.estimate_time()
                                if isinf(t):
                                    runtime = "∞"
                                else:
                                    hours, remainder = divmod(t, 3600)
                                    minutes, seconds = divmod(remainder, 60)
                                    content = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                            except AttributeError:
                                content = "-"
                            m += f"<td>{content}</td>"

                            m+= "</tr>"

                            content_table.append(m)

                content_table.append("<table>")
                return content_table

            def build_html_header():
                return [
                    '<!DOCTYPE html>',
                    '<html lang="en">',
                    '<head>',
                    '    <meta charset="UTF-8">',
                    '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                    '    <title>Webconsole Interface</title>',
                    '    <style>',
                    '      table, th, td {',
                    '        border: 1px solid black;',
                    '      }',
                    '    </style>',
                    '</head>',
                    '<body>',
                    f'   <h1>{self.context.kernel.name} {self.context.kernel.version} - Webconsole</h1>',
                    '     <h2>Active device</h2',
                    f'    <p>Active device: {self.context.device.label}</p>',
                ]

            # if "Host" in self.client_headers:
            #     myurl = self.client_headers["Host"]
            # else:
            #     myurl = f"http://127.0.0.1:{self.port}"
            myurl = "/"
            spooler_table = build_spooler_content()
            header = build_html_header()
            html = []
            html.extend(header)
            html.extend(spooler_table)
            html.extend(
                (
                '     </table>',
                '     <p></p>',
                '     <h2>Console commands</h2>',
                f'    <form action="{myurl}" method="post">',
                # '       <label for="cmd">Command:</label>',
                # '        <input type="text" id="cmd" name="cmd">',
                '       <textarea id="cmd" name="cmd" rows="10" cols="40"></textarea>',
                '       <br><br>',
                '       <input type="submit" value="Submit">',
                '    </form>',
                f'   <p>{content}</p>'
                '</body>',
                )
            )
            return html

        def build_json(content):
            return content

        parse_received_data()
        feedback_type, feedback_content = execute_data()
        # print (f"execute data: {feedback_type}: {feedback_content}")
        if feedback_type == "html":
            feedback_content = build_response(feedback_content)
        else:
            feedback_content = build_json(feedback_content)
        return feedback_type, feedback_content

    def respond_with_html(self, con, send_list):
        if con is None:
            return
        msg = "HTTP/1.0 200 OK\n"
        msg += "Content-Type: text/html\n"
        msg += "Content-Location: /\n"
# Separate headers from content
        msg += "\n"
        msg += "\n".join(send_list)
        try:
            # print(f"Will send:\n{msg}")
            e = bytes(msg, "utf-8")
            con.sendall(e)
            self.data_channel(f"<-- {str(e)}")
        except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
            self.events_channel(f"Sending data failed: {e}")

    def respond_with_json(self, con, send_list):
        if con is None:
            return
        msg = "HTTP/1.0 200 OK\n"
        msg += "Content-Type: application/json\n"
        msg += "Content-Location: /\n"
# Separate headers from content
        msg += "\n"
        msg += "\n".join(send_list)
        try:
            # print(f"Will send:\n{msg}")
            e = bytes(msg, "utf-8")
            con.sendall(e)
            self.data_channel(f"<-- {str(e)}")
        except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
            self.events_channel(f"Sending data failed: {e}")

    def run_server(self):
        """
        TCP Run is a connection thread delegate. Any connections are given a different threaded
        handle to interact with that connection. This thread here waits for sockets and delegates.
        """
        _ = self.context._
        self.socket = socket.socket()
        try:
            self.socket.bind(("", self.port))
            self.socket.listen(1)
        except OSError:
            self.events_channel(_("Could not start listening."))
            return
        self.events_channel(
            _("Listening {name} on port {port}...").format(
                name=self.name, port=self.port
            )
        )
        connection = None
        address = None
        while self.state != "terminate":
            try:
                connection, address = self.socket.accept()
                self.events_channel(
                    _("Socket Connected: {address}").format(address=address)
                )
                data_from_socket = connection.recv(1024).decode("UTF-8")
                headers, body = data_from_socket.split("\r\n\r\n", 1)  # Split request data into headers and body

                # get the content length from the headers
                content_length = 0
                for line in headers.split("\r\n"):
                    if "Content-Length" in line:
                        content_length = int(line.split(": ")[1])
                        break

                while len(body) < content_length:
                    body += connection.recv(1024).decode('UTF-8')
                data_from_socket = headers + "\n" + body
                if len(data_from_socket):
                    self.data_channel(f"--> {str(data_from_socket)}")
                    send_type, to_send = self.receive(data_from_socket)
                    if to_send:
                        if send_type == "html":
                            self.respond_with_html(connection, to_send)
                        elif send_type == "json":
                            self.respond_with_json(connection, to_send)
                connection.close()
                connection = None
                self.events_channel(
                    _("Connection to {address} was closed.").format(address=address)
                )
            except socket.timeout:
                self.events_channel(
                    _("Connection to {address} timed out.").format(address=address)
                )
            except OSError as e:
                self.events_channel(f"OS-Error: {e}")
            finally:
                if connection is not None:
                    connection.close()
            # except AttributeError :
            #     self.events_channel(_("Socket did not exist to accept connection."))
            #     break

        if self.socket is not None:
            self.socket.close()
