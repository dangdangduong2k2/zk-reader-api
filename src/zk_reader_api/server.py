"""Loopback HTTP adapter. Reader connects directly to the same OS as this process."""
import argparse
import hmac
import json
import secrets
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import Reader, __version__
from .errors import DeviceError, ProtocolError, ReaderError, RestoreError, TransportError


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class ApiServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, address, reader, token):
        if address[0] != "127.0.0.1":
            raise ValueError("This local adapter binds to 127.0.0.1 only")
        if not isinstance(token, str) or len(token) < 24 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError("API token must contain at least 24 non-whitespace ASCII characters")
        self.reader, self.token = reader, token
        self.operation_lock = threading.Lock()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "ZkReaderAPI/0.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_):
        pass  # Never log Authorization, passwords or tag payloads.

    def respond(self, status, body):
        data = json.dumps(body, ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.handle_api()

    def do_POST(self):
        self.handle_api()

    def handle_api(self):
        host = self.headers.get("Host", "")
        if host not in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"):
            return self.respond(403, {"error": "invalid_host"})
        supplied = self.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied.encode("utf-8"), ("Bearer " + self.server.token).encode("ascii")):
            return self.respond(401, {"error": "unauthorized"})
        # No CORS: browser origins cannot issue device mutations.
        if self.headers.get("Origin"):
            return self.respond(403, {"error": "browser_origin_not_allowed"})
        if self.command == "GET" and self.path == "/health":
            reader = self.server.reader
            return self.respond(200, {"version": __version__, "simulated": reader.simulated,
                                     "connected": not reader.transport.closed and not reader.transport.failed})
        routes = {("GET", "/v1/reader"): self.server.reader.info,
                  ("GET", "/v1/power"): self.server.reader.power,
                  ("POST", "/v1/power"): self.server.reader.power,
                  ("GET", "/v1/region"): self.server.reader.region,
                  ("POST", "/v1/region"): self.server.reader.region,
                  ("GET", "/v1/profile"): self.server.reader.profile,
                  ("GET", "/v1/profile/extended"): partial(self.server.reader.profile, format="extended"),
                  ("POST", "/v1/profile"): self.server.reader.profile,
                  ("GET", "/v1/query"): self.server.reader.query,
                  ("POST", "/v1/query"): self.server.reader.query,
                  ("POST", "/v1/inventory"): self.server.reader.inventory,
                  ("POST", "/v1/read"): self.server.reader.read,
                  ("POST", "/v1/write"): self.server.reader.write}
        operation = routes.get((self.command, self.path))
        if operation is None:
            return self.respond(404, {"error": "route_not_found"})
        try:
            params = {}
            if self.command == "POST":
                if self.headers.get("Transfer-Encoding"):
                    return self.respond(400, {"error": "chunked_not_supported"})
                if self.headers.get_content_type() != "application/json":
                    return self.respond(415, {"error": "expected_application_json"})
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or not lengths[0].isdigit():
                    return self.respond(411, {"error": "content_length_required"})
                length = int(lengths[0])
                if length > 8192:
                    return self.respond(413, {"error": "body_too_large"})
                raw = self.rfile.read(length)
                if len(raw) != length:
                    return self.respond(400, {"error": "incomplete_body"})
                params = json.loads(raw, object_pairs_hook=unique_object)
                if not isinstance(params, dict):
                    raise ValueError("JSON body must be an object")
                if self.path == "/v1/power":
                    if ("dbm" in params) == ("powers_dbm" in params):
                        raise ValueError("Exactly one of dbm/powers_dbm is required")
                    if "dbm" in params and type(params["dbm"]) is not int:
                        raise ValueError("Integer dbm is required")
                    if "powers_dbm" in params and not isinstance(params["powers_dbm"], list):
                        raise ValueError("powers_dbm array is required")
                if self.path == "/v1/region" and any(type(params.get(k)) is not int for k in ("band", "min_channel", "max_channel")):
                    raise ValueError("Integer band/min_channel/max_channel required")
                if self.path == "/v1/profile" and type(params.get("profile_id")) is not int:
                    raise ValueError("Integer profile_id required")
                if self.path == "/v1/query":
                    if not any(k in params for k in ("q", "session")):
                        raise ValueError("q or session required")
                    if any(type(params[k]) is not int for k in ("q", "session") if k in params):
                        raise ValueError("q and session must be integers when provided")
        except (ValueError, UnicodeError, OSError):
            return self.respond(400, {"error": "invalid_json_body"})
        if not self.server.operation_lock.acquire(blocking=False):
            return self.respond(409, {"error": "reader_busy"})
        try:
            self.respond(200, operation(**params))
        except (ValueError, TypeError) as error:
            self.respond(400, {"error": "invalid_parameters", "message": str(error)})
        except DeviceError as error:
            self.respond(422, {"error": "device_error", "command": error.command,
                               "status": error.status, "detail_hex": error.data.hex().upper()})
        except RestoreError as error:
            self.respond(502, {"error": "antenna_restore_failed", "action_succeeded": error.action_succeeded,
                               "message": str(error)})
        except TransportError as error:
            self.respond(503, {"error": "transport_error", "message": str(error), "retry_safe": False})
        except (ProtocolError, ReaderError) as error:
            self.respond(502, {"error": "protocol_error", "message": str(error), "retry_safe": False})
        finally:
            self.server.operation_lock.release()


def main():
    parser = argparse.ArgumentParser(description="ZK Ex10 direct serial API (Windows/macOS/Linux)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--port", help="Physical COM49, /dev/cu.usbserial-... or /dev/ttyUSB0")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--list-ports", action="store_true")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--antennas", type=int, choices=(1, 4), default=4)
    parser.add_argument("--http-port", type=int, default=8765)
    parser.add_argument("--token-file", help="Optional file containing a >=24 character API token")
    args = parser.parse_args()
    if args.list_ports:
        from serial.tools.list_ports import comports
        print(json.dumps([{"port": p.device, "description": p.description} for p in comports()], indent=2))
        return
    if not 1 <= args.http_port <= 65535:
        parser.error("http-port must be 1..65535")
    token = Path(args.token_file).read_text().strip() if args.token_file else secrets.token_urlsafe(32)
    reader = Reader.simulate(args.antennas) if args.simulate else Reader.open(args.port, args.baud, args.antennas)
    with reader:
        with ApiServer(("127.0.0.1", args.http_port), reader, token) as server:
            print(f"ZK Reader API {__version__} | {'SIMULATION' if reader.simulated else 'HARDWARE'}", flush=True)
            print(f"URL: http://127.0.0.1:{args.http_port}", flush=True)
            if not args.token_file:
                print(f"Token: {token}", flush=True)
            print("Ctrl+C stops server and closes serial port.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
