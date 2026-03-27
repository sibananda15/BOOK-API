import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).with_name("books.db")


class BookRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    genre TEXT
                )
                """
            )

    def list_books(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, title, author, year, genre FROM books ORDER BY id").fetchall()
            return [dict(row) for row in rows]

    def get_book(self, book_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, author, year, genre FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            return dict(row) if row else None

    def create_book(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO books (title, author, year, genre) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("genre")),
            )
            book_id = cursor.lastrowid
            conn.commit()
        return self.get_book(book_id)

    def update_book(self, book_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        with self._connect() as conn:
            existing = conn.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
            if not existing:
                return None
            conn.execute(
                """
                UPDATE books
                SET title = ?, author = ?, year = ?, genre = ?
                WHERE id = ?
                """,
                (data["title"], data["author"], data.get("year"), data.get("genre"), book_id),
            )
            conn.commit()
        return self.get_book(book_id)

    def delete_book(self, book_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
            return cursor.rowcount > 0


class BookRequestHandler(BaseHTTPRequestHandler):
    repository: BookRepository

    def _json_response(self, status: int, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_json_body(self) -> dict[str, Any] | None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None

        if content_length <= 0:
            return None

        raw = self.rfile.read(content_length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None

        return body if isinstance(body, dict) else None

    def _validate_book_payload(self, payload: dict[str, Any] | None) -> tuple[bool, str]:
        if payload is None:
            return False, "Invalid JSON payload"
        if not payload.get("title"):
            return False, "'title' is required"
        if not payload.get("author"):
            return False, "'author' is required"
        year = payload.get("year")
        if year is not None and not isinstance(year, int):
            return False, "'year' must be an integer when provided"
        return True, ""

    def _extract_id(self) -> int | None:
        parts = [p for p in self.path.split("/") if p]
        if len(parts) == 2 and parts[0] == "books" and parts[1].isdigit():
            return int(parts[1])
        return None

    def do_GET(self) -> None:
        if self.path == "/books":
            self._json_response(HTTPStatus.OK, self.repository.list_books())
            return

        book_id = self._extract_id()
        if book_id is None:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
            return

        book = self.repository.get_book(book_id)
        if not book:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Book not found"})
            return

        self._json_response(HTTPStatus.OK, book)

    def do_POST(self) -> None:
        if self.path != "/books":
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
            return

        payload = self._parse_json_body()
        is_valid, message = self._validate_book_payload(payload)
        if not is_valid:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": message})
            return

        book = self.repository.create_book(payload)
        self._json_response(HTTPStatus.CREATED, book)

    def do_PUT(self) -> None:
        book_id = self._extract_id()
        if book_id is None:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
            return

        payload = self._parse_json_body()
        is_valid, message = self._validate_book_payload(payload)
        if not is_valid:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": message})
            return

        book = self.repository.update_book(book_id, payload)
        if not book:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Book not found"})
            return

        self._json_response(HTTPStatus.OK, book)

    def do_DELETE(self) -> None:
        book_id = self._extract_id()
        if book_id is None:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
            return

        deleted = self.repository.delete_book(book_id)
        if not deleted:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Book not found"})
            return

        self._json_response(HTTPStatus.OK, {"message": "Book deleted"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    repository = BookRepository(DB_PATH)

    class Handler(BookRequestHandler):
        pass

    Handler.repository = repository

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Book API server running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
