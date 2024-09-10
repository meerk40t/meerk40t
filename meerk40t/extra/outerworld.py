"""
This module exposes a couple of simple commands to send some simple commands to the outer world
"""
import json
import threading
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

from meerk40t.kernel import get_safe_path

HTTPD = None
SERVER_THREAD = None
KERN = None

def plugin(kernel, lifecycle):
    global KERN
    KERN = kernel

    class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            from meerk40t.main import APPLICATION_NAME, APPLICATION_VERSION
            html = (
                '<!DOCTYPE html>',
                '<html lang="en">',
                '<head>',
                '    <meta charset="UTF-8">',
                '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                '    <title>Webconsole Interface</title>',
                '</head>',
                '<body>',
                f'   <h1>{APPLICATION_NAME} {APPLICATION_VERSION} - Webconsole</h1>',
                '    <form action="http://127.0.0.1:2080" method="post">',
                '        <label for="cmd">Command:</label>',
                '        <input type="text" id="cmd" name="cmd"><br><br>',
                '       <input type="submit" value="Submit">',
                '    </form>',
                '</body>',
            )            
            htmlstr = bytes("\n".join(html), "utf-8")
            
            # Send response status code
            self.send_response(200)
            
            # Send headers
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Write the response content
            self.wfile.write(htmlstr)            

        def do_POST(self):
            global KERN
            # Get the length of the data
            content_length = int(self.headers['Content-Length'])
            # Read the data
            post_data = self.rfile.read(content_length).decode("utf-8")
            data = urllib.parse.parse_qs(post_data) 
            # print(f"Received data: {post_data}: {data}")
            executed= []
            for header, lines in data.items():
                for line in lines:
                    print(f"Received data: '{header}' - '{line}'")
                    if header == "cmd":
                        executed.append(line) 
                        print (f"Execute: '{line}'") 
                        KERN.root(f"{line}\n")
                        print ("exec done")
            # Send response
            print ("Sending response")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"message": "Data received successfully", "executed_commands": executed}
            self.wfile.write(json.dumps(response).encode('utf-8'))

    def start_server(channel=None, port=None, context=None):
        global HTTPD
        global SERVER_THREAD

        def run_server():
            # print ("Started")
            try:
                HTTPD.serve_forever()
            except Exception as e:
                # print (f"Dying because: {e}")
                pass

        if port is None:
            port = 2080
        if channel:
            channel(f"Starting webconsole on port {port}")
        server_address = ('', port)
        HTTPD = HTTPServer(server_address, SimpleHTTPRequestHandler)
        SERVER_THREAD = threading.Thread(target=run_server)
        SERVER_THREAD.daemon = True  # This ensures the thread will exit when the main program exits
        SERVER_THREAD.start()

    def stop_server(channel=None):
        global HTTPD
        global SERVER_THREAD
        if HTTPD:
            if channel:
                channel("Shutting down webconsole...")
            HTTPD.server_close()
            if SERVER_THREAD:
                if channel:
                    channel("Shutting down thread")
                SERVER_THREAD.join()
                SERVER_THREAD = None
            if channel:
                channel("Shut down of webconsole done")
        
        HTTPD = None

    if lifecycle == "preshutdown":
        if HTTPD is not None:
            stop_server()
        return
    if lifecycle != "register":
        return
    
    import platform

    from meerk40t.core.units import Length, DEFAULT_PPI, UNITS_PER_PIXEL

    _ = kernel.translation
    context = kernel.root

    
    @kernel.console_argument("port", type=int, help=_("port to listen to, default 2080"))
    @kernel.console_command("webconsole",
        help=_("webconsole <port>")
        + "\n"
        + _("Opens a webpage or REST-Interface page"),
        input_type=None,
        output_type=None,
    )
    def webconsole(
        command,
        channel,
        _,
        port=None,
        data=None,
        post=None,
        **kwargs,
    ):
        global HTTPD

        if HTTPD is None:
            start_server(channel=channel, port=port, context=context)
        else:
            stop_server(channel=channel)


    @kernel.console_argument("url", type=str, help=_("Web url to call"))
    @kernel.console_command(
        "call_url",
        help=_("call_url <url>")
        + "\n"
        + _("Opens a webpage or REST-Interface page"),
        input_type=None,
        output_type=None,
    )
    def call_url(
        command,
        channel,
        _,
        url=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if url is None:
            channel(_("You need to provide an url to call"))
            return

        try:
            with urllib.request.urlopen(url, data=None) as f:
                channel(f.read().decode('utf-8'))
        except Exception as e:
            channel (f"Failed to call {url}: {e}")

    # webimage is just a subcase of webload
    
    # @kernel.console_argument("url", type=str, help=_("Image url to load"))
    # @kernel.console_argument("x", type=Length, help="Sets the x-position of the image",)
    # @kernel.console_argument("y", type=Length, help="Sets the y-position of the image",)
    # @kernel.console_argument("width", type=Length, help="Sets the width of the given image",)
    # @kernel.console_argument("height", type=Length, help="Sets the width of the given image",)
    # @kernel.console_command(
    #     "webimage",
    #     help=_("webimage <url> <x> <y> <width> <height")
    #     + "\n"
    #     + _("Gets an image or an svg file and puts it on the screen"),
    #     input_type=None,
    #     output_type=None,
    # )
    # def get_webimage(
    #     command,
    #     channel,
    #     _,
    #     url=None,
    #     x=None,
    #     y=None,
    #     width=None,
    #     height=None,
    #     data=None,
    #     post=None,
    #     **kwargs,
    # ):
    #     if url is None:
    #         channel(_("You need to provide an url of an image to load"))
    #         return
    #     try:
    #         import urllib
    #         import io
    #         from PIL import Image
    #         from meerk40t.svgelements import Matrix
    #     except ImportError:
    #         channel("Could not import urllib")
    #         return
    #     # Download the image data
    #     try:
    #         with urllib.request.urlopen(url) as response:
    #             image_data = response.read()
    
    #         # Open the image using PIL
    #         image = Image.open(io.BytesIO(image_data))        
    #     except Exception as e:
    #         channel (f"Failed to get {url}: {e}")
    #         return

    #     elements_service = kernel.elements
    #     # Now create the image object
    #     try:
    #         from PIL import ImageOps

    #         image = ImageOps.exif_transpose(image)
    #     except ImportError:
    #         pass
    #     _dpi = DEFAULT_PPI
    #     matrix = Matrix(f"scale({UNITS_PER_PIXEL})")
    #     try:
    #         context.setting(bool, "image_dpi", True)
    #         if context.image_dpi:
    #             try:
    #                 dpi = image.info["dpi"]
    #             except KeyError:
    #                 dpi = None
    #             if (
    #                 isinstance(dpi, tuple)
    #                 and len(dpi) >= 2
    #                 and dpi[0] != 0
    #                 and dpi[1] != 0
    #             ):
    #                 matrix.post_scale(
    #                     DEFAULT_PPI / float(dpi[0]), DEFAULT_PPI / float(dpi[1])
    #                 )
    #                 _dpi = round((float(dpi[0]) + float(dpi[1])) / 2, 0)
    #     except (KeyError, IndexError):
    #         pass

    #     element_branch = elements_service.get(type="branch elems")
    #     n = element_branch.add(
    #         image=image,
    #         matrix=matrix,
    #         # type="image raster",
    #         type="elem image",
    #         dpi=_dpi,
    #     )

    #     if width is not None:
    #         bb = n.bbox()
    #         wd = float(width)
    #         if height is None:
    #             # if we don't have a height then we use the image ratio
    #             ratio = (bb[2] - bb[0]) / (bb[3] - bb[1])
    #             ht = wd / ratio
    #         else:
    #             ht = float(height)
    #         sx = wd / (bb[2] - bb[0])
    #         sy = ht / (bb[3] - bb[1])
    #         n.matrix.post_scale(sx, sy)
    #     else:
    #         context.setting(bool, "scale_oversized_images", True)
    #         if context.scale_oversized_images:
    #             bb = n.bbox()
    #             sx = (bb[2] - bb[0]) / context.device.space.width
    #             sy = (bb[3] - bb[1]) / context.device.space.height
    #             if sx > 1 or sy > 1:
    #                 sx = max(sx, sy)
    #                 n.matrix.post_scale(1 / sx, 1 / sx)

    #     if x is not None and y is not None:
    #         bb = n.bbox()
    #         px = float(x)
    #         py = float(y)
    #         dx = px - bb[0]
    #         dy = py - bb[1]
    #         n.matrix.post_translate(dx, dy)
    #     else:
    #         context.setting(bool, "center_image_on_load", True)
    #         if context.center_image_on_load:
    #             bb = n.bbox()
    #             dx = (context.device.space.width - (bb[2] - bb[0])) / 2
    #             dy = (context.device.space.height - (bb[3] - bb[1])) / 2

    #             n.matrix.post_translate(dx, dy)

    #     post.append(elements_service.post_classify([n]))

    #     context.signal("refresh_scene", "Scene")

    @kernel.console_argument("url", type=str, help=_("Image url to load"))
    @kernel.console_argument("x", type=Length, help="Sets the x-position of the image",)
    @kernel.console_argument("y", type=Length, help="Sets the y-position of the image",)
    @kernel.console_argument("width", type=Length, help="Sets the width of the given image",)
    @kernel.console_argument("height", type=Length, help="Sets the width of the given image",)
    @kernel.console_command(
        "webload",
        help=_("webload <url> <x> <y> <width> <height")
        + "\n"
        + _("Gets a file and puts it on the screen"),
        input_type=None,
        output_type=None,
    )
    def get_webfile(
        command,
        channel,
        _,
        url=None,
        x=None,
        y=None,
        width=None,
        height=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if url is None:
            channel(_("You need to provide an url of a file to load"))
            return
        try:
            import urllib
            import os.path
            from meerk40t.svgelements import Matrix
        except ImportError:
            channel("Could not import urllib")
            return
        # Download the file data
        tempfile = None
        try:
            with urllib.request.urlopen(url) as response:
                # Try to get the original filename
                info = response.info()
                filename = None
                if 'Content-Disposition' in info:
                    content_disposition = info['Content-Disposition']
                    if 'filename=' in content_disposition:
                        filename = content_disposition.split('filename=')[1].strip('"')
                if filename is None:
                    # lets split the name
                    parts = url.split("/")
                    if len(parts) > 0:
                        filename = parts[-1]
                        for invalid in (":", "/", "\\"):
                            filename = filename.replace(invalid, "_")
                    else:
                        filename = "_webload.svg"
                file_data = response.read()
        
                safe_dir = os.path.realpath(get_safe_path(kernel.name))
                tempfile = os.path.join(safe_dir, filename)
                channel(f"Writing result to {tempfile}")
                with open(tempfile, "wb") as f:
                    f.write(file_data) 
        except Exception as e:
            channel (f"Failed to get {url}: {e}")
            return
        if tempfile is None:
            channel("Could not load any data")
            return
        elements_service = kernel.elements
        res = elements_service.load(tempfile)
        if not res:
            return
        
        def union_box(elements):
            boxes = []
            for e in elements:
                if not hasattr(e, "bbox"):
                    continue
                box = e.bbox()
                if box is None:
                    continue
                boxes.append(box)
            if len(boxes) == 0:
                return None
            (xmins, ymins, xmaxs, ymaxs) = zip(*boxes)
            return min(xmins), min(ymins), max(xmaxs), max(ymaxs)

        if width is not None:
            bb = union_box(elements_service.added_elements)
            if bb is not None:
                wd = float(width)
                if height is None:
                    # if we don't have a height then we use the ratio
                    ratio = (bb[2] - bb[0]) / (bb[3] - bb[1])
                    ht = wd / ratio
                else:
                    ht = float(height)
            sx = wd / (bb[2] - bb[0])
            sy = ht / (bb[3] - bb[1])
            for n in elements_service.added_elements:
                if hasattr(n, "matrix"):
                    n.matrix.post_scale(sx, sy)

        if x is not None and y is not None:
            bb = union_box(elements_service.added_elements)
            if bb is not None:
                px = float(x)
                py = float(y)
                dx = px - bb[0]
                dy = py - bb[1]
            for n in elements_service.added_elements:
                if hasattr(n, "matrix"):
                    n.matrix.post_translate(dx, dy)
        elements_service.clear_loaded_information()

        context.signal("refresh_scene", "Scene")


    os_system = platform.system()
    os_machine = platform.machine()
    # 1 = Windows, 2 = Linux, 3 = MacOSX, 4 = RPI
    default_system = 1
    if os_system == "Windows":
        default_system = 1
    elif os_system == "Linux":
        if os_machine in ("armv7l", "aarch64"):
            # Arm processor of a rpi
            default_system = 4
        else:
            default_system = 2
    elif os_system == "Darwin":
        default_system = 3
    if default_system == 4:
        @kernel.console_argument("port", type=int, help=_("Port to use"))
        @kernel.console_argument("value", type=int, help=_("Value to set (0/1)"))
        @kernel.console_command(
            "gpio_set",
            help=_("gpio_set <port> <value>")
            + "\n"
            + _("Sets a GPIO port on the RPI to a given value"),
            input_type=None,
            output_type=None,
        )
        def gpio_set(
            command,
            channel,
            _,
            port=None,
            value=None,
            post=None,
            **kwargs,
        ):
            if port is None:
                channel(_("You need to provide a port between 1 and 16"))
                return
            if value is None:
                channel(_("You need to provide a value to set (1 / = or True / False"))
                return
            if value:
                port_value = gpio.HIGH
            else:
                port_value = gpio.LOW
            try:
                import RPi.GPIO as gpio
            except ImportError:
                channel("Could not raspberry gpio library")
                return

            try:
                gpio.setmode(gpio.BCM)
                gpio.setup(port, gpio.OUT)
                gpio.output(port, port_value)
            except Exception as e:
                channel (f"Failed to set port {port} to {value}: {e}")
                pass
