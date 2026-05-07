#!/usr/bin/env python3
"""
Simple mock PagerDuty receiver for demo/testing. Listens for POSTs and prints payloads.
Usage: python3 monitoring/mock_pagerduty_receiver.py --port 8080
"""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length)
        print('Received mock PagerDuty payload:')
        print(body.decode('utf-8'))
        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=8080)
    args = p.parse_args()
    server = HTTPServer(('0.0.0.0', args.port), Handler)
    print(f"Mock PagerDuty receiver running on 0.0.0.0:{args.port}")
    server.serve_forever()
