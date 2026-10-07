"""Small HTTP API for the Frontend; uses Python's standard library only.

Run from the repository root:
    python -m ranking_eval.http_api --db data_module/src/movies.db
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import frontend_service as service


def make_handler(db_path: str, cors_origin: str):
    class ApiHandler(BaseHTTPRequestHandler):
        server_version = "MovieRecommenderAPI/1.0"

        def _send_json(self, status: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 1_000_000:
                    raise ValueError("Request body is too large")
                raw = self.rfile.read(length) if length else b"{}"
                value = json.loads(raw.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("JSON body must be an object")
                return value
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Invalid JSON request body") from exc

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/api/health":
                    self._send_json(200, {"ok": True})
                    return

                if parsed.path == "/api/movies":
                    result = service.list_movies(
                        db_path=db_path,
                        page=int(query.get("page", ["1"])[0]),
                        page_size=int(query.get("page_size", ["20"])[0]),
                        genre=query.get("genre", [None])[0],
                        search=query.get("search", [None])[0],
                    )
                    self._send_json(200, result)
                    return

                parts = parsed.path.strip("/").split("/")
                if len(parts) == 4 and parts[:2] == ["api", "users"] and parts[3] == "recommendations":
                    result = service.recommendations(
                        parts[2],
                        db_path=db_path,
                        limit=int(query.get("limit", ["10"])[0]),
                        candidate_k=int(query.get("candidate_k", ["100"])[0]),
                    )
                    self._send_json(200, result)
                    return

                self._send_json(404, {"error": "Endpoint not found"})
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
            except RuntimeError as exc:
                self._send_json(409, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        def do_POST(self):
            parsed = urlparse(self.path)
            parts = parsed.path.strip("/").split("/")
            try:
                body = self._read_json()
                if len(parts) == 4 and parts[:2] == ["api", "users"] and parts[3] == "onboarding":
                    result = service.onboard_user(
                        parts[2],
                        db_path=db_path,
                        selected_genres=body.get("selected_genres"),
                        favorite_movie_ids=body.get("favorite_movie_ids"),
                    )
                    self._send_json(200, result)
                    return

                if len(parts) == 4 and parts[:2] == ["api", "users"] and parts[3] == "interactions":
                    result = service.record_interaction(
                        parts[2],
                        body.get("movie_id"),
                        body.get("action"),
                        db_path=db_path,
                    )
                    self._send_json(200, result)
                    return

                self._send_json(404, {"error": "Endpoint not found"})
            except (ValueError, TypeError) as exc:
                self._send_json(400, {"error": str(exc)})
            except RuntimeError as exc:
                self._send_json(409, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        def log_message(self, format, *args):
            print("[%s] %s" % (self.log_date_time_string(), format % args))

    return ApiHandler


def main():
    parser = argparse.ArgumentParser(description="Run the movie recommendation HTTP API.")
    parser.add_argument("--db", default=os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data_module", "src", "movies.db"
    ))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--cors-origin", default="*", help="Allowed frontend origin; '*' is for local development.")
    args = parser.parse_args()
    if not os.path.exists(args.db):
        parser.error(f"database not found: {args.db}")
    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.db, args.cors_origin))
    print(f"Movie API listening at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
