from cowboy.utils import start_daemon, is_port_available
from cowboy.config import REACT_DIST_DIR

from http.server import SimpleHTTPRequestHandler
from webbrowser import open
import socketserver
import os
import sys

HOST = "localhost"
PORT = 8085
MAX_RETRIES = 10


class CustomHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=REACT_DIST_DIR, **kwargs)

    # need this to route all requests to index.html or else the web server
    # will default try look for files in the served directory
    def do_GET(self):
        if self.path != "/" and self.path != "" and self.path != "/index.html":
            if os.path.exists(self.translate_path(self.path)):
                print("Routing to file: ", self.path)
                return super().do_GET()

        self.path = "/"
        return super().do_GET()


def serve_ui(session_id):
    def run_server(port):
        print("Running server on port: ", port)
        with socketserver.TCPServer(("", port), CustomHandler) as httpd:
            httpd.serve_forever()

    retries = 0
    port = PORT

    while retries < MAX_RETRIES:
        if is_port_available(port):
            # technically doing this out of order but its fine ..
            open(f"http://{HOST}:{PORT}/test-results/{session_id}")
            start_daemon(run_server, (port,))
            return

        retries += 1
        port += 1
