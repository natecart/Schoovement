"""Static file server for local dev, identical to `python -m http.server`
except it disables caching. Plain http.server sends no Cache-Control header,
so browsers apply heuristic caching and can keep serving old .js files after
an edit even on a manual reload -- confusing when iterating on source files.

Usage: python no_cache_server.py PORT [--directory DIR]
"""
import argparse
import functools
import http.server


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_GET(self):
        # Also strip conditional-request headers so an already-cached client
        # (e.g. one that talked to a plain http.server before this one was
        # running) can't get a 304 and keep reusing its old cached body --
        # every request gets a full fresh response, no exceptions.
        for h in ('If-Modified-Since', 'If-None-Match'):
            del self.headers[h]
        super().do_GET()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, nargs='?', default=8000)
    parser.add_argument('--directory', '-d', default='.')
    args = parser.parse_args()

    handler = functools.partial(NoCacheHandler, directory=args.directory)
    http.server.test(HandlerClass=handler, port=args.port)
