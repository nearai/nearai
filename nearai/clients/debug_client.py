# This script creates a simple HTTP server that logs all incoming requests.
# May be used to replace NEAR AI provider and debug client communication.

# How to use:
# 1. Deploy local NEAR AI HUB instance
# 1. Update /hub/api/v1/completions.py to use the new provider URL (e.g. http://127.0.0.1:5000)
# 2. Start the hub and run the script:
#    python debug_client.py

import threading
import time

import BaseHTTPServer  # type: ignore


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    # This handler will catch all types of HTTP requests (GET, POST, PUT, DELETE, PATCH, OPTIONS)
    # and log the request details including timestamp, method, path, headers, and body.
    def do_ANY(self):  # noqa: N815, N802
        """Handle any type of request."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else ""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        print(
            "[{timestamp}] [{method}] {path} - Headers: {headers} - Body: {body}".format(
                timestamp=timestamp, method=self.command, path=self.path, headers=dict(self.headers), body=body
            )
        )
        while True:
            pass

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_ANY  # noqa: N815


class ThreadedHTTPServer(BaseHTTPServer.HTTPServer):
    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        thread = threading.Thread(target=self._handle_request, args=(request, client_address))
        thread.daemon = True
        thread.start()

    def _handle_request(self, request, client_address):
        """Handle one request by instantiating the handler class."""
        self.RequestHandlerClass(request, client_address, self)


if __name__ == "__main__":
    server = ThreadedHTTPServer(("0.0.0.0", 5000), RequestHandler)
    print("Starting server on port 5000...")
    server.serve_forever()
