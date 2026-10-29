#!/usr/bin/env python3
"""
CORS-enabled static server so figma_execute can fetch() label CSVs / thumbnails into
the plugin sandbox at zero context cost. Port 9230 is on the figma-console plugin
manifest allowlist (9223-9232); 9223 is the MCP websocket, 9230 is free.

Bind to "" (all interfaces) and fetch via http://localhost:9230/... — the manifest
allowlists host `localhost`, NOT `127.0.0.1` (different origins to Figma's gate).

Usage: python3 cors_server.py [dir=.] [port=9230]   (run backgrounded)
"""
import http.server, socketserver, os, sys
os.chdir(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "."))
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9230
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        super().end_headers()
    def do_OPTIONS(self): self.send_response(200); self.end_headers()
    def log_message(self, *a): pass
socketserver.TCPServer(("", PORT), H).serve_forever()
