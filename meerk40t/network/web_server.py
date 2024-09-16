import socket
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

    def stop(self):
        self.state = "terminate"

    def module_close(self, *args, **kwargs):
        _ = self.context._
        self.events_channel(_("Shutting down server."))
        self.state = "terminate"
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def receive(self, data):
        self.client_headers.clear()
        self.client_headers["TYPE"] = "UNKNOWN"
        self.client_headers["PAGE"] = "/"
        content = data.decode()
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

        if "Host" in self.client_headers:
            myurl = self.client_headers["Host"]
        else:
            myurl = f"http://127.0.0.1:{self.port}"
        content = ""
        if self.client_headers["TYPE"] == "GET":
            content = "---"
        if self.client_headers["TYPE"] == "POST":
            if "post_cmd" in self.client_headers:
                command = self.client_headers["post_cmd"]
                self.context(command + "\n")
                content = f"Received command: '{command}'"
        jobs = 0
        if self.context.device.spooler is not None:
            jobs = len(self.context.device.spooler.queue)
        html = (
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
            '     <table>',
            f'      <tr><td>Active device</td><td>{self.context.device.label}</td></tr>',
            f'      <tr><td>Current jobs</td><td>{jobs}</td></tr>',
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

        return html

    def send_to_connection(self, con, send_list):
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
        while self.state != "terminate":
            try:
                connection, address = self.socket.accept()
                self.events_channel(
                    _("Socket Connected: {address}").format(address=address)
                )
                data_from_socket = connection.recv(1024)
                if len(data_from_socket):
                    self.data_channel(f"--> {str(data_from_socket)}")
                    to_send = self.receive(data_from_socket)
                    if to_send:
                        self.send_to_connection(connection, to_send)
                connection.close()
            except socket.timeout:
                self.events_channel(
                    _("Connection to {address} timed out.").format(address=address)
                )
            except OSError:
                if connection is not None:
                    connection.close()
            # except AttributeError :
            #     self.events_channel(_("Socket did not exist to accept connection."))
            #     break
            self.events_channel(
                _("Connection to {address} was closed.").format(address=address)
            )

        if self.socket is not None:
            self.socket.close()
